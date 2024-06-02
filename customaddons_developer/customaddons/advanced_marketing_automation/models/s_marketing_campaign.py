from odoo import models, fields, api
from datetime import datetime


class SMarketingCampaign(models.Model):
    _inherit = 'marketing.campaign'

    s_is_completed_buy = fields.Boolean("Hoàn thành mua hàng")
    apply_order = fields.Selection([
        ('sale_order', 'Sale Order'),
        ('pos_order', 'Pos Order')
    ], string='Áp dụng cho')

    @api.onchange('apply_order')
    def onchange_type_marketing(self):

        if self.apply_order == 'pos_order':
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'pos.order')], limit=1)
            if model_id:
                self.sudo().write({
                    "model_id": model_id.id
                })
                self.sudo().write({
                    "domain": "[['is_order_payment', '=', True], ['is_send_message', '=', False]]"
                })
        elif self.apply_order == 'sale_order':
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'sale.order')], limit=1)
            if model_id:
                self.sudo().write({
                    "model_id": model_id.id
                })
                self.sudo().write({
                    "domain": "[['is_order_done', '=', True], ['is_send_message', '=', False]]"
                })
