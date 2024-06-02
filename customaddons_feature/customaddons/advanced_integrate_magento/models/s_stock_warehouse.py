import json
import logging
from urllib.parse import urljoin

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slugify_one
from odoo.exceptions import UserError,ValidationError
from ..tools.api_wrapper import _create_log

_logger = logging.getLogger(__name__)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    status_stock_warehouse = fields.Boolean(string='Is Magento Source')
    users_receive_noti = fields.Many2many('res.users', string="Người nhận thông báo")
    source_code_name = fields.Char(
        string='Source Code Name',
        compute='_compute_source_code_name',
        store=True
    )
    m2_stock_ids = fields.Many2many(
        comodel_name='magento.web.stock',
        relation='warehouse_magento_stock_rel',
        column1='warehouse_id',
        column2='magento_stock_id',
        string='Magento2 Stocks',
        readonly=True,
        help='This is a technical field, for technical problems!'
    )
    is_synced_magento = fields.Boolean('Đã được đồng bộ lên Magento', default=False)
    is_assigned_source_to_stock = fields.Boolean('Đã được gán vào kho', default=False)

    @api.model
    def create(self, vals_list):
        res = super(StockWarehouse, self).create(vals_list)
        # logan fix search magento source code duplicate
        existing_warehouse_same_m2_code = self.env['stock.warehouse'].search([('source_code_name', '=', self.source_code_name), ('id', '!=', self.id)], limit=1)
        if existing_warehouse_same_m2_code:
            raise UserError('Magento Source Code bị trùng')
        if vals_list.get('status_stock_warehouse') == True:
            res.write(vals_list)
        return res

    def write(self, vals):
        keys_to_check = ('name', 'code', 'partner_id')
        res = super(StockWarehouse, self).write(vals)
        if any([key in vals for key in keys_to_check]):
            for rec in self:
                if not rec.is_assigned_source_to_stock:
                    rec.is_assigned_source_to_stock = False
        if 'status_stock_warehouse' in vals:
            magento_web_stock_obj = self.env['magento.web.stock'].search([], limit=1)
            if magento_web_stock_obj:
                if vals['status_stock_warehouse'] == True:
                    magento_web_stock_obj.write({
                        'warehouse_ids': [(4, self.id)]
                    })
                else:
                    magento_web_stock_obj.write({
                        'warehouse_ids': [(3, self.id)]
                    })
        # data_update_sync_magento = ['partner_id']
        # if any([key in vals for key in data_update_sync_magento]):
        #     self.write({
        #         'is_synced_magento': False
        #     })
        #     self.magento_create_source()
        # logan - force update name, partner_id to M2
        if 'name' in vals or 'partner_id' in vals:
            for rec in self:
                rec.force_update_magento_source_info()
        return res

    def select_add_warehouse_magento_2x(self):
        for rec in self:
            rec.status_stock_warehouse = True
            rec._add_warehouse_ids_to_magento_web_stock()

    def _add_warehouse_ids_to_magento_web_stock(self):
        magento_web_stock_obj = self.env['magento.web.stock'].search([], limit=1)
        if magento_web_stock_obj:
            magento_web_stock_obj.write({
                'warehouse_ids': [(4, self.id)]
            })

    def select_cancel_warehouse_magento_2x(self):
        for rec in self:
            rec.status_stock_warehouse = False
            rec._cancel_warehouse_ids_to_magento_web_stock()

    def _cancel_warehouse_ids_to_magento_web_stock(self):
        magento_web_stock_obj = self.env['magento.web.stock'].search([], limit=1)
        if magento_web_stock_obj:
            magento_web_stock_obj.write({
                'warehouse_ids': [(3, self.id)]
            })

    @api.depends('name')
    def _compute_source_code_name(self):
        for r in self:
            if not r.source_code_name:
                r.source_code_name = slugify_one(r.name).replace('-', '_')

    @api.model
    def _get_magento_create_source_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url, f'/rest/{magento_odoo_bridge.store_code}/V1/inventory/sources')

    def _build_magento_create_source_data(self):
        self.ensure_one()
        partner = self.partner_id.sudo()
        source = {
            'name': self.name,
            'source_code': self.source_code_name,
            'postcode': partner.zip,
            'enabled': True,
            'contact_name': partner.name,
            'phone': partner.phone,
            'country_id': partner.country_id.code,
            'street': partner.street,
            'extension_attributes': {
                'city_id': partner.city_id and str(partner.city_id.code) or False,
                'district_id': partner.district_id and str(partner.district_id.code) or False,
                'ward_id': partner.ward_id and str(partner.ward_id.code) or False
            }
        }
        return {
            'source': source
        }

    @api.model
    def _get_magento_assign_source_to_stock_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url,
                       f'/rest/{magento_odoo_bridge.store_code}/V1/inventory/stock-source-links')

    def _build_magento_assign_source_to_stock_data(self, stock_external_id):
        links = []
        source_ids = self.filtered(lambda s: s.is_assigned_source_to_stock == False)
        for _index, r in enumerate(source_ids):
            links.append({
                'source_code': r.source_code_name,
                'stock_id': stock_external_id,
                'priority': _index + 1,
            })
        return {
            'links': links
        }

    @api.model
    def get_m2_sdk(self):
        return self.env.ref('magento2x_odoo_bridge.magento2x_channel').sudo().get_magento2x_sdk()['sdk']

    def magento_create_source(self):
        try:
            sdk = self.get_m2_sdk()
            url = self._get_magento_create_source_url()
            stock_warehouses = self.search([('status_stock_warehouse', '=', True), ('is_synced_magento', '=', False)], limit=20)
            for r in stock_warehouses:
                data = json.dumps(r._build_magento_create_source_data())
                resp = sdk._post_data(url=url, data=data)
                if resp.get('message'):
                    _logger.error(resp.get('message'))
                    # raise ValidationError(resp.get('message'))
                    # _create_log(
                    #     name=resp['message'],
                    #     message=f'{fields.Datetime.now().isoformat()} POST {url}\n' +
                    #             f'data={data}\n' +
                    #             f'response={resp}\n',
                    #     func='magento_create_source'
                    # )
                else:
                    r.write({
                        'is_synced_magento': True
                    })
        except Exception as e:
            _logger.error(e.args)
            # raise ValidationError(e.args)
            # _create_log(name='magento_create_source_error', message=e.args, func='magento_create_source')

    def magento_assign_source_to_stock(self, stock_external_id):
        try:
            sdk = self.get_m2_sdk()
            url = self._get_magento_assign_source_to_stock_url()
            data_dict = self._build_magento_assign_source_to_stock_data(stock_external_id)
            stock_link_list = data_dict['links']
            if len(stock_link_list) > 0:
                def list_split(listA, n):
                    for x in range(0, len(listA), n):
                        every_chunk = listA[x: n + x]

                        # if len(every_chunk) < n:
                        #     every_chunk = every_chunk + \
                        #                   [None for y in range(n - len(every_chunk))]
                        yield every_chunk

                if len(stock_link_list) > 10:
                    api_stock_link_list = list(list_split(stock_link_list, 10))
                else:
                    api_stock_link_list = [stock_link_list]
                for api_stock_link in api_stock_link_list:
                    data = json.dumps({
                        'links': api_stock_link
                    })
                    resp = sdk._post_data(url=url, data=data)
                    if resp.get('message'):
                        _logger.error(resp.get('message'))
                        # raise ValidationError(resp.get('message'))
                        # _create_log(
                        #     name=resp['message'],
                        #     message=f'{fields.Datetime.now().isoformat()} POST {url}\n' +
                        #             f'data={data}\n' +
                        #             f'response={resp}\n',
                        #     func='magento_assign_source_to_stock'
                        # )
                    else:
                        for r in api_stock_link:
                            source_id = self.sudo().search([('source_code_name', '=', r['source_code'])], limit=1)
                            if source_id:
                                source_id.sudo().write({'is_assigned_source_to_stock': True})
        except Exception as e:
            _logger.error(e.args)
            # raise ValidationError(e.args)
            # _create_log(name='magento_create_source_error', message=e.args, func='magento_assign_source_to_stock')

    def force_update_magento_source_info(self):
        for rec in self:
            if rec.status_stock_warehouse and rec.is_synced_magento and rec.partner_id:
                try:
                    sdk = self.get_m2_sdk()
                    magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
                    url = urljoin(magento_odoo_bridge.url, f'/rest/all/V1/inventory/sources/' + rec.source_code_name)
                    partner = rec.partner_id.sudo()
                    body_json = {
                        'source': {
                            'name': rec.name,
                            'postcode': partner.zip,
                            'enabled': True,
                            'contact_name': partner.name,
                            'phone': partner.phone,
                            'country_id': partner.country_id.code,
                            'street': partner.street,
                            'extension_attributes': {
                                'city_id': partner.city_id and str(partner.city_id.code) or False,
                                'district_id': partner.district_id and str(partner.district_id.code) or False,
                                'ward_id': partner.ward_id and str(partner.ward_id.code) or False
                            }
                        }
                    }
                    data = json.dumps(body_json)
                    resp = sdk._put_data(url=url, data=data)
                    if resp.get('message'):
                        _logger.error(resp.get('message'))
                        # _create_log(
                        #     name=resp['message'],
                        #     message=f'{fields.Datetime.now().isoformat()} POST {url}\n' +
                        #             f'data={data}\n' +
                        #             f'response={resp}\n',
                        #     func='force_update_source_error'
                        # )
                except Exception as e:
                    _logger.error(e.args)
                    # _create_log(name='force_update_source_error', message=e.args, func='force_update_source_error')

    @api.onchange('partner_id')
    def _on_change_m2_stock_warehouse_partner_id(self):
        if self.partner_id:
            if not self.partner_id.name:
                raise UserError('Tên địa chỉ kho là trường bắt buộc')
            if not self.partner_id.zip:
                raise UserError('Zipcode địa chỉ kho là trường bắt buộc')
            if not self.partner_id.phone:
                raise UserError('Số điện thoại địa chỉ kho là trường bắt buộc')
            if not self.partner_id.country_id:
                raise UserError('Quốc gia địa chỉ kho là trường bắt buộc')
            if not self.partner_id.street:
                raise UserError('Địa chỉ của địa chỉ kho là trường bắt buộc')
            if not self.partner_id.city_id:
                raise UserError('Thành phố địa chỉ kho là trường bắt buộc')
            if not self.partner_id.district_id:
                raise UserError('Quận huyện địa chỉ kho là trường bắt buộc')
            if not self.partner_id.ward_id:
                raise UserError('Thị xã địa chỉ kho là trường bắt buộc')