import json
from urllib.parse import urljoin
import time
import traceback
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sync_push_magento = fields.Boolean(
        string='Push Magento?',
        copy=False
    )
    m2_url = fields.Char(
        related='product_variant_id.m2_url',
        compute_sudo=True
    )
    is_gift_card = fields.Boolean(
        string='Là gift card', default=False
    )
    check_sync_qty = fields.Boolean(
        string='Trạng thái tồn kho được đồng bộ lên Magento'
    )

    @api.model
    def cron_post_product_m2(self):
        start_time = time.time()
        try:
            magento_sale_channel = self.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
            limit_product_size = self.env['ir.config_parameter'].get_param('advanced_pos.get_product_limit', 10)
            if not magento_sale_channel:
                raise ValidationError(_('Magento Odoo Bridge does not exist, pls contact your Administrator!'))
            count = 0
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                products = self.env['product.template'].search([('sync_push_magento', '=', True),
                                                                ('check_sync_product', '=', False)],
                                                               limit=int(limit_product_size))
                if len(products) > 0:
                    for product in products:
                        try:
                            to_create_mappings = []
                            res, remote_object = magento_sale_channel.export_magento2x(product)
                            # Save check_sync_product = True if sync product
                            self.env['product.template'].browse(product.id).write({
                                'check_sync_product': True
                            })
                            self.env.cr.commit()
                            if res:
                                to_create_mappings.append({
                                    'channel_id': magento_sale_channel.id,
                                    'ecom_store': 'magento2x',
                                    'template_name': product.id,
                                    'odoo_template_id': product.id,
                                    'default_code': product.default_code,
                                    'barcode': product.barcode,
                                    'store_product_id': remote_object.get('id') if isinstance(remote_object,
                                                                                              dict) else remote_object.id,
                                    'operation': 'export',
                                })
                                # logan start update stock.quant
                                current_product_quant = self.env['stock.quant'].sudo().search(
                                    [('product_id', 'in', [e.id for e in product.product_variant_ids])])
                                for stock_quant in current_product_quant:
                                    stock_quant.cron_synchronizing_stock_qty()
                                self.env['product.template'].browse(product.id).write({
                                    'check_sync_product': True
                                })
                            if to_create_mappings:
                                # return self.env['channel.template.mappings'].create(to_create_mappings)
                                current_product_template = self.env['channel.template.mappings'].sudo().search(
                                    [('odoo_template_id', '=', product.id)], limit=1)
                                if not current_product_template:
                                    self.env['channel.template.mappings'].create(to_create_mappings)
                        except Exception as ex:
                            error = traceback.format_exc()
                            _logger.error('cron_post_product_m2-child')
                            _logger.error(error)
                    print('Sync prouct time: %s, count: %s ' % (time.time() - start_time, count))
                else:
                    break
        except Exception as ex:
            error = traceback.format_exc()
            _logger.error('cron_post_product_m2')
            _logger.error(error)

    def write(self, vals):
        # if 'attribute_line_ids' in vals:
        #     raise UserError('Bạn không thể thay đổi "Thuộc tính & Biến thể"')
        need_to_update_sync_status_keys = ['description', 'ma_san_pham', 'thuong_hieu', 'bo_suu_tap', 'categ_id',
                                           'season', 'chung_loai', 'gioi_tinh', 'dong_hang', 'uom_id', 'mau_sac',
                                           'kich_thuoc', 'ma_vat_tu', 'attribute_line_ids']
        if any([key in vals for key in need_to_update_sync_status_keys]):
            vals['check_sync_product'] = False
        keys_to_check = ('name', 'list_price')
        res = super(ProductTemplate, self).write(vals)
        if any([key in vals for key in keys_to_check]):
            for r in self.filtered(lambda pt: pt.sync_push_magento):
                if len(r.product_variant_ids) > 0:
                    for variant in r.product_variant_ids:
                        variant.magento_update_product()
                r.magento_update_product()
        return res

    def magento_update_product(self):
        self.ensure_one()
        try:
            sdk = self.env.ref('magento2x_odoo_bridge.magento2x_channel').get_magento2x_sdk()['sdk']
            url = self._get_magento_update_product_url()
            data = json.dumps(self._prepare_push_data())
            resp = sdk._post_data(url=url, data=data)
            if resp.get('message'):
                _logger.error(resp.get('message'))
                # raise ValidationError(resp.get('message'))
        except Exception as e:
            _logger.error(e.args)
            # raise ValidationError(e.args)

    def _prepare_push_data(self):
        self.ensure_one()
        return {
            'product': {
                'sku': self.default_code,
                'name': self.name,
                'price': self.list_price
            }
        }

    @api.model
    def _get_magento_update_product_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url, f'/rest/all/V1/products')
