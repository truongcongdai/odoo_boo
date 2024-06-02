from odoo import models, fields, api

class SCouponProgram(models.Model):
    _inherit = 'coupon.program'

    is_vani_coupon_program = fields.Boolean(string='Là CTKM của Vani')