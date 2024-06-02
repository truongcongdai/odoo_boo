from odoo import models, fields, api


class SHrEmployee(models.Model):
    _inherit = 'hr.employee'

    cv = fields.Binary(string='CV', groups="advanced_sale.s_boo_group_hr")
    so_yeu_li_lich = fields.Binary(string='Sơ yếu lý lịch', groups="advanced_sale.s_boo_group_hr")
    cccd = fields.Binary(string='Căn cước công dân', groups="advanced_sale.s_boo_group_hr")
    hop_dong = fields.Binary(string='Hợp đồng lao động', groups="advanced_sale.s_boo_group_hr")
    bao_hiem_xa_hoi = fields.Binary(string='Bảo hiểm xã hội', groups="advanced_sale.s_boo_group_hr")
    bang_cap = fields.Binary(string='Bằng cấp', groups="advanced_sale.s_boo_group_hr")
    khac = fields.Binary(string='Khác', groups="advanced_sale.s_boo_group_hr")
