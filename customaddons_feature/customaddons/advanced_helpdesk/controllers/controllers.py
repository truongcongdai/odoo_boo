from datetime import date
from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.exceptions import ValidationError, _logger
import requests
from odoo.tests import Form
import json
from odoo.addons.mail.controllers.discuss import DiscussController
import urllib3
import base64

urllib3.disable_warnings()


class SendMessengerFacebook(DiscussController):
    @http.route('/mail/message/post', methods=['POST'], type='json', auth='public')
    def mail_message_post(self, thread_model, thread_id, post_data, **kwargs):
        channel = request.env['mail.channel'].sudo().search([('id', '=', thread_id)], limit=1)
        stage_new_ticket = channel.s_channel_ticket_ids.filtered(
            lambda r: r.stage_id == request.env.ref('helpdesk.stage_new') and r.stage_id not in [
                request.env.ref('helpdesk.stage_solved'), request.env.ref('helpdesk.stage_cancelled')])
        if channel.channel_type == "channel" and (channel.s_facebook_sender_id or channel.s_zalo_sender_id):
            headers = {
                'Content-Type': 'application/json'
            }
            if channel.s_facebook_sender_id:
                url = "{url_facebook}/me/messages".format(
                    url_facebook=request.env['ir.config_parameter'].sudo().get_param(
                        'advanced_helpdesk.url_facebook'))
                params = dict(
                    access_token=request.env['ir.config_parameter'].sudo().get_param(
                        "advanced_helpdesk.facebook_access_token_page")
                )

                payload = json.dumps({
                    "recipient": "{id:%s}" % channel.s_facebook_sender_id,
                    "message":
                        {
                            "text": post_data.get('body')
                        },
                    "messaging_type": "RESPONSE"
                })
                req = requests.post(
                    url=url,
                    params=params,
                    headers=headers,
                    data=payload,
                    verify=False
                )
                if 'error' in req.json():
                    request.env['ir.logging'].sudo().create({
                        'name': 'messenger_odoo_facebook',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': req.json()['error']['message'],
                        'func': 'mail_message_post',
                        'line': '0',
                    })
                elif stage_new_ticket:
                    stage_new_ticket.stage_id = request.env.ref('helpdesk.stage_in_progress')
            if channel.s_zalo_sender_id:
                url_zalo = "{url_zalo}/oa/message/cs".format(
                    url_zalo=request.env['ir.config_parameter'].sudo().get_param(
                        'advanced_integrate_zalo.s_url_endpoint_oa'))
                payload = json.dumps({
                    "recipient":
                        {"user_id": channel.s_zalo_sender_id},
                    "message":
                        {
                            "text": post_data.get('body')
                        }
                })
                headers.update({
                    "access_token": request.env['ir.config_parameter'].sudo().get_param(
                        "advanced_integrate_zalo.access_token")
                })
                req = requests.post(
                    url=url_zalo,
                    headers=headers,
                    data=payload,
                    verify=False
                )
                if req.json()['error'] != 0:
                    request.env['ir.logging'].sudo().create({
                        'name': 'messenger_odoo_zalo',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': "Token bị lỗi, Reset lại token",
                        'func': 'mail_message_post',
                        'line': '0',
                    })
                elif stage_new_ticket:
                    stage_new_ticket.stage_id = request.env.ref('helpdesk.stage_in_progress')
        res = super(SendMessengerFacebook, self).mail_message_post(thread_model, thread_id, post_data, **kwargs)
        return res


