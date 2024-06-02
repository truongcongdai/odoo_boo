from odoo import fields, models, api


class SHelpdeskTicketQueue(models.Model):
    _name = 's.helpdesk.ticket.queue'

    name = fields.Char('Name')
    s_facebook_sender_id = fields.Char()
    s_zalo_sender_id = fields.Char()
    s_partner_channel_id = fields.Many2one('mail.channel', string="Partner Channel")
    s_partner_channel_count = fields.Integer(string="Channel")
    user_id = fields.Many2one('res.users', string='Assigned to')
    team_id = fields.Integer()
    message_text = fields.Char()

    def cron_create_helpdesk_tickets(self):
        helpdesk_ticket_ids = self.sudo().search([], limit=10000)
        if helpdesk_ticket_ids:
            for helpdesk_ticket_id in helpdesk_ticket_ids:
                helpdesk_ticket_queue_id = False
                new_ticket_id = False
                mail_channel_id = False

                if helpdesk_ticket_id.s_facebook_sender_id:
                    helpdesk_ticket_queue_id = self.sudo().search([
                        ('s_facebook_sender_id', '=', helpdesk_ticket_id.s_facebook_sender_id),
                        ('name', '=', helpdesk_ticket_id.name)], limit=1)
                    mail_channel_id = self.env['mail.channel'].sudo().search(
                        [('s_facebook_sender_id', '=', helpdesk_ticket_id.s_facebook_sender_id)], limit=1)
                elif helpdesk_ticket_id.s_zalo_sender_id:
                    helpdesk_ticket_queue_id = self.sudo().search([
                        ('s_zalo_sender_id', '=', helpdesk_ticket_id.s_zalo_sender_id),
                        ('name', '=', helpdesk_ticket_id.name)], limit=1)
                    mail_channel_id = self.env['mail.channel'].sudo().search(
                        [('s_zalo_sender_id', '=', helpdesk_ticket_id.s_zalo_sender_id)], limit=1)

                if helpdesk_ticket_queue_id:
                    helpdesk_ticket_data = {
                        'name': helpdesk_ticket_id.name,
                        's_facebook_sender_id': helpdesk_ticket_id.s_facebook_sender_id,
                        's_zalo_sender_id': helpdesk_ticket_id.s_zalo_sender_id,
                        'team_id': helpdesk_ticket_id.team_id
                    }
                    new_ticket_id = self.env['helpdesk.ticket'].sudo().create(helpdesk_ticket_data)

                if mail_channel_id and new_ticket_id:
                    mail_channel_id.channel_last_seen_partner_ids.unlink()
                    write_channel = {
                        's_assign_to': new_ticket_id.user_id.id
                    }
                    if mail_channel_id.s_facebook_sender_id != helpdesk_ticket_id.s_facebook_sender_id:
                        write_channel.update({
                            's_facebook_sender_id': helpdesk_ticket_id.s_facebook_sender_id,
                            'name': helpdesk_ticket_id.name
                        })
                    if mail_channel_id.s_assign_to.partner_id not in mail_channel_id.channel_last_seen_partner_ids.partner_id:
                        if mail_channel_id.channel_last_seen_partner_ids:
                            mail_channel_id.channel_last_seen_partner_ids.unlink()
                        write_channel.update({
                            'channel_last_seen_partner_ids': [
                                (0, 0, {'partner_id': new_ticket_id.user_id.partner_id.id}), ]
                        })
                    mail_channel_id.sudo().write(write_channel)
                    partner_id = self.env['res.partner'].sudo().search([
                        ('s_facebook_sender_id', '=', helpdesk_ticket_id.s_facebook_sender_id)], limit=1)
                    mail_channel_id.message_post(
                        partner_ids=mail_channel_id.s_assign_to.commercial_partner_id.ids,
                        body=helpdesk_ticket_queue_id.message_text, author_id=partner_id.id)

                helpdesk_ticket_queue_id.unlink()
