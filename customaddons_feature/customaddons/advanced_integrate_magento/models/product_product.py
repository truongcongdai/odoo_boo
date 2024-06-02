import json
from urllib.parse import urljoin

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    m2_url = fields.Char(
        string='Magento2x Link',
        copy=False
    )
    is_gift_card = fields.Boolean(
        string='Là gift card', default=False
    )
    la_so_tien_phai_thu_them = fields.Boolean(
        string='Là số tiền phải thu thêm trong hóa đơn'
    )
    la_phi_ship_hang_m2 = fields.Boolean(
        string='Là phí ship hàng từ M2'
    )
    ma_size = fields.Char(string="Mã Size", compute='_compute_ma_size', store=True)
    ma_mau = fields.Char(string="Mã Màu BOO", compute='_compute_ma_mau', store=True)
    need_sync_m2_stock = fields.Boolean(default=True)
    is_line_ctkm_m2 = fields.Boolean(default=False)
    s_loyalty_product_reward = fields.Boolean(string='Sản phẩm quy đổi điểm')

    @api.depends('product_template_attribute_value_ids')
    def _compute_ma_size(self):
        for rec in self:
            ma_size = ''
            for product_template_attribute_value in rec.product_template_attribute_value_ids:
                if product_template_attribute_value.attribute_id.type == "size":
                    ma_size = product_template_attribute_value.product_attribute_value_id.code
            rec.ma_size = ma_size

    @api.depends('product_template_attribute_value_ids')
    def _compute_ma_mau(self):
        for rec in self:
            ma_mau = ''
            for product_template_attribute_value in rec.product_template_attribute_value_ids:
                if product_template_attribute_value.attribute_id.type == "color":
                    ma_mau = product_template_attribute_value.product_attribute_value_id.code
            rec.ma_mau = ma_mau

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
                'price': self.lst_price
            }
        }

    @api.model
    def _get_magento_update_product_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url, f'/rest/all/V1/products')

    def write(self, vals):
        need_to_update_sync_status_keys = ['description', 'ma_san_pham', 'thuong_hieu', 'bo_suu_tap', 'categ_id',
                                           'season', 'chung_loai', 'gioi_tinh', 'dong_hang', 'uom_id', 'mau_sac',
                                           'kich_thuoc', 'ma_vat_tu']
        if any([key in vals for key in need_to_update_sync_status_keys]):
            vals['check_sync_product'] = False
        keys_to_check = ('name', 'lst_price')
        res = super(ProductProduct, self).write(vals)
        for rec in self:
            if vals.get('sync_push_magento') and not rec.need_sync_m2_stock:
                vals['need_sync_m2_stock'] = True
            elif not vals.get('sync_push_magento') and rec.need_sync_m2_stock:
                vals['need_sync_m2_stock'] = False
        if any([key in vals for key in keys_to_check]):
            for r in self.filtered(lambda pt: pt.sync_push_magento):
                r.magento_update_product()
        return res

    def _compute_need_sync_m2_stock(self):
        for r in self:
            if not r.need_sync_m2_stock and r.check_sync_product:
                r.need_sync_m2_stock = True
