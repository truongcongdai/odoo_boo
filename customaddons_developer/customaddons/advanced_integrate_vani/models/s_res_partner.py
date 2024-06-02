from odoo import fields, models, api, _
from odoo.http import request, _logger
import json
from datetime import datetime, timedelta
import pytz
import uuid


class SResPartner(models.Model):
    _inherit = 'res.partner'

    membership_id = fields.Char(string="MembershipId Vani")
    vanila_barcode = fields.Char(string="Vanila Barcode", readonly=True)
    s_loyalty_points = fields.Float(string='Điểm thân thiết', compute='_compute_point', store=True)
    is_connected_vani = fields.Boolean(string="Kết nối ví vani", readonly=True)
    vani_pos_config_id = fields.Many2one('pos.config', string='Kết nối ví vani từ cửa hàng', readonly=True)
    vani_connect_from = fields.Char(related="vani_pos_config_id.name", string="Tên cửa hàng kết nối ví Vani", readonly=True)
    is_regis_vani = fields.Boolean(string='Đã đăng ký trên Vani', default=False)

    @api.depends('loyalty_points')
    def _compute_point(self):
        for rec in self:
            if rec.loyalty_points:
                rec.s_loyalty_points = rec.loyalty_points

    def post_deregistration(self, customerId):
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('vani.api.url', '') + '/deregistration'
            data = {
                'customerId': str(customerId)
            }
            command = "Deregistration"
            data = json.dumps(data)
            self.env['base.integrate.vani']._post_data_vani(url, command=command, data=data)
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'post_deregistration',
                'line': '0',
            })

    # def post_points_filling(self, customer_id, points):
    #     try:
    #         url = self.env['ir.config_parameter'].sudo().get_param('vani.api.url', '') + '/points-approval'
    #         request_id = str(uuid.uuid4())
    #         time_now = pytz.timezone('Asia/Ho_Chi_Minh').localize(datetime.now())
    #         payload = {
    #             "iss": self.env['ir.config_parameter'].sudo().get_param('vani.membership.id', ''),
    #             "aud": "vani-points-filling",
    #             "iat": int(time_now.timestamp()),
    #             "exp": int((time_now + timedelta(minutes=10)).timestamp()),
    #             "requestId": request_id,
    #             "customerId": str(customer_id),
    #             "amountOfVaniPointTofill": int(points),
    #         }
    #         data = {
    #             "requestToken": self.env['base.integrate.vani']._generate_request_token_jwt(payload)
    #         }
    #         command = "Points filling"
    #         data = json.dumps(data)
    #         if data:
    #             res = self.env['base.integrate.vani']._post_data_vani(url, command=command, data=data)
    #             if res.status_code == 200:
    #                 request.env['request.vani.history'].sudo().create({
    #                     'request_id': request_id,
    #                     'vani_url': url,
    #                     'param': data,
    #                 })
    #     except Exception as e:
    #         _logger.error(e.args)
    #         self.env['ir.logging'].sudo().create({
    #             'name': command,
    #             'type': 'server',
    #             'dbname': 'boo',
    #             'level': 'ERROR',
    #             'message': str(e),
    #             'path': 'url',
    #             'func': 'post_points_filling',
    #             'line': '0',
    #         })

    def post_points_approval(self, transactionId, customerId, isVanilaBarcodeUsed, transactionType, transactionTime,
                             brandId, shopBrandName, branch, paymentMethod, productTitle, productAmount, billAmount,
                             productPurchaseTime, productCurrency, pointAmount, totalPointAmount, trafficType, vaniCouponNumber):
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('vani.api.url', '') + '/points-approval'
            data = {
                'transactionId': str(transactionId),
                'customerId': str(customerId),
                'isVanilaBarcodeUsed': isVanilaBarcodeUsed,
                'transactionType': str(transactionType),
                'transactionTime': str(transactionTime),
                'brandId': str(brandId),
                'shopBrandName': str(shopBrandName),
                'branch': str(branch),
                'paymentMethod': str(paymentMethod),
                'productTitle': str(productTitle),
                'productAmount': float(productAmount),
                'billAmount': float(billAmount),
                'productPurchaseTime': str(productPurchaseTime),
                'productCurrency': str(productCurrency),
                'pointAmount': float(pointAmount),
                'totalPointAmount': float(totalPointAmount),
                'trafficType': str(trafficType),
                'vaniCouponNumber': str(vaniCouponNumber)
            }
            if data.get('vaniCouponNumber') == 'None':
                data.pop('vaniCouponNumber')
            command = "Points approval"
            # data = json.dumps(data)
            if data:
                self.env['s.vani.queue'].sudo().create({
                    'command': command,
                    'url': 'points-approval',
                    'data': str(data),
                })
                # self.env['base.integrate.vani']._post_data_vani(url, command=command, data=data)
                self.env['ir.logging'].sudo().create({
                    'name': command,
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'message': str(data),
                    'path': 'url',
                    'func': 'get_points_filling_info',
                    'line': '0',
                })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': "Points approval",
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'post_points_approval',
                'line': '0',
            })

    def post_points_cancellation(self, transactionId, customerId, orgTransactionId, transactionTime, cancelType, cancelPointAmount, totalPointAmount):
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('vani.api.url', '') + '/points-cancellation'
            data = {
                'transactionId': str(transactionId),
                'customerId': str(customerId),
                'orgTransactionId': str(orgTransactionId),
                'transactionTime': str(transactionTime),
                'cancelType': str(cancelType),
                'cancelPointAmount': float(cancelPointAmount),
                'totalPointAmount': float(totalPointAmount)
            }
            command = "Points cancellation"
            # data = json.dumps(data)
            if data:
                self.env['s.vani.queue'].sudo().create({
                    'command': command,
                    'url': 'points-cancellation',
                    'data': str(data),
                })
                # self.env['base.integrate.vani']._post_data_vani(url, command=command, data=data)
                self.env['ir.logging'].sudo().create({
                    'name': "Points cancellation",
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'message': str(data),
                    'path': 'url',
                    'func': 'post_points_cancellation',
                    'line': '0',
                })
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': "Points cancellation",
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'post_points_cancellation',
                'line': '0',
            })

    def get_points_filling_info(self, request_id=None):
        try:
            url = 'balance-api.test.vani.la/v1.0/points-filling-info/' + request_id
            command = "Points filling info"
            res = self.env['base.integrate.vani']._post_data_vani(url, command=command)
            return res
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': command,
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'get_points_filling_info',
                'line': '0',
            })

    # def post_points_filling_cancellation(self, customer_id, cancellation_point):
    #     try:
    #         url = self.env['ir.config_parameter'].sudo().get_param('vani.point.api.url',
    #                                                                '') + '/points-cancellation'
    #         time_now = pytz.timezone('Asia/Ho_Chi_Minh').localize(datetime.now())
    #         request_id = str(uuid.uuid4())
    #         payload = {
    #             "iss": self.env['ir.config_parameter'].sudo().get_param('vani.membership.id', ''),
    #             "aud": "vani-points-filling-cancellation",
    #             "iat": int(time_now.timestamp()),
    #             "exp": int((time_now + timedelta(minutes=10)).timestamp()),
    #             "requestId": request_id,
    #             "customerId": str(customer_id),
    #             "cancellationPoint": int(cancellation_point)
    #         }
    #         data = {
    #             "requestToken": self.env['base.integrate.vani']._generate_request_token_jwt(payload)
    #         }
    #         command = "Points filling cancellation"
    #         data = json.dumps(data)
    #         if data:
    #             res = self.env['base.integrate.vani']._post_data_vani(url, command=command, data=data)
    #             if res.status_code == 200:
    #                 request.env['request.vani.history'].sudo().create({
    #                     'request_id': request_id,
    #                     'vani_url': url,
    #                     'param': payload
    #                 })
    #
    #     except Exception as e:
    #         _logger.error(e.args)
    #         self.env['ir.logging'].sudo().create({
    #             'name': command,
    #             'type': 'server',
    #             'dbname': 'boo',
    #             'level': 'ERROR',
    #             'message': str(e),
    #             'path': 'url',
    #             'func': 'post_points_filling_cancellation',
    #             'line': '0',
    #         })


    def unlink(self):
        customerIds = self.filtered(lambda c: c.vanila_barcode).ids
        res= super(SResPartner, self).unlink()
        if res:
            for customerId in customerIds:
                self.post_deregistration(customerId=customerId)
        return res

    # Cập nhật is_regis_vani cho khách hàng cũ
    def _update_res_partner(self):
        check_phone = self.env['res.partner'].sudo().search([('id', '=', self.id), ('type', '=', 'contact')], limit=1)
        if len(check_phone) > 0:
            check_phone.write({
            'is_regis_vani': True
        })

    def compute_connected_vani_from(self):
        # Lấy tên dựa theo đơn hàng POS đầu tiên có gửi transaction đến Vani.
        query = """
                    SELECT id 
                    FROM res_partner
                    WHERE vani_connect_from IS NOT NULL
                        AND vani_pos_config_id IS NULL;
                """
        self.env.cr.execute(query)
        vani_connect_from = self.env.cr.dictfetchall()
        if len(vani_connect_from) > 0:
            for partner in vani_connect_from:
                res_partner = self.env['res.partner'].sudo().search([('id', '=', partner.get('id'))], limit=1)
                vani_pos_order = self.env['pos.order'].sudo().search(
                    [('partner_id', '=', res_partner.id), ('is_vani_post_transaction', '=', True)], order='id asc',
                    limit=1)
                if len(vani_pos_order) > 0:
                    res_partner.write({
                        'vani_pos_config_id': vani_pos_order.session_id.config_id.id
                    })

        # 2 khách hàng là KH test của Vani ở site live
        self.env.cr.execute(query)
        vani_test_connect_from = self.env.cr.dictfetchall()
        if len(vani_test_connect_from) > 0:
            for partner in vani_test_connect_from:
                partner_test = self.env['res.partner'].sudo().search([('id', '=', partner.get('id'))], limit=1)
                pos_order = self.env['pos.order'].sudo().search([('partner_id', '=', partner_test.id)], order='id asc',
                                                                limit=1)
                if len(pos_order) > 0:
                    partner_test.write({
                        'vani_pos_config_id': pos_order.session_id.config_id.id
                    })

        # Địa điểm tạo khách hàng
        pos_create_customer = self.env['res.partner'].sudo().search(
            [('s_pos_order_id', '!=', False), ('pos_create_customer', '!=', False)])
        if len(pos_create_customer) > 0:
            for customer in pos_create_customer:
                if customer.pos_create_customer != 'POS ecommerce' and customer.s_pos_order_id:
                    customer.sudo().write({
                        'pos_create_customer': customer.s_pos_order_id.name
                    })