from odoo import models, fields,api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    code = fields.Char()
    first_working_day = fields.Date(string='Ngày đầu đi làm')
    employee_code = fields.Char(string='Mã nhân viên')

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template Nhân viên',
            'template': '/advanced_integrate_data_warehouse/static/xlsx/import_template_employee.xlsx'
        }]
