from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    m2_url = fields.Char(
        related='product_id.m2_url',
        store=True,
        readonly=False
    )
    is_magento_order = fields.Boolean(
        related='order_id.is_magento_order',
        store=True
    )
    s_product_barcode = fields.Char(related='product_id.barcode')
    s_ma_mau = fields.Char(related='product_id.ma_mau')
    is_product_free = fields.Boolean(string='Là line sản phẩm được tặng', default=False)
    is_line_coupon_program = fields.Boolean(string='Là line CTKM', default=False)
    program_name = fields.Char(string='Tên CTKM', related='coupon_program_id.name', store=True)
    promo_code_line = fields.Char(string='Mã CTKM')
    coupon_code_line = fields.Char(string='Mã phiếu giảm giá')
    pod_image_url = fields.Char(string='Url ảnh POD')
    is_loyalty_reward_line = fields.Boolean(string='Là line loyalty program')

    # @api.constrains('m2_url', 'is_magento_order')
    # def _check_magento_order_product_url(self):
    #     for r in self:
    #         if r.is_magento_order and r.product_id and not r.m2_url:
    #             raise ValidationError(_('Magento Order Line must have Magento Link for products!'))

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        magento_order_lines = self.filtered(lambda r: r.is_magento_order)
        odoo_order_line = self.filtered(lambda r: not r.is_magento_order)
        res = super(SaleOrderLine, odoo_order_line)._action_launch_stock_rule(
            previous_product_uom_qty=previous_product_uom_qty
        )
        super(SaleOrderLine, magento_order_lines.with_context(skip_procurement=True))._action_launch_stock_rule(
            previous_product_uom_qty=previous_product_uom_qty
        )
        return res

    def check_is_shipping_line(self):
        return self.is_delivery

    def check_is_line_coupon_program(self):
        return self.is_line_coupon_program

    def check_is_line_product_free(self):
        return self.is_product_free

    def read_converted(self):
        res = super(SaleOrderLine, self).read_converted()
        for r in res:
            sale_order_line_id = self.search([('id', '=', r.get('id'))], limit=1)
            if sale_order_line_id:
                r['boo_total_discount_percentage'] = sale_order_line_id.boo_total_discount_percentage
        return res
