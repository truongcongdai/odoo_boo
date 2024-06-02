from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'
    loyalty_points = fields.Float(
        string='Loyalty points', compute="_compute_payment_sate", store=True)

    # @api.depends('payment_state')
    # def _compute_payment_sate(self):
    #     for rec in self:
    #         sale_id = self.env['sale.order'].sudo().search([('invoice_ids', 'in', rec.ids)], limit=1)
    #         if rec.partner_id and len(rec.pos_order_ids) == 0 and rec.payment_state == 'paid' and sale_id:
    #             s_order_history_point = self.env['s.order.history.points'].sudo()
    #             s_order_history_point_id = s_order_history_point.search_count([('sale_order_id', '=', sale_id.id)])
    #             if s_order_history_point_id == 0:
    #                 s_so_loyalty_points_id = self.env['s.sale.order.loyalty.program'].sudo().search([], limit=1)
    #                 if s_so_loyalty_points_id:
    #                     loyalty_points = round(rec.amount_total / float(s_so_loyalty_points_id.s_points_currency), 6)
    #                     rec.loyalty_points = loyalty_points
    #                     rec.partner_id.write({
    #                         'loyalty_points': rec.partner_id.loyalty_points + rec.loyalty_points
    #                     })
    #                     sale_order_id = self.env['sale.order'].search([('name', '=', rec.invoice_origin)])
    #                     if sale_order_id:
    #                         self.env['s.order.history.points'].sudo().create([{
    #                             'sale_order_id': sale_order_id.id,
    #                             'ly_do': 'Điểm trên đơn hàng ' + rec.invoice_origin,
    #                             'diem_cong': rec.loyalty_points,
    #                             'res_partner_id': rec.partner_id.id
    #                         }])

    def action_switch_invoice_into_refund_credit_note(self):
        if any(move.move_type not in ('in_invoice', 'out_invoice') for move in self):
            raise ValidationError(_("This action isn't available for this document."))

        for move in self:
            if move.invoice_origin:
                sale_id = self.env['sale.order'].sudo().search([('name', '=', move.invoice_origin)], limit=1)
                if len(sale_id) > 0:
                    if sale_id.is_return_order:
                        if move.amount_total < 0:
                            move.amount_total = 0
                        continue
            reversed_move = move._reverse_move_vals({}, False)
            new_invoice_line_ids = []
            for cmd, virtualid, line_vals in reversed_move['line_ids']:
                if not line_vals['exclude_from_invoice_tab']:
                    new_invoice_line_ids.append((0, 0, line_vals))
            if move.amount_total < 0:
                # Inverse all invoice_line_ids
                for cmd, virtualid, line_vals in new_invoice_line_ids:
                    line_vals.update({
                        'quantity': -line_vals['quantity'],
                        'amount_currency': -line_vals['amount_currency'],
                        'debit': line_vals['credit'],
                        'credit': line_vals['debit']
                    })
            move.write({
                'move_type': move.move_type.replace('invoice', 'refund'),
                'invoice_line_ids': [(5, 0, 0)],
                'partner_bank_id': False,
            })
            move.write({'invoice_line_ids': new_invoice_line_ids})
