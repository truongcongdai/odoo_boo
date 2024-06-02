import traceback

from odoo import fields, models, api
import time
import logging

_logger = logging.getLogger(__name__)


class sUpdateLoyaltyPoints(models.Model):
    _name = 's.update.loyalty.points'
    _description = 'Description'

    phone = fields.Char(
        string='Phone', )
    points = fields.Integer(
        string='Điểm', )
    total_period_revenue = fields.Float(
        string='Chi tieu trong nam')

    def mass_action_update_loyalty_points(self):
        start_time = time.time()
        try:
            self._cr.execute(
                """SELECT id,phone,points,total_period_revenue FROM s_update_loyalty_points WHERE phone IN (SELECT phone FROM res_partner WHERE phone is not null)""", )
            query_result = self.env.cr.dictfetchall()
            limit_update_loyalty_points = self.env['ir.config_parameter'].get_param(
                'advanced_address.limit_update_loyalty_points', 10)
            count = 0
            while count < 10 and (time.time() - start_time) < 50:
                count += 1
                for rec in query_result[:int(limit_update_loyalty_points)]:
                    if rec.get('phone'):
                        partner_id = self.env['res.partner'].sudo().search(
                            [('phone', '=', rec.get('phone'))],
                            limit=1)
                        if partner_id:
                            partner_id.write({'loyalty_points': 0,
                                              'total_period_revenue': rec.get('total_period_revenue')})
                            self.env['s.update.loyalty.points'].sudo().browse(rec.get('id')).unlink()
                            self.env.cr.commit()
        except Exception as ex:
            error = traceback.format_exc()
            _logger.error('mass_action_update_loyalty_points')
            _logger.error(error)
