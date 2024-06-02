import json
import logging
from urllib.parse import urljoin
from odoo import _, api, fields, models
from odoo.addons.http_routing.models.ir_http import slugify_one

from odoo.exceptions import ValidationError
from ..tools.api_wrapper import _create_log

_logger = logging.getLogger(__name__)


class SProductAttribute(models.Model):
    _inherit = 'product.attribute'

    name = fields.Char('Attribute', required=True, translate=False)
    type = fields.Selection(
        string='Type',
        selection=[('color', 'Color'),
                   ('size', 'Size'), ('gender', 'Gender'), ('other', 'Other')], default='other')
    status_product_attribute = fields.Boolean(string='Is Magento Attribute')

    # chi tao 1 attribute color, size
    @api.constrains('type')
    def _check_color_n_size(self):
        attr_exist = 0
        if self.type == 'color':
            attr_exist = self.env['product.attribute'].sudo().search_count([('type', '=', 'color')])
        elif self.type == 'size':
            attr_exist = self.env['product.attribute'].sudo().search_count([('type', '=', 'size')])
        if attr_exist > 1:
            raise ValidationError('Thuộc tính %s đã tồn tại!' % self.type)

    @api.model
    def create(self, vals_list):
        res = super(SProductAttribute, self).create(vals_list)
        if vals_list.get('status_product_attribute', False):
            res.write({'status_product_attribute': vals_list.get('status_product_attribute', False)})
        return res

    def write(self, vals):
        res = super(SProductAttribute, self).write(vals)
        if 'status_product_attribute' in vals:
            magento2x_odoo_bridge_obj = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
            magento_attributes_set_obj = magento2x_odoo_bridge_obj.default_product_set_id
            if magento_attributes_set_obj:
                if vals['status_product_attribute']:
                    magento_attributes_set_obj.write({
                        'attribute_ids': [(4, self.id)]
                    })
                else:
                    magento_attributes_set_obj.write({
                        'attribute_ids': [(3, self.id)]
                    })
                magento_sale_channel = self.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
                if magento_sale_channel:
                    magento_sale_channel.export_magento2x_attributes()
                    magento_attributes_set = magento_sale_channel.default_product_set_id
                    if len(magento_attributes_set.attribute_ids) > 0:
                        for attribute in magento_attributes_set.attribute_ids:
                            attribute.magento_assign_to_attribute_set(magento_attributes_set.store_id)
        return res

    # Them vao danh sach dong bo Attribute

    def select_add_attribute_magento(self):
        for rec in self:
            rec.status_product_attribute = True
            rec._add_attribute_ids_to_magento_attributes_set()

    def _add_attribute_ids_to_magento_attributes_set(self):
        magento2x_odoo_bridge_obj = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        magento_attributes_set_obj = magento2x_odoo_bridge_obj.default_product_set_id
        if magento_attributes_set_obj:
            magento_attributes_set_obj.write({
                'attribute_ids': [(4, self.id)]
            })

    # Xoa khoi danh sach dong bo attribute

    def select_cancel_attribute_magento(self):
        for rec in self:
            rec.status_product_attribute = False
            rec._cancel_attribute_ids_to_magento_attributes_set()

    def _cancel_attribute_ids_to_magento_attributes_set(self):
        magento2x_odoo_bridge_obj = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        magento_attributes_set_obj = magento2x_odoo_bridge_obj.default_product_set_id
        if magento_attributes_set_obj:
            magento_attributes_set_obj.write({
                'attribute_ids': [(3, self.id)]
            })

    def magento_assign_to_attribute_set(self, attribute_store_id):
        try:
            sdk = self.get_m2_sdk()
            url = self._get_magento_assign_attribute_url()
            data = json.dumps(self._build_magento_assign_attribute_data(attribute_store_id))
            resp = sdk._post_data(url=url, data=data)
            if resp.get('message'):
                _logger.error(resp.get('message'))
                # _create_log(
                #     name=resp['message'],
                #     message=f'{fields.Datetime.now().isoformat()} POST {url}\n' +
                #             f'data={data}\n' +
                #             f'response={resp}\n',
                #     func='magento_assign_to_attribute_set'
                # )
        except Exception as e:
            _logger.error(e.args)
            # _create_log(name='magento_create_attribute_error', message=e.args, func='magento_assign_to_attribute_set')

    def get_m2_sdk(self):
        return self.env.ref('magento2x_odoo_bridge.magento2x_channel').sudo().get_magento2x_sdk()['sdk']

    def _get_magento_assign_attribute_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url,
                       f'/rest/{magento_odoo_bridge.store_code}/V1/products/attribute-sets/attributes')

    def _build_magento_assign_attribute_data(self, attribute_store_id):
        attribute_group_id_obj = self._get_magento_attribute_group_id(attribute_store_id)
        attribute_group_id = int(attribute_group_id_obj['data']['items'][0]['attribute_group_id'])
        current_attribute_mapping = self.env['channel.attribute.mappings'].sudo().search(
            [('odoo_attribute_id', '=', self.id)], limit=1)
        if current_attribute_mapping:
            attribute_code = current_attribute_mapping.store_attribute_name
        else:
            attribute_code = "odoo_" + str(self.id)
            # M2 mac dinh co attribute_code color & size
            if self.type == 'color':
                attribute_code = 'color'
            elif self.type == 'size':
                attribute_code = 'size'
        data = {
            "attributeSetId": attribute_store_id,
            "attributeGroupId": attribute_group_id,
            "attributeCode": attribute_code,
            "sortOrder": 150,
        }


        return data

    def _get_magento_attribute_group_id(self, attribute_store_id):
        try:
            sdk = self.get_m2_sdk()
            url = self._get_magento_attribute_group_url(attribute_store_id)
            resp = sdk._get_data(url=url)
            return resp
        except Exception as e:
            _logger.error(e.args)
            # _create_log(name='magento_get_attribute_group_id_error', message=e.args,
            #             func='magento_get_attribute_group_id')

    def _get_magento_attribute_group_url(self, attribute_store_id):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url,
                       f'/rest/{magento_odoo_bridge.store_code}/V1/products/attribute-sets/groups/list?searchCriteria[filter_groups][0][filters][0][field]=attribute_set_id&searchCriteria[filter_groups][0][filters][0][value]={attribute_store_id}')
