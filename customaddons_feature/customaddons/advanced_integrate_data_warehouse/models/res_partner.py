from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    membership_code = fields.Char(string='Mã khách hàng')
    total_sales_amount = fields.Integer(string='Tổng giá trị các đơn đã mua',compute='_compute_total_sales_amount')
    total_sale_products_qty = fields.Integer(string='Tổng số sản phẩm',compute='_compute_total_sale_products_qty')

    def _update_s_pos_order_id(self):
        for rec in self.env.context.get('active_ids'):
            partner_id = self.browse(rec)
            customer_obj = self.env['pos.config'].search([('name', 'ilike', partner_id.pos_create_customer)], limit=1)
            if customer_obj:
                partner_id.s_pos_order_id = customer_obj.id

    def _get_amount_so_invoice(self, sale_order_ids):
        amount_total = 0
        if len(sale_order_ids) > 0:
            for order in sale_order_ids:
                if order.invoice_ids:
                    for invoice in order.invoice_ids:
                        if invoice.payment_state in ['paid', 'partial']:
                            amount_total += invoice.amount_total - invoice.amount_residual
        return amount_total

    def _get_amount_so(self, sale_order_ids):
        amount_total = 0
        if len(sale_order_ids) > 0:
            for order in sale_order_ids:
                if order.sale_order_status == 'hoan_thanh':
                    amount_total += order.amount_total
                elif order.sale_order_status == 'hoan_thanh_1_phan':
                    if order.order_line:
                        for line in order.order_line:
                            if 0 < line.price_unit < line.s_lst_price:
                                amount_total += round(line.s_lst_price) * line.qty_delivered - (
                                        round(int(line.boo_total_discount_percentage)) + round(
                                    int(line.boo_total_discount))) * line.qty_delivered / line.product_uom_qty
                            else:
                                amount_total += round(line.price_unit) * line.qty_delivered - (
                                        round(int(line.boo_total_discount_percentage)) + round(
                                    int(line.boo_total_discount))) * line.qty_delivered / line.product_uom_qty

        return amount_total

    def _get_amount_pos_order(self, pos_order_ids):
        amount_pos_order = 0
        if len(pos_order_ids) > 0:
            for pos in pos_order_ids:
                amount_pos_order += pos.amount_total
        return amount_pos_order

    def _compute_total_sales_amount(self):
        for rec in self:
            pos_order_ids = rec.pos_order_ids.filtered(lambda am: am.state == 'paid' or am.state == 'invoiced')
            sale_order_invoiced = self._get_amount_so(rec.sale_order_ids)
            amount_pos_order = self._get_amount_pos_order(pos_order_ids)
            rec.total_sales_amount = amount_pos_order + sale_order_invoiced

    def _compute_total_sale_products_qty(self):
        for rec in self:
            product_total = 0
            sale_order_line_obj = self.env['sale.order.line'].search([('order_partner_id', '=', rec.id)])
            if sale_order_line_obj:
                # for product_so in sale_order_line_obj:
                #     product_so_obj = self.env['product.product'].search([('id', '=', product_so.product_id.id)])
                #     if product_so_obj:
                product_total += len(sale_order_line_obj.mapped('product_id').ids)
            pos_order_obj = self.env['pos.order'].search([('partner_id', '=', rec.id)])
            if pos_order_obj:
                for po_order_line in pos_order_obj:
                    pos_order_line_obj = self.env['pos.order.line'].search([('order_id', '=', po_order_line.id)])
                    if pos_order_line_obj:
                        # for product_po in pos_order_line_obj:
                        #     product_po_obj = self.env['product.product'].search([('id', '=', product_po.product_id.id)])
                        #     if product_po_obj:
                        product_total += len(pos_order_line_obj.mapped('product_id').ids)
            rec.total_sale_products_qty = product_total