class AdvancedHelpdeskFacebookController(http.Controller):
    @http.route('/facebook/callback/', type='http', auth='public', methods=["GET"], csrf=False)
    def get_callback_facebook_url(self, **kw):
        try:
            redirect_uri = "%s/facebook/callback/" % request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            client_id = request.env['ir.config_parameter'].sudo().get_param('advanced_helpdesk.facebook_client_id', '')
            client_secret = request.env['ir.config_parameter'].sudo().get_param(
                'advanced_helpdesk.facebook_client_secret')
            url = "{url_facebook}/oauth/access_token".format(
                url_facebook=request.env['ir.config_parameter'].sudo().get_param(
                    'advanced_helpdesk.url_facebook'))
            params = dict(
                redirect_uri=redirect_uri,
                client_id=client_id,
                client_secret=client_secret,
                code=kw['code'],
                auth_type="rerequest",
                scope="pages_messaging,pages_show_list,public_profile,pages_read_engagement,pages_manage_metadata"
            )
            res = requests.get(
                url=url,
                params=params,
                verify=False
            )
            if res.status_code == 200:
                access_token_facebook = res.json().get('access_token', '')
                request.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_access_token',
                                                                    access_token_facebook)
                request.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_connect_date',
                                                                    date.today())
                request.env['ir.config_parameter'].sudo().set_param('advanced_helpdesk.facebook_is_connect', True)
                request.env['res.config.settings'].sudo().get_token_page_facebook()
                return request.redirect(request.env['ir.config_parameter'].sudo().get_param('web.base.url') + "/web")
            else:
                return ("Kết nối thất bại")
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'Connect-Odoo-Facebook',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'get_callback_facebook_url',
                'line': '0',
            })

    @http.route('/boo/facebook/messenger', type='json', auth='none', methods=['POST'], csrf=False)
    def webhook_facebook(self, **kw):
        request.env.uid = SUPERUSER_ID
        body = json.loads(request.httprequest.data.decode('utf-8'))
        vals = {
            'name': '###Facebook: webhook_facebook',
            'type': 'server',
            'dbname': 'boo',
            'level': 'ERROR',
            'path': 'url',
            'func': 'webhook_facebook',
            'line': '0',
        }
        create_error = False
        if body:
            if body.get('object'):
                if body['object'] == 'page':
                    entries = body.get('entry')
                    if entries:
                        for entry in entries:
                            if entry.get('messaging'):
                                webhook_events = entry.get('messaging')
                            else:
                                webhook_events = entry.get('standby')
                            if webhook_events:
                                for webhook_event in webhook_events:
                                    if webhook_event:
                                        search_fb_message_id = False
                                        fb_message_id = False
                                        if webhook_event.get('message'):
                                            fb_message = webhook_event.get('message')
                                            if fb_message.get('mid'):
                                                fb_message_id = fb_message.get('mid')
                                                search_fb_message_id = request.env['mail.message'].search(
                                                    [('s_helpdesk_message_id', '=', fb_message_id)], limit=1)
                                        sender = webhook_event.get('sender')
                                        if sender:
                                            senderPsid = sender.get('id')
                                            if senderPsid:
                                                channel = request.env['mail.channel'].sudo().search(
                                                    [('s_facebook_sender_id', '=', senderPsid)], limit=1)
                                                partner = request.env['res.partner'].sudo().search(
                                                    [('s_facebook_sender_id', '=', senderPsid)], limit=1)
                                                ticket = channel.s_channel_ticket_ids.filtered(
                                                    lambda r: r.stage_id not in [request.env.ref('helpdesk.stage_solved'),
                                                                                 request.env.ref('helpdesk.stage_cancelled')])
                                                if not channel or not partner or not ticket:
                                                    if webhook_event.get('message'):
                                                        message_text = webhook_event.get('message').get('text')
                                                    else:
                                                        message_text = False
                                                    facebook_send_message_realtime = request.env[
                                                        'ir.config_parameter'].sudo().get_param(
                                                        'advanced_helpdesk.s_facebook_send_message_realtime')
                                                    if facebook_send_message_realtime == 'True':
                                                        mail_channel_queue = request.env['s.mail.channel.queue'].sudo().create({
                                                            's_facebook_sender_id': senderPsid,
                                                            's_facebook_message': message_text,
                                                            's_fb_message_id': fb_message_id
                                                        })
                                                        if mail_channel_queue:
                                                            mail_channel_queue.cron_create_mail_channel()
                                                    else:
                                                        request.env['s.mail.channel.queue'].sudo().create({
                                                            's_facebook_sender_id': senderPsid,
                                                            's_facebook_message': message_text,
                                                            's_fb_message_id': fb_message_id
                                                        })
                                                    # channel, partner, ticket = request.env['mail.channel'].sudo().create_mail_channel_facebook(senderPsid, message_text)
                                                elif channel:
                                                    if not search_fb_message_id:
                                                        channel.message_post(
                                                            partner_ids=channel.s_assign_to.commercial_partner_id.ids,
                                                            body=webhook_event.get('message').get('text'),
                                                            author_id=partner.id, s_helpdesk_message_id=fb_message_id)
                                                return 200
                                            else:
                                                vals.update({
                                                    'message': "Kiểm tra sender, body: " + str(body),
                                                })
                                                create_error = True
                                        else:
                                            vals.update({
                                                'message': "Kiểm tra sender, body: " + str(body),
                                            })
                                            create_error = True
                            else:
                                vals.update({
                                    'message': "Kiểm tra messaging, body: " + str(body),
                                })
                                create_error = True
                    else:
                        vals.update({
                            'message': "Kiểm tra entry, body: " + str(body),
                        })
                        create_error = True
                else:
                    vals.update({
                        'message': "Kiểm tra object, body: " + str(body),
                    })
                    create_error = True
            else:
                vals.update({
                    'message': "Kiểm tra object, body: " + str(body),
                })
                create_error = True
        else:
            vals.update({
                'message': "Kiểm tra body, body: " + str(body),
            })
            create_error = True
        if create_error:
            request.env['ir.logging'].sudo().create(vals)

    @http.route('/boo/facebook/messenger', type='http', auth='public', methods=["GET"], csrf=False)
    def get_webhook_url(self, **kw):
        verify_token = "secret"
        if "hub.mode" in kw and "hub.verify_token" in kw:
            mode = kw["hub.mode"]
            token = kw["hub.verify_token"]
            if mode == "subscribe" and token == verify_token:
                challenge = kw['hub.challenge']
                return challenge
            else:
                return 'Error'
        return 'Something'


