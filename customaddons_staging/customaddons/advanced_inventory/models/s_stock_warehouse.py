from odoo import models, fields,api

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    pos_config_ids = fields.One2many('pos.config', 'warehouse_id_related')
    employee_ids = fields.Many2many('hr.employee', string="Nhân viên", compute='_compute_employee_ids', store=True)
    code = fields.Char(size=255)


    @api.depends('pos_config_ids','pos_config_ids.employee_ids','pos_config_ids.warehouse_id_related')
    def _compute_employee_ids(self):
        for rec in self:
            list_employee = []
            for pos in rec.pos_config_ids:
                list_employee.extend(pos.employee_ids.ids)
            rec.employee_ids = [(6, 0, list_employee)]




