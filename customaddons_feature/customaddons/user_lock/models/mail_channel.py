# -*- coding: utf-8 -*-
import werkzeug.urls
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ChannelNoJoinedNoti(models.Model):
    _inherit = 'mail.channel'

    # def channel_join_and_get_info(self):
    #     self.ensure_one()
        # if self.channel_type == 'channel' and not self.email_send:
            # notification = _(
            #     '<div class="o_mail_notification">joined <a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a></div>') % (
            #                self.id, self.name,)
            # self.message_post(body=notification, message_type="notification", subtype="mail.mt_comment")
        # self.action_follow()
        #
        # if self.moderation_guidelines:
        #     self._send_guidelines(self.env.user.partner_id)
        #
        # channel_info = self.channel_info()[0]
        # self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), channel_info)
        # return channel_info