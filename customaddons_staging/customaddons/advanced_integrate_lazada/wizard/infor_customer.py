from odoo import fields, models, api


class InforCusomer(models.TransientModel):
    _name = "infor.customer"

    order_id = fields.Many2one('sale.order', readonly=True)
    name = fields.Char("Tên khách hàng")
    phone = fields.Char("Điện thoại")
    street = fields.Char("Địa chỉ")

    @api.model
    def default_get(self, fields):
        res = super(InforCusomer, self).default_get(fields)
        res['order_id'] = self.env.context.get('active_id')
        return res

    def btn_confirm(self):
        value = {
            "sale_order_ids": self.order_id,
            "name": self.name,
            "phone": self.phone,
            "street": self.street,
        }
        partner_id = self.order_id.partner_id.create(value)
        if self.order_id.picking_ids:
            for picking_id in self.order_id.picking_ids:
                picking_id.write({
                    "partner_id": partner_id.id
                })