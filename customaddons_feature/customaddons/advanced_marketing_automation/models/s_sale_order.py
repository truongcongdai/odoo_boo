from datetime import datetime, timedelta
from odoo import models, fields, api


class SSaleOrder(models.Model):
    _inherit = 'sale.order'
    is_order_done = fields.Boolean(string='Là đơn hàng đã hoàn thành', compute='_compute_sale_order_status', store=True)
    is_send_message = fields.Boolean(string='Là đơn hàng đã gửi tin nhắn', default=False)
    send_message_error = fields.Boolean(string='Gửi Zns lỗi', default=False)
    is_so_not_done_do = fields.Boolean(string='Là đơn hàng chưa hoàn thành DO Return', default=False,
                                       compute='_compute_sale_order_status', store=True)

    @api.depends('sale_order_status')
    def _compute_sale_order_status(self):
        for r in self:
            r.sudo().is_order_done = False
            r.sudo().is_so_not_done_do = False
            if r.sale_order_status in ['hoan_thanh_1_phan', 'hoan_thanh']:
                r.is_order_done = True
                if r.sale_order_status in ['hoan_thanh_1_phan']:
                    picking_ids = r.picking_ids.filtered(
                        lambda p: p.state in ['draft', 'confirmed', 'assigned', 'waiting'])
                    if len(picking_ids) > 0:
                        r.sudo().is_so_not_done_do = True

    @api.model
    def create(self, vals):
        res = super(SSaleOrder, self).create(vals)
        if res.partner_id and not res.partner_id.check_buy_order:
            res.partner_id.check_buy_order = True
        return res

    def write(self, vals):
        if vals.get('is_send_message'):
            for r in self:
                self._cr.execute(
                    """UPDATE sale_order SET is_send_message = %s WHERE id = %s""",
                    (vals.get('is_send_message'), r.id))
            vals.pop('is_send_message')
        else:
            return super(SSaleOrder, self).write(vals)
