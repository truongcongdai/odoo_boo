from odoo import fields, models, api


class MassInsertCouponProgram(models.TransientModel):
    _name = 'mass.insert.pricelist'
    pricelist_id = fields.Many2one(comodel_name='product.pricelist', string='Bảng giá')
    pos_ids = fields.Many2many(comodel_name='pos.config', string='Cửa hàng')

    def confirm_pricelist(self):
        for pos in self.pos_ids:
            pos.write({'pricelist_id': self.pricelist_id})
