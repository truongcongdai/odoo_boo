from odoo import fields, models, api, _


class SImportCouponCoupon(models.Model):
    _name = 's.import.coupon.coupon'
    _description = 'Description'

    boo_code = fields.Char(string='Boo Code', required=True)
    # expiration_date = fields.Date(
    #     string='Expiration Date',
    #     required=True)
    program_id = fields.Many2one(
        comodel_name='coupon.program',
        string='Program',
        required=True)
    # state = fields.Selection(
    #     string='State',
    #     selection=[('reserved', 'Reserved'), ('pending', 'Pending'), ('sent', 'Sent'),
    #                ('expired', 'Expired'), ('cancel', 'Cancel'), ('new', 'Valid'),
    #                ('used', 'Used')], required=True)

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template for Coupons',
            'template': '/advanced_pos/static/xlsx/template_coupon_coupon.xlsx'
        }]