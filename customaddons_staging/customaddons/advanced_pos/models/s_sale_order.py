from odoo import fields, models, api, _


class SSaleOrder(models.Model):
    _inherit = 'sale.order'

    s_facebook_sender_id = fields.Char(string='Id Sender Facebook',
                                       required=False)
    s_zalo_sender_id = fields.Char(string='Id Sender Zalo',
                                   required=False)

class SSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def check_return_sale_order_line(self):
        for rec in self:
            refunded_orderline_id = self.env['sale.order.line'].search([('refunded_orderline_id', '=', rec.id)])
            if len(refunded_orderline_id) > 0:
                return True
