from odoo import fields, models, _, api
from datetime import date
from datetime import datetime


class DisplayOrderData(models.TransientModel):
    _name = 'display.order.line.data'
    date_from = fields.Datetime(string='Từ ngày')
    date_to = fields.Datetime(string='Đến ngày')

    def display_order_line_data(self):
        self._cr.execute("""DELETE FROM order_line_data_report WHERE create_uid = %s""",(self.env.user.id,))
        self._cr.execute("""SELECT * FROM sale_order_line WHERE order_id IN (SELECT id FROM sale_order WHERE sale_order_status ='hoan_thanh'
            AND completed_date >= %s 
            AND completed_date <= %s
        )
        AND coupon_program_id is null 
        AND gift_card_id is null
        AND m2_is_global_discount = FALSE 
        AND is_delivery = FALSE 
        AND is_line_coupon_program = FALSE 
        AND state not in ('draft','cancel')""", (self.date_from, self.date_to,))
        sale_order_lines = self.env.cr.dictfetchall()
        if len(sale_order_lines) > 0:
            for line in sale_order_lines:
                # exist_record = self.env['order.line.data.report'].search([('sale_order_line_id', '=', line.id)])
                # if len(exist_record) == 0:
                order_id = False
                if line.get('order_id'):
                    order_id = self.env['sale.order'].sudo().browse(line.get('order_id'))
                data_sale_order_line = self.get_report_sale_order_line_data(line, order_id)
                if data_sale_order_line:
                    line_data_report = self.env['order.line.data.report'].sudo().create(data_sale_order_line)
                    # if order_id.is_sell_wholesale == True or (order_id.is_sell_wholesale == False and order_id.is_magento_order == False):
                    #     line_data_report.update({
                    #         'pos_name': order_id.pos_name
                    #     })
        # query_pos_order_line = """SELECT * FROM pos_order_line WHERE program_id is null AND coupon_id is null AND create_date >= %s AND create_date <= %s AND m2_is_global_discount = FALSE"""
        self._cr.execute(
            """SELECT * FROM pos_order_line WHERE program_id is null 
            AND coupon_id is null 
            AND is_line_gift_card = FALSE 
            AND is_product_service = FALSE 
            AND order_id IN (SELECT id FROM pos_order WHERE date_order >= %s AND date_order <= %s)""",
            (self.date_from, self.date_to,))
        pos_order_lines = self.env.cr.dictfetchall()
        if len(pos_order_lines) > 0:
            for line in pos_order_lines:
                order_id = False
                if line.get('order_id'):
                    order_id = self.env['pos.order'].sudo().browse(line.get('order_id'))
                data_pos_order_line = self.get_report_pos_order_line_data(line, order_id)
                if data_pos_order_line:
                    self.env['order.line.data.report'].sudo().create(data_pos_order_line)
        action = self.env['ir.actions.act_window']._for_xml_id('advanced_sale.order_data_report_action')
        action['domain'] = [('order_line_create_date', '>=', self.date_from),
                            ('order_line_create_date', '<=', self.date_to)]
        return action

    def get_report_sale_order_line_data(self, line, order):
        if order.is_sell_wholesale:
            order_type = 'ban_buon'
        elif order.is_magento_order:
            order_type = 'online'
        else:
            order_type = 'don_hang'
        vals = {
            'product_id': line.get('product_id'),
            'special_price': line.get('price_unit'),
            'partner_order_id': order.partner_id.id if order and order.partner_id else False,
            'product_qty': line.get('product_uom_qty'),
            'boo_total_discount': line.get('boo_total_discount'),
            'boo_total_discount_percentage': line.get('boo_total_discount_percentage'),
            'price_total': line.get('price_total'),
            'order_code': order.name,
            'sale_person': order.user_id.name,
            'order_type': order_type,
            'qty_delivered': line.get('qty_delivered'),
            'sale_order_line_id': line.get('id'),
            'order_line_create_date': line.get('create_date'),
            'boo_phan_bo_price_total': line.get('boo_phan_bo_price_total'),
        }
        return vals

    def get_report_pos_order_line_data(self, line, order):
        vals = {
            'product_id': line.get('product_id'),
            'special_price': line.get('price_unit'),
            'partner_order_id': order.partner_id.id if order and order.partner_id else False,
            'product_qty': line.get('qty'),
            'boo_total_discount': line.get('boo_total_discount'),
            'boo_total_discount_percentage': line.get('boo_total_discount_percentage'),
            'price_total': float(line.get('price_subtotal_incl')),
            'order_code': order.name,
            'sale_person': order.sale_person_id.name if order.sale_person_id else False,
            'order_type': 'offline',
            'qty_delivered': line.get('qty'),
            'pos_order_line_rp_id': line.get('id'),
            'pos_ref': order.pos_reference if order and order.pos_reference else False,
            'order_line_create_date': line.get('create_date'),
            'boo_phan_bo_price_total': line.get('boo_phan_bo_price_total'),
        }
        return vals
