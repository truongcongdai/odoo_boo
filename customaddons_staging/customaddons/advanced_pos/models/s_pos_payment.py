from odoo import fields, models, api
from odoo.osv.expression import AND


class SPosOrderPayment(models.Model):
    _inherit = 'pos.payment'

    payment_note = fields.Char(string="Ghi chú thanh toán")
    s_pos_reference = fields.Char('Mã biên lai', related='pos_order_id.pos_reference')
    s_pos_name = fields.Char('Điểm bán hàng', related='pos_order_id.pos_name', store=True)
    s_gift_card_id = fields.Many2one('gift.card', string='GiftCard')
    s_gift_card_code = fields.Char(related='s_gift_card_id.code', string='Giftcard code')
    s_completed_time = fields.Datetime(string='Ngày hoàn thành đơn hàng', compute='_compute_s_completed_time',
                                       store=True)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(SPosOrderPayment, self).fields_get(allfields, attributes)
        hide_list = ['partner_id']
        user = self.env.user
        user_group_has_access = [user.has_group('advanced_sale.s_boo_group_administration'),
                                 user.has_group('advanced_sale.s_boo_group_area_manager'),
                                 user.has_group('advanced_sale.s_boo_group_ecom')]
        user_group_thu_ngan = user.has_group('advanced_sale.s_boo_group_thu_ngan')
        if user_group_thu_ngan and not any(user_group_has_access):
            for field in hide_list:
                if res.get(field):
                    res[field]['exportable'] = False
        return res

    @api.depends('pos_order_id')
    def _compute_s_completed_time(self):
        for rec in self:
            if rec.pos_order_id:
                rec.s_completed_time = rec.pos_order_id.date_order

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(SPosOrderPayment, self)._order_fields(ui_order)
        order_fields['payment_note'] = ui_order.get('payment_note')
        return order_fields

    def create(self, vals_list):
        res = super(SPosOrderPayment, self).create(vals_list)
        if res.s_gift_card_id:
            res.s_gift_card_id.sudo().write({
                'is_used_gift_card': True
            })

    # @api.depends('pos_order_id')
    # def _compute_s_gift_card_id(self):
    #     for rec in self:
    #         rec.s_gift_card_id = None
    #         if rec.pos_order_id:
    #             gift_card_lines = rec.pos_order_id.lines.filtered(lambda l: l.is_line_gift_card)
    #             if len(gift_card_lines) > 0:
    #                 rec.s_gift_card_id = gift_card_lines[0].gift_card_id.id
