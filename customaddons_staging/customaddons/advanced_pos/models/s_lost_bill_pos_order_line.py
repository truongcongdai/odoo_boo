from odoo import fields, models, api


class SPosOrderLineLot(models.Model):
    _name = "s.pos.pack.operation.lot"
    _description = "Specify product lot/serial number in pos order line"
    _rec_name = "lot_name"

    pos_order_line_id = fields.Many2one('pos.order.line')
    order_id = fields.Many2one('pos.order', related="pos_order_line_id.order_id", readonly=False)
    lot_name = fields.Char('Lot Name')
    product_id = fields.Many2one('product.product', related='pos_order_line_id.product_id', readonly=False)


class SlostBillPosOrderLine(models.Model):
    _name = 's.lost.bill.pos.order.line'

    qty = fields.Float('Số lượng', digits='Product Unit of Measure', default=1)
    logging_lost_bill_pos_order_id = fields.Many2one('s.lost.bill',
                                                     string='Order',
                                                     required=False)
    price_unit = fields.Float(string='Đơn giá')
    price_subtotal_incl = fields.Float(string='Thành tiền', digits=0,
                                       readonly=True, required=True)
    price_subtotal = fields.Float(string='Thành tiền chưa thuế', digits=0,
        readonly=True, required=True)
    discount = fields.Float(string='CK. (%)', digits=0, default=0.0)
    product_id = fields.Many2one('product.product', string='Product')
    tax_ids = fields.Many2many('account.tax', string='Thuế', readonly=True)
    full_product_name = fields.Char('Tên đầy đủ sản phẩm')
    price_extra = fields.Float('Giá thêm')
    mau_sac = fields.Char('Màu sắc')
    kich_thuoc = fields.Char('Kích thước')
    default_code = fields.Char('SKU')
    pack_lot_ids = fields.One2many('s.pos.pack.operation.lot', 'pos_order_line_id', string='Số lô/Seri')
    description = fields.Html('Mô tả')
    price_manually_set = fields.Float('Đặt giá thủ công')
    is_program_reward = fields.Boolean("Is reward line")
    program_id = fields.Many2one('coupon.program')
    coupon_id = fields.Many2one("coupon.coupon")
    gift_card_id = fields.Many2one("gift.card")
    s_gift_card_code = fields.Char(string='Gift card code', store=True)
