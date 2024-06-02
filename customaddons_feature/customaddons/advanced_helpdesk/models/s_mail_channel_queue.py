from odoo import fields, models, api


class SMailChannelQueue(models.Model):
    _name = 's.mail.channel.queue'

    s_facebook_sender_id = fields.Char()
    s_facebook_message = fields.Char()
    s_fb_message_id = fields.Char()
    s_zalo_sender_id = fields.Char()
    s_zalo_message = fields.Char()
    s_zalo_message_id = fields.Char()

    def cron_create_mail_channel(self):
        # query_product_product = self._cr.execute("""select id from s_mail_channel_queue""",)
        # product_details = [item[0] for item in self._cr.fetchall()]
        # mail_channel_ids = self.browse(product_details)
        mail_channel_queue_ids = self.search([], limit=50)
        if len(mail_channel_queue_ids) > 0:
            for rec in mail_channel_queue_ids:
                if rec.s_facebook_sender_id:
                    facebook_mail_channel_id = self.env['mail.channel'].sudo().search(
                        [('s_facebook_sender_id', '=', rec.s_facebook_sender_id)], limit=1)
                    facebook_partner_id = self.env['res.partner'].sudo().search(
                        [('s_facebook_sender_id', '=', rec.s_facebook_sender_id)], limit=1)
                    facebook_ticket_id = facebook_mail_channel_id.s_channel_ticket_ids.filtered(
                        lambda r: r.stage_id not in [self.env.ref('helpdesk.stage_solved'),
                                                     self.env.ref('helpdesk.stage_cancelled')])
                    if not facebook_mail_channel_id or not facebook_partner_id or not facebook_ticket_id:
                        self.env['mail.channel'].sudo().create_mail_channel_facebook(
                            s_facebook_sender_id=rec.s_facebook_sender_id, message_text=rec.s_facebook_message,s_fb_message_id=rec.s_fb_message_id)
                    else:
                        search_fb_message_id = self.env['mail.message'].search(
                            [('s_helpdesk_message_id', '=', rec.s_fb_message_id)], limit=1)
                        if not search_fb_message_id:
                            facebook_mail_channel_id.message_post(
                                partner_ids=facebook_mail_channel_id.s_assign_to.commercial_partner_id.ids,
                                body=rec.s_facebook_message, author_id=facebook_partner_id.id, s_helpdesk_message_id=rec.s_fb_message_id)
                elif rec.s_zalo_sender_id:
                    zalo_mail_channel_id = self.env['mail.channel'].sudo().search(
                        [('s_zalo_sender_id', '=', rec.s_zalo_sender_id)], limit=1)
                    zalo_partner_id = self.env['res.partner'].sudo().search(
                        [('s_zalo_sender_id', '=', rec.s_zalo_sender_id)], limit=1)
                    zalo_ticket_id = zalo_mail_channel_id.s_channel_ticket_ids.filtered(
                        lambda r: r.stage_id not in [self.env.ref('helpdesk.stage_solved'),
                                                     self.env.ref('helpdesk.stage_cancelled')])
                    if not zalo_mail_channel_id or not zalo_partner_id or not zalo_ticket_id:
                        self.env['mail.channel'].sudo().create_channel_ticket_zalo(
                            s_zalo_sender_id=rec.s_zalo_sender_id, s_zalo_message=rec.s_zalo_message,s_zalo_message_id=rec.s_zalo_message_id)
                    else:
                        search_zalo_message_id = self.env['mail.message'].search(
                            [('s_helpdesk_message_id', '=', rec.s_zalo_message_id)], limit=1)
                        if not search_zalo_message_id:
                            zalo_mail_channel_id.message_post(
                                partner_ids=zalo_mail_channel_id.s_assign_to.commercial_partner_id.ids,
                                body=rec.s_zalo_message, author_id=zalo_partner_id.id,s_helpdesk_message_id=rec.s_zalo_message_id)
                rec.unlink()
