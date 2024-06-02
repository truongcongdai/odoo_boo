from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    boo_warehouse_ids = fields.Many2many('stock.warehouse', compute='_compute_boo_location_ids')

    def _compute_boo_location_ids(self):
        for rec in self:
            employee_ids = rec.employee_ids.ids
            list_wh = []
            warehouses = self.env['stock.warehouse'].sudo().search([])
            for warehouse in warehouses:
                new_list = warehouse.employee_ids.ids
                if set(employee_ids).issubset(new_list):
                    list_wh.append(warehouse.id)
            rec.boo_warehouse_ids = [(6, 0, list_wh)]
        return
    #
    # employee_ids = fields.Many2many('hr.employee', string="Nhân viên", compute='_compute_employee_ids', store=True)
    # code = fields.Char(size=255)
    #
    # @api.depends('pos_config_ids', 'pos_config_ids.employee_ids', 'pos_config_ids.warehouse_id_related')
    # def _compute_employee_ids(self):
    #     for rec in self:
    #         list_employee = []
    #         for pos in rec.pos_config_ids:
    #             list_employee.extend(pos.employee_ids.ids)
    #         rec.employee_ids = [(6, 0, list_employee)]
    #
