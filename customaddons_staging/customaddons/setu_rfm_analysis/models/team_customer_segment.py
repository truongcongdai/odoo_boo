from odoo import fields, models, api, _
from datetime import datetime
from dateutil import relativedelta


class TeamCustomerSegment(models.Model):
    _name = "team.customer.segment"
    _description = "Sales team wise customer segmentation"

    team_id = fields.Many2one(comodel_name="crm.team", string="Sales team", ondelete='cascade')
    rfm_segment_id = fields.Many2one(comodel_name='setu.rfm.segment', string="RFM Segment", ondelete='cascade')
    total_orders = fields.Integer(string="Total Orders", compute='_compute_customers')
    total_revenue = fields.Float(string="Total Revenue", compute='_compute_customers')

    def _compute_customers(self):
        for team_segment in self:
            company = self.env.user.company_id
            past_x_days_sales = company.take_sales_from_x_days or 365
            from_date = datetime.today() - relativedelta.relativedelta(days=int(past_x_days_sales))
            to_date = datetime.today()
            if team_segment.rfm_segment_id:
                if team_segment.rfm_segment_id.is_template:
                    domain = [('rfm_segment_id', '=', team_segment.rfm_segment_id.id),
                              ('team_id', '=', team_segment.team_id.id)]
                else:
                    domain = [('rfm_team_segment_id', '=', team_segment.rfm_segment_id.id)]
                orders = self.env['sale.order'].search(domain).filtered(
                    lambda order: from_date < order.date_order <= to_date)

                # orders = team_segment.rfm_segment_id.partner_ids.mapped('sale_order_ids').filtered(lambda order: order.date_order > from_date and order.date_order <= to_date and order.state not in ('draft', 'sent', 'cancel') and order.team_id == team_segment.team_id.id)
                team_segment.total_orders = len(orders.ids)
                team_segment.total_revenue = sum(orders.mapped('amount_total'))
