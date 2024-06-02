from odoo import _, api, models, fields


class SaleOrderLineCouponProgram(models.Model):
    _name = 'sale.order.line.coupon.program'

    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity', default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    qty_delivered = fields.Float('Delivered Quantity', default=0.0)
    qty_invoiced = fields.Float(string='Invoiced Quantity')
    qty_to_invoice = fields.Float(string='To Invoice Quantity')
    price_total = fields.Float(string='Total')
    price_subtotal = fields.Float(string='Subtotal')
    untaxed_amount_to_invoice = fields.Float("Untaxed Amount To Invoice")
    untaxed_amount_invoiced = fields.Float("Untaxed Invoiced Amount")
    price_unit = fields.Float(string='Unit Price', required=True, default=0.0)
    gift_card_id = fields.Many2one('gift.card', string='Gift Card')
    coupon_program_id = fields.Many2one('coupon.program', string='Discount Program')
    program_name = fields.Char(string='Tên CTKM')
    order_id = fields.Many2one('sale.order', string='Sale Order')
    discount = fields.Float(string='Discount (%)', default=0.0)
    is_line_coupon_program = fields.Boolean(string='Là line CTKM', default=False)
    boo_total_discount = fields.Float()
    boo_total_discount_percentage = fields.Float()
    boo_phan_bo_price_total = fields.Float(string="Phân bổ thành tiền")
    order_name = fields.Char(string="Order Name", related='order_id.name', store=True)
    amount_total_so = fields.Float(string="Order Amount Total", compute='_compute_sale_order_m2', store=True)
    state_so = fields.Char(string="Order State", compute='_compute_sale_order_m2', store=True)
    partner_id_so = fields.Integer(string="Order Partner", compute='_compute_sale_order_m2', store=True)
    user_id_so = fields.Integer(string="Order User", compute='_compute_sale_order_m2', store=True)
    quantity_program_duplicate = fields.Float(string='Số lượng CTKM duplicate trong đơn hàng chưa tách line',
                                              compute='_compute_quantity_coupon_program_duplicate', store=True)

    @api.depends('order_id')
    def _compute_quantity_coupon_program_duplicate(self):
        for r in self:
            r.quantity_program_duplicate = 1
            coupon_program_ids = []
            if r.order_id.coupon_code:
                coupon_m2_ids = r.order_id.coupon_code.split(',')
                for coupon_m2_id in coupon_m2_ids:
                    coupon_odoo = self.env['coupon.coupon'].search(
                        [('boo_code', '=', coupon_m2_id)], limit=1)
                    if coupon_odoo:
                        if coupon_odoo.program_id.id not in coupon_program_ids:
                            coupon_program_ids.append(coupon_odoo.program_id.id)
                        else:
                            r.quantity_program_duplicate += 1

    @api.depends('order_id')
    def _compute_sale_order_m2(self):
        for r in self:
            r.amount_total_so = r.order_id.amount_total if r.order_id.amount_total else 0
            r.state_so = r.order_id.state
            r.partner_id_so = r.order_id.partner_id.id if r.order_id.partner_id else False
            r.user_id_so = r.order_id.user_id.id if r.order_id.user_id else False
