from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'
    _rec_name = 'code'
    code = fields.Char()
    _sql_constraints = [
        ('value_company_uniq', 'unique (code, attribute_id)', "You cannot create two values with the same name for the same attribute")
    ]

    name = fields.Char(string='Value', required=True, translate=False)
    # @api.constrains('code')
    # def check_id(self):
    #     for rec in self:
    #         if rec.code:
    #             if self.env['product.attribute.value'].search_count([('code', '=', rec.code)]) > 1:
    #                 raise ValidationError('Trường code không được phép nhập giá trị trùng.')