class AdvancedHelpdeskZaloController(http.Controller):

    @http.route('/boo/zalo/messenger', type='json', auth='none', methods=['POST'], csrf=False)
    def webhook_zalo(self, **kwargs):
        request.env.uid = SUPERUSER_ID
        body = json.loads(request.httprequest.data)
        vals = {
            'name': '###Zalo: webhook_zalo',
            'type': 'server',
            'dbname': 'boo',
            'level': 'ERROR',
            'path': 'url',
            'func': 'webhook_zalo',
            'line': '0',
        }
        create_error = False
        if body:
            s_zalo_sender_id, s_zalo_message, s_zalo_messag_id, search_zalo_message_id = False, False, False, False
            if body.get('sender'):
                sender = body.get('sender')
                if sender.get('id'):
                    s_zalo_sender_id = sender.get('id')
                else:
                    vals.update({
                        'message': "Kiểm tra sender, body: " + str(body),
                    })
                    create_error = True
            else:
                vals.update({
                    'message': "Kiểm tra sender, body: " + str(body),
                })
                create_error = True
            if body.get('message'):
                message = body.get('message')
                if message.get('text'):
                    s_zalo_message = body['message']['text']
                else:
                    vals.update({
                        'message': "Kiểm tra message, body: " + str(body),
                    })
                    create_error = True
                if message.get('msg_id'):
                    s_zalo_messag_id = body.get('message').get('msg_id')
                    search_zalo_message_id = request.env['mail.message'].search(
                        [('s_helpdesk_message_id', '=', s_zalo_messag_id)], limit=1)
            else:
                vals.update({
                    'message': "Kiểm tra message, body: " + str(body),
                })
                create_error = True
            if s_zalo_sender_id and s_zalo_message:
                channel = request.env['mail.channel'].sudo().search([('s_zalo_sender_id', '=', s_zalo_sender_id)],
                                                                    limit=1)
                partner = request.env['res.partner'].sudo().search([('s_zalo_sender_id', '=', s_zalo_sender_id)],
                                                                   limit=1)
                ticket = channel.s_channel_ticket_ids.filtered(
                    lambda r: r.stage_id not in [request.env.ref('helpdesk.stage_solved'),
                                                 request.env.ref('helpdesk.stage_cancelled')])
                if (not channel or not partner or not ticket) and s_zalo_message != 'This is testing message':
                    request.env['s.mail.channel.queue'].sudo().create({
                        's_zalo_sender_id': s_zalo_sender_id,
                        's_zalo_message': s_zalo_message,
                        's_zalo_message_id': s_zalo_messag_id
                    })
                    # channel, partner, ticket = request.env['mail.channel'].sudo().create_channel_ticket_zalo(
                    #     s_zalo_sender_id)
                elif channel:
                    if not search_zalo_message_id:
                        request.env['mail.channel'].sudo().change_name_channel_zalo(channel, s_zalo_sender_id)
                        channel.message_post(
                            partner_ids=channel.s_assign_to.commercial_partner_id.ids,
                            body=s_zalo_message, author_id=partner.id, s_helpdesk_message_id=s_zalo_messag_id)
                return 200
        else:
            vals.update({
                'message': "body: " + str(body),
            })
            create_error = True
        if create_error:
            request.env['ir.logging'].sudo().create(vals)
