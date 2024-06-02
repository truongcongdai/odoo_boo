from odoo import api, fields, models, tools, _


class InforCustomer(models.TransientModel):
    _name = "mass.action.infor.customer.shopee"

    s_infor_customer = fields.Many2one('res.partner')
    s_shopee_id_order = fields.Many2one('sale.order')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        partners = self.search(['|', '|', ('name', operator, name), ('phone', operator, name),
                                ('email', operator, name)])  # here you need to pass the args as per your requirement.
        return partners.name_get()

    def s_submit_customer_sale_order(self):
        # if self.s_infor_customer:
        #     if self.s_shopee_id_order:
        #         self._cr.execute("""UPDATE sale_order SET partner_id = %s WHERE id = %s""",
        #                          (self.s_infor_customer.id, self.s_shopee_id_order.id,))
        #         self._cr.execute("""UPDATE stock_picking SET partner_id = %s WHERE sale_id = %s""",
        #                          (self.s_infor_customer.id, self.s_shopee_id_order.id,))

        if self.s_infor_customer:
            if self.s_shopee_id_order:
                self._cr.execute("""
                    UPDATE sale_order 
                    SET partner_id = %s, 
                        partner_invoice_id = %s, 
                        partner_shipping_id = %s     
                    WHERE id = %s
                """, (self.s_infor_customer.id, self.s_infor_customer.id, self.s_infor_customer.id, self.s_shopee_id_order.id,))

                self._cr.execute("""UPDATE stock_picking SET partner_id = %s WHERE sale_id = %s""",
                                 (self.s_infor_customer.id, self.s_shopee_id_order.id,))

