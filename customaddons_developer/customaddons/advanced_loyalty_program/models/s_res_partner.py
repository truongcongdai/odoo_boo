from odoo import fields, models, api, _
from json import dumps
from urllib.parse import urljoin
from odoo.addons.advanced_integrate_magento.tools.common import invalid_response


class SResPartner(models.Model):
    _inherit = 'res.partner'
    total_period_revenue = fields.Monetary(string='Chi tiêu trong năm (VNĐ)', default=0, tracking=True)
    total_reality_revenue = fields.Monetary(string='Doanh thu thực tế (VNĐ)', default=0)
    # s_point_last_period = fields.Float(string='Điểm thân thiết kỳ trước')
    # s_ranked_last_period = fields.Many2one(string='Hạng khách hàng kỳ trước', comodel_name='s.customer.rank')
    # s_ranked_afer_reset = fields.Many2one(string='Hạng khách hàng sau khi reset', comodel_name='s.customer.rank')

    def write(self, vals):
        res = super(SResPartner, self).write(vals)
        if not self.env.context.get('is_call_api'):
            data_check_sync_m2 = ['total_period_revenue', 'total_reality_revenue', 'loyalty_points', 'customer_ranked']
            if any([key in vals for key in data_check_sync_m2]):
                partner_ids = self.filtered(lambda r: r.type == 'contact')
                if partner_ids:
                    for rec in partner_ids:
                        rec.sudo().write({
                            'is_partner_sync_m2': True
                        })
        return res

    @api.model
    def create_from_ui(self, partner):
        is_create_customer = False
        if not partner.get('id'):
            is_create_customer = True
        res = super(SResPartner, self).create_from_ui(partner)
        if res:
            partner_id = self.sudo().search([('id', '=', res)])
            if partner_id:
                lowest_rank = self.env['s.customer.rank'].sudo().search([]).sorted(key='total_amount')[0]
                if lowest_rank:
                    if is_create_customer:
                        if not partner_id.customer_ranked and not partner_id.related_customer_ranked:
                            partner_id.sudo().write({
                                'customer_ranked': lowest_rank.rank,
                                'related_customer_ranked': lowest_rank.id
                            })
        return res

