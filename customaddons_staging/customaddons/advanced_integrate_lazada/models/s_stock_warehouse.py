from odoo import fields, models, api
from odoo.exceptions import ValidationError


class SStockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    e_commerce = fields.Selection(selection_add=[('lazada', 'Lazada')])
    is_push_lazada = fields.Boolean('Đã đồng bộ lên sàn TMĐT Lazada', compute="_compute_e_commerce", store=True)

    @api.constrains("e_commerce", "is_push_lazada")
    def _check_e_commerce(self):
        search_count = self.sudo().search_count(
            ['|', ('e_commerce', '=', 'lazada'), ('is_push_lazada', '=', True)])
        if search_count > 1:
            raise ValidationError('Kho của sàn TMĐT Lazada đã tồn tại.')

    @api.depends('e_commerce')
    def _compute_e_commerce(self):
        for r in self:
            r.is_push_lazada = False
            if r.e_commerce == 'lazada':
                r.is_push_lazada = True
