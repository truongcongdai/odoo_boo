from odoo import fields, models, api


class productPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template Bảng giá',
            'template': '/advanced_pos/static/xlsx/template-bang-gia-diem-ban-hang.xlsx'
        }]
