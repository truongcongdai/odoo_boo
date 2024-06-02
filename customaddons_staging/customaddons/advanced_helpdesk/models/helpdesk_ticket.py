from datetime import datetime
from odoo.osv import expression
from odoo import fields, models, api


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    s_facebook_sender_id = fields.Char()
    s_zalo_sender_id = fields.Char()

    s_partner_channel_id = fields.Many2one('mail.channel', compute='_compute_partner_channel_count',
                                           string="Partner Channel")
    s_partner_channel_count = fields.Integer(string="Channel",
                                             compute='_compute_partner_channel_count')
    user_id = fields.Many2one(
        'res.users', string='Assigned to', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, tracking=True, inverse="_inverse_user_id",
        domain=lambda self: [('groups_id', 'in', self.env.ref('helpdesk.group_helpdesk_user').id)])

    def _inverse_user_id(self):
        if self.user_id:
            self.s_partner_channel_id.s_assign_to = self.user_id
        pass

    @api.depends('s_facebook_sender_id')
    def _compute_partner_channel_count(self):
        for ticket in self:
            domain = []
            partner_channel = self.env['mail.channel']
            if ticket.s_facebook_sender_id:
                domain = expression.OR([domain, [('s_facebook_sender_id', '=', ticket.s_facebook_sender_id)]])
            elif ticket.s_zalo_sender_id:
                domain = expression.OR([domain, [('s_zalo_sender_id', '=', ticket.s_zalo_sender_id)]])
            if domain:
                partner_channel = self.env['mail.channel'].search(domain)
            ticket.s_partner_channel_id = partner_channel
            ticket.s_partner_channel_count = len(partner_channel) if partner_channel else 0

    def action_open_helpdesk_channel(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mail.mail_channel_action_view")
        action.update({
            'domain': [('id', 'in', [self.s_partner_channel_id.id])],
            'context': {'create': False},
        })
        return action

    def cronjob_done_ticket_after_24h(self):
        helpdesk_team = self.env['helpdesk.team'].sudo().search([('s_select_integration', '=', 'facebook')], limit=1)
        if helpdesk_team:
            for ticket in helpdesk_team.ticket_ids:
                date_now = datetime.now()
                check_hours = date_now - ticket.create_date
                if check_hours.days >= 1:
                    ticket.stage_id = self.env.ref('helpdesk.stage_solved').id
