from odoo import api, models, fields
from datetime import datetime


class PosOrder(models.Model):
    _inherit = 'pos.order'

    total_discount = fields.Float(string='Total Discount Test', compute='_compute_total_discount')
    pos_completed_time = fields.Datetime(compute='_compute_pos_completed_time', store=True)

    @api.depends('lines')
    def _compute_total_discount(self):
        for res in self:
            total = 0.0
            if res.lines:
                for line in res.lines:
                    if line.coupon_id or line.program_id:
                        total += abs(line.price_subtotal)
                    if line.discount:
                        total += (line.qty * line.price_unit * line.discount) / 100
                    res.total_discount = total
            else:
                res.total_discount = 0.0

    @api.depends(
        'picking_ids',
        'picking_ids.state',
        'picking_ids.date_done'
    )
    def _compute_pos_completed_time(self):
        for res in self:
            if res.picking_ids and not res.picking_ids.filtered(lambda sp: sp.state != 'done'):
                res.pos_completed_time = max(res.picking_ids.mapped('date_done'))
            else:
                res.pos_completed_time = False

    def _compute_write_date_pos_order(self):
        pos_order_error = []
        pos_order_ids = self.sudo().search([('state', '!=', 'draft'), ('write_date', '<', datetime.strptime(
            "2023-11-21 23:59:59", "%Y-%m-%d %H:%M:%S"))])
        if pos_order_ids:
            # pos_order_ids = pos_order_obj.lines.filtered(lambda line: line.qty != 0).mapped('order_id')
            for pos_order_id in pos_order_ids:
                order_type = 'Order'
                if pos_order_id.is_cancel_order and pos_order_id.refunded_orders_count > 0:
                    order_type = 'Cancel'
                elif not pos_order_id.is_cancel_order and pos_order_id.refunded_orders_count > 0:
                    order_type = 'Return'
                total_bill = 0
                total_discount = 0
                if pos_order_id.lines:
                    if order_type == 'Return' and pos_order_id.write_date > datetime.strptime("2023-04-10 23:59:59",
                                                                                              "%Y-%m-%d %H:%M:%S"):
                        for r in pos_order_id.lines:
                            if r.product_id.detailed_type == 'product':
                                if 0 < r.price_unit < r.product_id.lst_price:
                                    total_bill += r.qty * r.price_unit
                                # if 0 < r.price_unit < r.s_lst_price:
                                #     total_bill += r.qty * r.s_lst_price
                                else:
                                    # total_bill += r.qty * r.price_unit
                                    total_bill += r.qty * r.product_id.lst_price
                                if not r.refunded_orderline_id:
                                    total_discount += r.boo_total_discount_percentage
                            elif r.product_id.detailed_type == 'service':
                                if r.qty < 0 and r.price_unit < 0:
                                    total_bill += r.qty * r.price_unit

                    elif order_type != 'Return' or order_type == 'Return' and pos_order_id.write_date < datetime.strptime(
                            "2023-04-10 23:59:59", "%Y-%m-%d %H:%M:%S"):
                        for r in pos_order_id.lines:
                            if r.product_id.detailed_type == 'product':
                                # if 0 < r.price_unit < r.s_lst_price:
                                #     total_bill += r.qty * r.s_lst_price
                                if 0 < r.price_unit < r.product_id.lst_price:
                                    total_bill += r.qty * r.price_unit
                                else:
                                    # total_bill += r.qty * r.price_unit
                                    total_bill += r.qty * r.product_id.lst_price
                                if r.qty < 0:
                                    total_discount += - (r.boo_total_discount_percentage + r.boo_total_discount)
                                else:
                                    total_discount += r.boo_total_discount_percentage + r.boo_total_discount
                    if total_bill - total_discount != pos_order_id.amount_total and pos_order_id.id not in pos_order_error:
                        pos_order_error.append(pos_order_id.id)
                        pos_order_id.sudo().write({
                            'write_date': datetime.today()
                        })
        if pos_order_error:
            print(pos_order_error)
