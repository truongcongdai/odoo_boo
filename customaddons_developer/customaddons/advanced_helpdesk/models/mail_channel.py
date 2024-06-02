import base64
from datetime import date
import urllib.parse
import requests
from odoo import fields, models, api
from odoo.exceptions import ValidationError, _logger
from werkzeug.urls import url_encode
from odoo.http import request


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    s_partner_id = fields.Many2one(comodel_name='res.partner', string='Khách hàng')
    s_facebook_sender_id = fields.Char()
    s_zalo_sender_id = fields.Char()
    s_assign_to = fields.Many2one("res.users", string="Assign to", inverse="_inverse_assign_to")
    s_channel_ticket_ids = fields.One2many('helpdesk.ticket', 's_partner_channel_id')
    s_source_id = fields.Many2one(comodel_name='utm.source')

    @api.constrains('s_assign_to')
    def _constrains_assign_to(self):
        if self.s_assign_to:

            if self.s_assign_to.id not in self.env.ref('advanced_helpdesk.group_customer_care').users.ids:
                self.env.ref('advanced_helpdesk.group_customer_care').users = [(4, self.s_assign_to.id)]
            if self.s_assign_to.partner_id not in self.channel_last_seen_partner_ids.partner_id:
                if self.channel_last_seen_partner_ids:
                    self.channel_last_seen_partner_ids.unlink()
                write_channel = {
                    'channel_last_seen_partner_ids': [
                        (0, 0, {'partner_id': self.s_assign_to.partner_id.id}), ]
                }
                self.sudo().write(write_channel)

    def _inverse_assign_to(self):
        if self.s_assign_to:
            stage = (self.env.ref('helpdesk.stage_solved').id, self.env.ref('helpdesk.stage_cancelled').id)
            self.s_channel_ticket_ids.filtered(lambda r: r.stage_id.id not in stage).user_id = self.s_assign_to
        pass

    def channel_info(self):
        channel_infos = super().channel_info()
        channel_infos_dict = dict((c['id'], c) for c in channel_infos)
        for channel in self:
            if channel.channel_type == 'channel':
                if channel.s_facebook_sender_id:
                    channel_infos_dict[channel.id]['s_facebook_sender_id'] = channel.s_facebook_sender_id
                    channel_infos_dict[channel.id]['s_source_id'] = self.env.ref('utm.utm_source_facebook').id
                if channel.s_zalo_sender_id:
                    channel_infos_dict[channel.id]['s_zalo_sender_id'] = channel.s_zalo_sender_id
                    channel_infos_dict[channel.id]['s_source_id'] = self.env.ref('advanced_helpdesk.utm_source_zalo').id
                if channel.s_partner_id:
                    channel_infos_dict[channel.id]['s_partner_id'] = channel.s_partner_id.id
        return list(channel_infos_dict.values())

    def create_mail_channel_facebook(self, s_facebook_sender_id, message_text, s_fb_message_id):
        search_helpdesk = self.env['helpdesk.team'].sudo().search([('s_select_integration', '=', 'facebook')], limit=1)
        if search_helpdesk:
            url = "https://graph.facebook.com/%s" % s_facebook_sender_id
            params = dict(
                fields='name,gender',
                access_token=self.env['ir.config_parameter'].sudo().get_param(
                    'advanced_helpdesk.facebook_access_token_page')
            )
            res = requests.get(
                url=url,
                params=params,
                verify=False
            )
            if res and res.status_code == 200:
                req = res.json()
                stage = (self.env.ref('helpdesk.stage_solved').id, self.env.ref('helpdesk.stage_cancelled').id)
                ticket = self.env['helpdesk.ticket'].sudo().search(
                    [('s_facebook_sender_id', '=', s_facebook_sender_id)]).filtered(
                    lambda r: r.stage_id.id not in stage)
                channel = self.env['mail.channel'].sudo().search(
                    ['|', ('s_facebook_sender_id', '=', s_facebook_sender_id), '&',
                     ('name', 'ilike', req.get('name')), ('s_zalo_sender_id', '=', False)], limit=1)
                partner = self.env['res.partner'].sudo().search(
                    ['|', ('s_facebook_sender_id', '=', s_facebook_sender_id), '&', '&',
                     ('name', 'ilike', req.get('name')), ('s_facebook_sender_id', '!=', False),
                     ('s_zalo_sender_id', '=', False)], limit=1)

                name = 'Anh_Chi_%s_%s' % (req['name'], req['id'])
                if req['gender'] == 'male':
                    name = 'Anh_%s_%s' % (req['name'], req['id'])
                elif req['gender'] == 'female':
                    name = 'Chi_%s_%s' % (req['name'], req['id'])
                if not ticket:
                    ticket = search_helpdesk.ticket_ids.sudo().create({
                        'name': req['name'],
                        's_facebook_sender_id': s_facebook_sender_id,
                        'team_id': search_helpdesk.id
                    })
                    # self.env['s.helpdesk.ticket.queue'].sudo().create({
                    #     'name': req['name'],
                    #     's_facebook_sender_id': s_facebook_sender_id,
                    #     'team_id': search_helpdesk.id,
                    #     'message_text': message_text
                    # })
                    if channel:
                        channel.channel_last_seen_partner_ids.unlink()
                        write_channel = {
                            's_assign_to': ticket.user_id.id
                        }
                        if channel.s_facebook_sender_id != req.get('id'):
                            write_channel.update({
                                's_facebook_sender_id': req.get('id'),
                                'name': name
                            })
                        if channel.s_assign_to.partner_id not in channel.channel_last_seen_partner_ids.partner_id:
                            if channel.channel_last_seen_partner_ids:
                                channel.channel_last_seen_partner_ids.unlink()
                            write_channel.update({
                                'channel_last_seen_partner_ids': [
                                    (0, 0, {'partner_id': ticket.user_id.partner_id.id}), ]
                            })
                        channel.sudo().write(write_channel)
                elif ticket and ticket.user_id.id not in self.env.ref(
                        'advanced_helpdesk.group_customer_care').users.ids:
                    self.env.ref('advanced_helpdesk.group_customer_care').users = [(4, ticket.user_id.id)]
                if not channel:
                    with open("customaddons/advanced_helpdesk/static/src/img/logo_facebook.jpg",
                              "rb") as image_file:
                        data = base64.b64encode(image_file.read())
                    s_assign_to = False
                    if ticket:
                        s_assign_to = ticket.user_id.id
                    create_channel = {
                        'name': name,
                        's_facebook_sender_id': s_facebook_sender_id,
                        's_assign_to': s_assign_to,
                        'group_public_id': self.env.ref('advanced_helpdesk.group_customer_care').id,
                        'channel_type': 'channel',
                        'image_128': data,
                        'channel_last_seen_partner_ids': [
                            (0, 0, {'partner_id': ticket.user_id.partner_id.id}),
                        ]
                    }
                    channel = self.env['mail.channel'].sudo().create(create_channel)
                elif channel and channel.s_facebook_sender_id != req.get('id'):
                    channel.sudo().write({
                        's_facebook_sender_id': req.get('id'),
                        'name': name
                    })
                if not partner:
                    self.env['res.partner'].sudo().create_res_partner_helpdesk(req['name'],
                                                                               s_facebook_sender_id=s_facebook_sender_id)
                else:
                    if partner.s_facebook_sender_id != req.get('id'):
                        partner.s_facebook_sender_id = req.get('id')
                if channel and partner and ticket and len(message_text) > 0:
                    search_fb_message_id = self.env['mail.message'].search(
                        [('s_helpdesk_message_id', '=', s_fb_message_id)], limit=1)
                    if not search_fb_message_id:
                        channel.message_post(
                            partner_ids=channel.s_assign_to.commercial_partner_id.ids,
                            body=message_text, author_id=partner.id, s_helpdesk_message_id=s_fb_message_id)
                return channel, partner, ticket
            else:
                self.env['ir.logging'].sudo().create({
                    'name': 'create_mail_channel_facebook',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': res.json(),
                    'func': 'create_mail_channel_facebook',
                    'line': '0',
                })
        else:
            self.env['ir.logging'].sudo().create({
                'name': 'create_mail_channel_facebook',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': "Chưa có đội hỗ trợ facebook",
                'func': 'create_mail_channel_facebook',
                'line': '0',
            })

    def create_channel_ticket_zalo(self, s_zalo_sender_id, s_zalo_message, s_zalo_message_id):
        helpdesk_team = self.env['helpdesk.team'].sudo().search([('s_select_integration', '=', 'zalo')], limit=1)
        if helpdesk_team:
            url = "https://openapi.zalo.me/v2.0/oa/getprofile?data={\"user_id\":\"%s\"}" % s_zalo_sender_id
            headers = {
                'access_token': self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_zalo.access_token',
                                                                                 '')
            }
            res = requests.get(
                url=url,
                headers=headers,
                verify=False
            ).json()
            if res and res.get('error') == 0:
                channel = self.env['mail.channel'].sudo().search([('s_zalo_sender_id', '=', s_zalo_sender_id)], limit=1)
                stage = (self.env.ref('helpdesk.stage_solved').id, self.env.ref('helpdesk.stage_cancelled').id)
                ticket = self.env['helpdesk.ticket'].sudo().search(
                    [('s_zalo_sender_id', '=', s_zalo_sender_id)]).filtered(lambda r: r.stage_id.id not in stage)
                partner = self.env['res.partner'].sudo().search([('s_zalo_sender_id', '=', s_zalo_sender_id)], limit=1)
                if res['data']['user_gender'] == 1:
                    name = 'Anh_%s_%s' % (res['data']['display_name'], s_zalo_sender_id)
                elif res['data']['user_gender'] == 2:
                    name = 'Chi_%s_%s' % (res['data']['display_name'], s_zalo_sender_id)
                elif res['data']['user_gender'] == 0:
                    name = 'Anh/Chi_%s_%s' % (res['data']['display_name'], s_zalo_sender_id)

                if not ticket:
                    # partner.channel_ids.sudo().channel_join()
                    ticket = helpdesk_team.ticket_ids.sudo().create({
                        'name': res['data']['display_name'],
                        's_zalo_sender_id': s_zalo_sender_id,
                        'team_id': helpdesk_team.id
                    })
                    if channel:
                        write_channel = {
                            's_assign_to': ticket.user_id.id
                        }
                        if channel.s_assign_to.partner_id not in channel.channel_last_seen_partner_ids.partner_id:
                            if channel.channel_last_seen_partner_ids:
                                channel.channel_last_seen_partner_ids.unlink()
                            write_channel.update({
                                'channel_last_seen_partner_ids': [
                                    (0, 0, {'partner_id': ticket.user_id.partner_id.id}), ]
                            })
                        channel.sudo().write(write_channel)

                if ticket.user_id.id not in self.env.ref('advanced_helpdesk.group_customer_care').users.ids and ticket:
                    self.env.ref('advanced_helpdesk.group_customer_care').users = [(4, ticket.user_id.id)]
                if not channel:
                    with open("customaddons/advanced_helpdesk/static/src/img/logo_zalo.jpg", "rb") as image_file:
                        data = base64.b64encode(image_file.read())
                    if ticket:
                        s_assign_to = ticket.user_id.id
                    create_channel = {
                        'name': name,
                        's_zalo_sender_id': s_zalo_sender_id,
                        's_assign_to': s_assign_to,
                        'group_public_id': self.env.ref('advanced_helpdesk.group_customer_care').id,
                        'channel_type': 'channel',
                        'image_128': data,
                        'channel_last_seen_partner_ids': [
                            (0, 0, {'partner_id': ticket.user_id.partner_id.id}),
                        ]
                    }
                    channel = self.env['mail.channel'].sudo().create(create_channel)
                if not partner:
                    info = res.get('data').get('shared_info')
                    if info:
                        self.env['res.partner'].sudo().create_res_partner_zalo_oa(info=info,
                                                                                     s_zalo_sender_id=s_zalo_sender_id)
                    else:
                        self.env['res.partner'].sudo().create_res_partner_helpdesk(res['data']['display_name'],
                                                                                   s_zalo_sender_id=s_zalo_sender_id)
                if channel and partner and ticket and len(s_zalo_message) > 0:
                    search_zalo_message_id = self.env['mail.message'].search(
                        [('s_helpdesk_message_id', '=', s_zalo_message_id)], limit=1)
                    if not search_zalo_message_id:
                        channel.message_post(
                            partner_ids=channel.s_assign_to.commercial_partner_id.ids,
                            body=s_zalo_message, author_id=partner.id, s_helpdesk_message_id=s_zalo_message_id)
                return channel, partner, ticket
            else:
                self.env['ir.logging'].sudo().create({
                    'name': 'create_channel_ticket_zalo',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': res,
                    'func': 'create_channel_ticket_zalo',
                    'line': '0',
                })
        else:
            self.env['ir.logging'].sudo().create({
                'name': 'create_channel_ticket_zalo',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': "Chưa có đội hỗ trợ Zalo",
                'func': 'create_channel_ticket_zalo',
                'line': '0',
            })

    # start thay đổi tên channel khi giới tính thay đổi
    def change_name_channel_zalo(self, channel, s_zalo_sender_id):
        url = "https://openapi.zalo.me/v2.0/oa/getprofile?data={\"user_id\":\"%s\"}" % s_zalo_sender_id
        headers = {
            'access_token': self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_zalo.access_token',
                                                                             '')
        }
        res = requests.get(
            url=url,
            headers=headers,
            verify=False
        ).json()
        if res and res.get('error') == 0:
            if "Anh/Chi" in channel.name and res['data']['user_gender'] != 0:
                if res['data']['user_gender'] == 1:
                    name = 'Anh_%s_%s' % (res['data']['display_name'], s_zalo_sender_id)
                elif res['data']['user_gender'] == 2:
                    name = 'Chi_%s_%s' % (res['data']['display_name'], s_zalo_sender_id)
                channel.sudo().write({
                    'name': name
                })
        else:
            self.env['ir.logging'].sudo().create({
                'name': 'change_name_channel_zalo',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': res,
                'func': 'change_name_channel_zalo',
                'line': '0',
            })

    def btn_show_channel_chat_helpdesk(self):
        channel_id = self.id
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '{base_url}/web#menu_id={menu_discuss}&cids=1&default_active_id=mail.box_inbox&action={action_discuss}&active_id=mail.channel_{channel_id}'.format(
                base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                menu_discuss=self.env.ref('mail.menu_root_discuss').id,
                action_discuss=self.env.ref('mail.action_discuss').id, channel_id=channel_id)
        }

    def channel_join(self):
        res = super(MailChannel, self).channel_join()
        if self.s_facebook_sender_id or self.s_zalo_sender_id:
            channel_id = self.id
            return {
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': '{base_url}/web#menu_id={menu_discuss}&cids=1&default_active_id=mail.box_inbox&action={action_discuss}&active_id=mail.channel_{channel_id}'.format(
                    base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                    menu_discuss=self.env.ref('mail.menu_root_discuss').id,
                    action_discuss=self.env.ref('mail.action_discuss').id, channel_id=channel_id)
            }
        return res

    def btn_done_ticket(self):
        ticket_unfinished = self.s_channel_ticket_ids.filtered(lambda r: r.stage_id not in [
            self.env.ref('helpdesk.stage_solved'), self.env.ref('helpdesk.stage_cancelled')])
        if ticket_unfinished:
            ticket_unfinished.stage_id = self.env.ref('helpdesk.stage_solved')
            return True
        else:
            return False
