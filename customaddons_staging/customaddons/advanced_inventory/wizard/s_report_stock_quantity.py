from odoo import fields, models


class SDisplayReportStockQuantity(models.Model):
    _name = 's.display.report.stock.quantity'
    product_id = fields.Many2one('product.product', string='Sản Phẩm')

    def display_report_stock_quantity_data(self):
        action = self.env['ir.actions.act_window']._for_xml_id('stock.report_stock_quantity_action')
        action['context'] = {'search_default_filter_forecast': 1, 'search_default_product_id': self.product_id.id}
        return {
            'name': 'Dự báo tồn kho',
            'type': 'ir.actions.act_window',
            'view_mode': 'grid',
            'res_model': 'report.stock.quantity',
            'target': 'current',
            'context': action['context']
        }