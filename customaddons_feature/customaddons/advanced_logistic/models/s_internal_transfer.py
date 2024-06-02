from odoo import fields, models, api


class SInternalTransferInherit(models.Model):
    _inherit = 's.internal.transfer'

    s_total_time_transfer = fields.Float(string='Tổng thời gian')

    # @api.depends('picking_in_ids.date_done')
    # def _compute_total_time_delivery(self):
    #     for rec in self:
    #         rec.s_total_time_transfer = 0
    #         if rec.picking_in_ids and rec.picking_out_ids:
    #             if rec.picking_in_ids[0].date_done and rec.picking_out_ids[0].date_done:
    #                 calculate_timedelta = (rec.picking_in_ids[0].date_done - rec.picking_out_ids[0].date_done)
    #                 days = calculate_timedelta.days
    #                 hours, remainder = divmod(calculate_timedelta.seconds, 3600)
    #                 minutes, seconds = divmod(remainder, 60)
    #                 hours += days * 24
    #                 rec.s_total_time_transfer = str(hours) + ':' + str(minutes)
    #                 b=0



