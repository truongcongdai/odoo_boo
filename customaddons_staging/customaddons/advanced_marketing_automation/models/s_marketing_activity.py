from odoo import fields, models, api, _
import re
from odoo.fields import Datetime
import threading

class SMarketingActivity(models.Model):
    _inherit = 'marketing.activity'

    s_is_zalo_sms_marketing = fields.Boolean("Zalo")
    s_is_zalo_activity = fields.Boolean(string="Zalo")
    s_mass_mailing_zalo_id = fields.Many2one('mailing.mailing', string='Marketing Template',
                                             domain="[('use_in_marketing_automation', '=', True)]")


    @api.onchange("s_mass_mailing_zalo_id")
    def _onchange_sms_mass_mailing_id(self):
        if self.s_mass_mailing_zalo_id:
            self.mass_mailing_id = self.s_mass_mailing_zalo_id.id

    @api.depends('activity_type')
    def _compute_mass_mailing_id_mailing_type(self):
        for activity in self:
            if activity.activity_type == 'sms' or activity.s_is_zalo_activity == True :
                activity.mass_mailing_id_mailing_type = 'sms'
        super(SMarketingActivity, self)._compute_mass_mailing_id_mailing_type()

    @api.onchange('s_is_zalo_activity')
    def _onchange_s_is_zalo_activity(self):
        self.mass_mailing_id = False
        self.s_mass_mailing_zalo_id = False

    def _action_view_documents_filtered(self, view_filter):
        if not self.mass_mailing_id:  # Only available for mass mailing
            return False
        action = self.env["ir.actions.actions"]._for_xml_id("marketing_automation.marketing_participants_action_mail")

        if view_filter in ('reply', 'bounce'):
            found_traces = self.trace_ids.filtered(lambda trace: trace.mailing_trace_status == view_filter)
        elif view_filter == 'sent':
            found_traces = self.trace_ids.filtered(
                lambda trace: trace.mailing_trace_ids.filtered(lambda t: t.sent_datetime))
        elif view_filter == 'click':
            found_traces = self.trace_ids.filtered(
                lambda trace: trace.mailing_trace_ids.filtered(lambda t: t.links_click_datetime))
        else:
            found_traces = self.env['marketing.trace']

        participants = found_traces.participant_id
        action.update({
            'display_name': _('Participants of %s (%s)') % (self.name, view_filter),
            'domain': [('id', 'in', participants.ids)],
            'context': dict(self._context, create=False)
        })
        return action

    def execute(self, domain=None):
        # auto-commit except in testing mode
        auto_commit = not getattr(threading.currentThread(), 'testing', False)
        trace_domain = [
            ('schedule_date', '<=', Datetime.now()),
            ('state', '=', 'scheduled'),
            ('activity_id', 'in', self.ids),
            ('participant_id.state', '=', 'running'),
        ]
        if domain:
            trace_domain += domain
        limit_traces = int(self.env['ir.config_parameter'].sudo().get_param('advanced_marketing_automation.limit_traces', 10000))
        traces = self.env['marketing.trace'].search(trace_domain, limit=limit_traces)

        # organize traces by activity
        trace_to_activities = dict()
        for trace in traces:
            if trace.activity_id not in trace_to_activities:
                trace_to_activities[trace.activity_id] = trace
            else:
                trace_to_activities[trace.activity_id] |= trace

        # execute activity on their traces
        BATCH_SIZE = 500  # same batch size as the MailComposer

        for activity, traces in trace_to_activities.items():
            for traces_batch in (traces[i:i + BATCH_SIZE] for i in range(0, len(traces), BATCH_SIZE)):
                activity.execute_on_traces(traces_batch)
                if auto_commit:
                    self.env.cr.commit()
