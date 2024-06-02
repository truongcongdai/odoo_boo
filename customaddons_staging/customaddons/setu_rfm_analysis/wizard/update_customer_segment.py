from odoo import fields, models, api
from datetime import datetime
from dateutil import relativedelta


class UpdateCustomerSegment(models.TransientModel):
    _name = 'update.customer.segment'
    _description = "Update Customer Segment"

    def _default_end_date(self):
        past_x_days_sales = '365'
        if past_x_days_sales:
            return datetime.today() - relativedelta.relativedelta(days=int(past_x_days_sales))

    def _get_default_note(self):
        segment = self.env['setu.rfm.segment'].search([], limit=1)

        if segment and segment.calculated_on and segment.from_date and segment.to_date:
            return """
                Past sales history has been taken from %s to %s to calculate RFM segment.
                RFM segment calculation was made last on %s 
            """ % (segment.from_date, segment.to_date, segment.calculated_on)

    date_begin = fields.Date(string='Start Date', required=True, default=_default_end_date)
    date_end = fields.Date(string='End Date', required=True, default=datetime.today())
    note = fields.Text(string="Note", default=_get_default_note)

    def update_customer_segment(self):
        date_end = datetime.today()
        company_ids = self.env['res.company'].sudo().search([])
        calculation_type = 'static'
        if self.env.user.has_group('setu_rfm_analysis.group_dynamic_rules'):
            calculation_type = 'dynamic'
        segment_type = 'company'
        if self.env.user.has_group('setu_rfm_analysis.group_sales_team_rfm'):
            segment_type = 'sales_team'

        query = """
                    Select * from update_customer_rfm_segment('%s',null::date,'%s','%s','%s')
                """ % (str(set(company_ids.ids)), date_end, calculation_type, segment_type)
        #
        # query = """
        #         Select * from update_customer_rfm_segment('{}','%s','%s')
        #     """ % (self.date_begin, self.date_end)
        # print(query)
        self._cr.execute(query)
        for company in company_ids:
            history_date = datetime.today() - relativedelta.relativedelta(days=int(company.segment_history_days))
            history_date = history_date.date()
            history_clean_up_query = f"""delete from rfm_partner_history
                                        where date_changed < '{str(history_date)}' and company_id = {company.id};"""
            self._cr.execute(history_clean_up_query)
