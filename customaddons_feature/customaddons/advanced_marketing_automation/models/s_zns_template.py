from odoo import fields, models


class ZnsTemplate(models.Model):
    _name = 'zns.template'
    _description = 'ZNS Template'

    name = fields.Char('Tên ZNS Template')
    s_template_id = fields.Integer("ID Zns Template")



