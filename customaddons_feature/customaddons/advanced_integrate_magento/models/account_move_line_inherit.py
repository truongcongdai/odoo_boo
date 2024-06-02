from odoo import fields, models, api


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    m2_total_line_discount = fields.Float(
        string='M2 total line discount',
        required=False)
    s_m2_total_line_discount = fields.Float(string='M2 total line discount', compute='_compute_account_move_line', store=True)
    s_price_unit = fields.Float(string='Đơn giá', compute='_compute_account_move_line', store=True)
    check_compute_account_move_line = fields.Boolean(string='Tình trạng compute dòng hóa đơn', default=False, compute='_compute_account_move_line', store=True)

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
                                            move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}
        # if self.m2_total_line_discount:
        #     if self.s_price_unit > price_unit:
        #         line_discount_price_unit = self.s_price_unit * (
        #                 1 - (discount / 100.0)) - self.m2_total_line_discount
        #     else:
        #         line_discount_price_unit = price_unit * (
        #                 1 - (discount / 100.0)) - self.m2_total_line_discount
        # else:
        #     line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))

        # try:
        #     if self.m2_total_line_discount:
        #         line_discount_price_unit = price_unit * (
        #                 1 - (discount / 100.0)) - self.m2_total_line_discount
        #     else:
        #         line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        # except Exception:
        #     line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        # Compute 'price_subtotal'.

        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                                                                             quantity=quantity, currency=currency,
                                                                             product=product, partner=partner,
                                                                             is_refund=move_type in (
                                                                             'out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    # @api.depends('product_id.lst_price')
    # def _compute_product_id_price(self):
    #     for r in self:
    #         r.s_price_unit = r.product_id.lst_price

    @api.depends('product_id')
    def _compute_account_move_line(self):
        account_move_line_ids = self.filtered(
            lambda a: a.check_compute_account_move_line == False and a.product_id.detailed_type == 'product')
        if len(account_move_line_ids):
            for r in account_move_line_ids:
                for order_line in r.sale_line_ids:
                    if order_line.product_id.id == r.product_id.id:
                        r.s_price_unit = order_line.price_unit
                        if order_line.order_id.payment_method == 'cod':
                            r.s_m2_total_line_discount = order_line.m2_total_line_discount * order_line.qty_delivered / order_line.product_uom_qty
                        else:
                            r.s_m2_total_line_discount = order_line.m2_total_line_discount
                        r.check_compute_account_move_line = True
