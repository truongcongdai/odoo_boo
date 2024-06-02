from datetime import date
from odoo import http, SUPERUSER_ID
from odoo.http import request
import requests
import json
import webbrowser
import datetime as date
from datetime import datetime

import urllib3

urllib3.disable_warnings()


class SZaloOaController(http.Controller):

    @http.route('/zalo/loyalty_point', type='json', auth='public', methods=["POST"], csrf=False)
    def send_loyalty_point_zalo_oa(self, **kwargs):
        request.env.uid = SUPERUSER_ID
        body = json.loads(request.httprequest.data)
        partner_id = request.env['res.partner'].sudo().search([('s_zalo_sender_id', '=', body.get('id'))], limit=1)
        url_zalo = "{url_zalo}/oa/message/cs".format(
            url_zalo=request.env['ir.config_parameter'].sudo().get_param(
                'advanced_integrate_zalo.s_url_endpoint_oa'))
        headers = {
            'Content-Type': "application/json",
            "access_token": request.env['ir.config_parameter'].sudo().get_param(
                "advanced_integrate_zalo.access_token")
        }
        if partner_id:
            payload = json.dumps({
                "recipient":
                    {"user_id": partner_id.s_zalo_sender_id},
                "message":
                    {
                        "text": "Chào mừng bạn đến với BOO\n" + "Khách hàng: %s\n" % body.get(
                            'ho_ten') + "Hạng thành viên: %s\n" % partner_id.customer_ranked + "Điểm thưởng: %s" % "{:,.2f}".format(
                            round(partner_id.loyalty_points, 2))}
            })
            req = requests.post(
                url=url_zalo,
                headers=headers,
                data=payload,
                verify=False
            )
            if req.json()['error'] != 0:
                request.env['ir.logging'].sudo().create({
                    'name': '###Zalo_OA: Send_loyalty_point_zalo_oa',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': str(req.json()),
                    'func': 'send_loyalty_point_zalo_oa',
                    'line': '0',
                })
        else:
            # không có thành viên thì gửi tin nhắn đăng ký
            payload = json.dumps({
                "recipient":
                    {"user_id": body.get('id')},
                "message":
                    {
                        "text": "Bạn chưa đăng ký thành viên, vui lòng đăng ký để nhận ưu đãi",
                        "attachment": {
                            "type": "template",
                            "payload": {
                                "buttons": [
                                    {
                                        "title": "Đăng ký thành viên",
                                        "type": "oa.query.hide",
                                        "payload": "#register_member"
                                    }
                                ]
                            }
                        }
                    }
            })
            req = requests.post(
                url=url_zalo,
                headers=headers,
                data=payload,
                verify=False
            )
            if req.json()['error'] != 0:
                request.env['ir.logging'].sudo().create({
                    'name': '###Zalo_OA: đăng ký thành viên',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'path': 'url',
                    'message': str(req.json()),
                    'func': 'send_loyalty_point_zalo_oa',
                    'line': '0',
                })

    # đăng ký thành viên zalo oa

    # Route to render HTML
    @http.route('/zalo/register_member_html', type='http', auth='public', methods=["GET"], csrf=False)
    def zalo_oa_register_member_html(self, **kw):
        if not kw.get('edit_customer_zalo'):
            kw['edit_customer_zalo'] = False
            kw['zalo_error_message'] = ""
            kw['zalo_call_error'] = False
        return http.request.render('advanced_integrate_zalo.template_register_member_zalo', kw)

    # Route to return URL of HTML route
    @http.route('/zalo/register_member', type='json', auth='public', methods=["POST"], csrf=False)
    def zalo_oa_register_member(self, **kwargs):
        return {'redirect_url': '/zalo/register_member_html'}

    @http.route('/get_districts', type='http', auth='public')
    def get_districts(self, city_id):
        districts = http.request.env['res.country.address'].search([('parent_id', '=', int(city_id))])
        return http.request.make_response(
            json.dumps(
                {'districts': [{'code': district.code, 'name': district.name_with_type} for district in districts]}),
            headers=[('Content-Type', 'application/json')])

    @http.route('/zalo/register_member_submit', type='http', auth='public', methods=["POST"], csrf=False)
    def zalo_oa_register_member_submit(self, **post):
        edit_customer_zalo = False
        zalo_error_message = ""
        zalo_call_error = False
        ho_ten = post.get('ho_ten')
        dob = post.get('dob')
        email = post.get('email')
        so_dien_thoai = post.get('so_dien_thoai')
        dia_chi = post.get('dia_chi')
        city_id = post.get('city_id')
        country_district_id = post.get('country_district_id')
        confirm_info = post.get('confirm_info')
        s_zalo_sender_id = post.get('s_zalo_sender_id')
        url_updatefollowerinfo = "https://openapi.zalo.me/v2.0/oa/updatefollowerinfo"
        payload = json.dumps({
            "user_id": s_zalo_sender_id,
            "name": ho_ten,
            "phone": so_dien_thoai,
            "address": dia_chi,
            "city_id": int(http.request.env['res.country.address'].search([('id', '=', int(city_id))]).code),
            "district_id": int(country_district_id)
        })
        headers = {
            'Content-Type': "application/json",
            "access_token": request.env['ir.config_parameter'].sudo().get_param(
                "advanced_integrate_zalo.access_token")
        }
        req = requests.post(
            url=url_updatefollowerinfo,
            headers=headers,
            data=payload,
            verify=False
        )
        if req.json()['error'] != 0:
            zalo_call_error = True
            zalo_error_message = req.json().get('message')
            request.env['ir.logging'].sudo().create({
                'name': '###Zalo_OA: zalo_oa_register_member_submit',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': "req: %s - payload: %s" % (str(req.json()), payload),
                'func': 'zalo_oa_register_member_submit',
                'line': '0',
            })
        else:
            edit_customer_zalo = request.env['res.partner'].sudo().create_res_partner_zalo_oa(info=post,
                                                                                              s_zalo_sender_id=s_zalo_sender_id)
        return http.request.render('advanced_integrate_zalo.template_register_member_zalo',
                                   {'edit_customer_zalo': edit_customer_zalo, 'id': s_zalo_sender_id,
                                    'zalo_call_error': zalo_call_error, 'zalo_error_message': zalo_error_message})

    # @http.route('/zalo/register_member', type='http', auth='public', methods=["POST"], csrf=False)
    # def zalo_oa_register_member(self, **kwargs):
    #     return http.request.render('advanced_integrate_zalo.template_register_member_zalo')
    # return http.request.render('advanced_integrate_zalo.template_register_member_zalo')
    # def zalo_oa_register_member(self, **kwargs):
    #     request.env.uid = SUPERUSER_ID
    #     body = json.loads(request.httprequest.data)
    #     url_zalo = "{url_zalo}/oa/message/cs".format(
    #         url_zalo=request.env['ir.config_parameter'].sudo().get_param(
    #             'advanced_integrate_zalo.s_url_endpoint_oa'))
    #     url_image = request.env['ir.config_parameter'].sudo().get_param('advanced_integrate_zalo.s_zalo_url_image')
    #     payload = json.dumps({
    #         "recipient":
    #             {"user_id": body.get('id')},
    #         "message":
    #             {
    #                 "attachment": {
    #                     "type": "template",
    #                     "payload": {
    #                         "template_type": "request_user_info",
    #                         "elements": [{
    #                             "title": "Đăng ký thành viên",
    #                             "subtitle": "Đăng ký thành viên để nhận ưu đãi",
    #                             "image_url": url_image
    #                         }]
    #                     }
    #                 }
    #             }
    #     })
    #     headers = {
    #         'Content-Type': "application/json",
    #         "access_token": request.env['ir.config_parameter'].sudo().get_param(
    #             "advanced_integrate_zalo.access_token")
    #     }
    #     req = requests.post(
    #         url=url_zalo,
    #         headers=headers,
    #         data=payload,
    #         verify=False
    #     )
    #     if req.json()['error'] != 0:
    #         request.env['ir.logging'].sudo().create({
    #             'name': '###Zalo_OA: zalo_oa_register_member',
    #             'type': 'server',
    #             'dbname': 'boo',
    #             'level': 'ERROR',
    #             'path': 'url',
    #             'message': req.json(),
    #             'func': 'zalo_oa_register_member',
    #             'line': '0',
    #         })
