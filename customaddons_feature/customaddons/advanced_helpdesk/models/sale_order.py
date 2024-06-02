from odoo import fields, models, api
import requests
import json
import io
from odoo.exceptions import ValidationError, _logger


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    s_thread_id = fields.Integer(
        string='Thread',
        required=False)
    s_facebook_sender_id = fields.Char(string='Id Sender Facebook',
                                       required=False)
    s_zalo_sender_id = fields.Char(string='Id Sender Zalo',
                                   required=False)
    is_push_to_m2 = fields.Boolean(required=False, compute="_compute_is_push_to_m2")

    def _compute_is_push_to_m2(self):
        for rec in self:
            rec.is_push_to_m2 = False
            picking_done_ids = rec.picking_ids.filtered(lambda p: p.transfer_type == 'out')
            if (rec.s_zalo_sender_id or rec.s_facebook_sender_id) and (picking_done_ids or rec.m2_so_id):
                rec.is_push_to_m2 = True

    def send_order_information(self):
        product = ""
        payment_method = "Thanh toán khi giao hàng" if self.payment_method == 'cod' else "Thanh toán online"
        location = '{name} {phone}, {location}'.format(name=self.partner_id.name, phone=self.partner_id.phone,
                                                       location=self.partner_id.contact_address_complete)
        for line in self.order_line:
            product += """
                    <div style="margin-left:6px;margin-bottom:12px;">
                        <p style="margin:0">%s</p>
                        <p style="margin:0">Số lượng: %s</p>
                    </div>
                    """ % (line.name, line.product_uom_qty)
        body = """
                <div style="max-width:450px; background-color:white; border:1px solid #cccc; border-radius: 10px;">
                    <div class="content" style="margin: 6px 12px">
                        <header style="border-bottom: 1px solid #e1e0e0;">
                            <span style="font-size: 15px;">Đơn hàng - %s</span>
                        </header>
                        <main style="border-bottom: 1px solid #e1e0e0;">
                            <div name="product" style="margin-top:12px">
                                <p style="margin:0;font-size: 15px;">Sản Phẩm</p>
                                %s
                            </div>
                            <div name="payment_method" style="margin-bottom:12px">
                                <p style="margin:0;font-size: 15px;">Phương thức thanh toán</p>
                                <p style="margin:0;margin-left:6px">%s</p>
                            </div>
                            <div name="location" style="margin-bottom:12px">
                                <p style="margin:0;font-size: 15px;">Địa chỉ giao hàng</p>
                                <p style="margin:0;margin-left:6px">%s</p>
                            </div>
                        </main>
                        <footer style="margin:6px 0px 0px 0px">
                            <div class="row">
                                <div class="col-6" style="font-size:15px">Tổng tiền</div>
                                <div class="col-6" style="font-weight: bold; font-size:15px;padding: 0px">%s %s</div>
                            </div>
                        </footer>
                    </div>
                </div>
                """ % (self.name, product, payment_method, location,
                       '{:,.0f}'.format(sum(self.carrier_id.mapped('fixed_price'), self.amount_total)),
                       self.pricelist_id.currency_id.name)

        channel = self.env['mail.channel'].sudo().search([('id', '=', self.s_thread_id)], limit=1)
        if channel.s_facebook_sender_id:
            url = "{url_facebook}/me/messages".format(
                url_facebook=self.env['ir.config_parameter'].sudo().get_param('advanced_helpdesk.url_facebook'))
            params = dict(
                access_token=self.env['ir.config_parameter'].sudo().get_param(
                    'advanced_helpdesk.facebook_access_token_page')
            )
            headers = {
                'Content-Type': 'application/json'
            }
            element = []
            for line in self.order_line:
                element.append({
                    "title": line.name + '.\n' + 'Số lượng: %s' % int(
                        line.product_uom_qty) + '.\n' + 'Đơn giá: %s' % (
                                 line.price_unit if line.price_unit >= 0 else line.price_unit * -1),
                    "quantity": int(line.product_uom_qty),
                    "price": (
                        line.price_unit if line.price_unit >= 0 else line.price_unit * -1),
                    "currency": line.currency_id.display_name
                })
            if not self.partner_id.street:
                raise ValidationError("Cần bổ sung street 1 trong contact")
            if not self.partner_id.zip:
                raise ValidationError("Cần bổ sung zip trong contact")
            if not self.partner_id.state_id.name:
                raise ValidationError("Cần bổ sung state trong contact")
            if not self.partner_id.country_id.name:
                raise ValidationError("Cần bổ sung country trong contact")
            if not self.order_line:
                raise ValidationError("Đơn hàng chưa có sản phẩm")
            payload = json.dumps({
                "recipient": {
                    "id": channel.s_facebook_sender_id,
                },
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "receipt",
                            "recipient_name": self.partner_id.name,
                            "order_number": self.display_name,
                            "currency": self.pricelist_id.currency_id.name,
                            "payment_method": "Thanh toán khi giao hàng" if self.payment_method == 'cod' else "Thanh toán online",
                            "address": {
                                "street_1": '{name} {phone}, {street}'.format(name=self.partner_id.name,
                                                                              phone=self.partner_id.phone,
                                                                              street=self.partner_id.street),
                                "street_2": self.partner_id.street2 if self.partner_id.street2 else "",
                                "city": self.partner_id.state_id.name,
                                "postal_code": self.partner_id.zip,
                                "state": self.partner_id.state_id.name,
                                "country": self.partner_id.country_id.name
                            },
                            "summary": {
                                "subtotal": self.amount_total,
                                "shipping_cost": self.carrier_id.fixed_price,
                                "total_cost": sum(self.carrier_id.mapped('fixed_price'), self.amount_total)
                            },
                            "elements": element
                        }
                    }
                }
            })
            req_facebook = requests.post(
                url=url,
                params=params,
                headers=headers,
                data=payload,
                verify=False
            )
            if 'error' not in req_facebook.json():
                channel.message_post(
                    partner_ids=channel.s_assign_to.commercial_partner_id.ids,
                    body=body)
                notification = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Thông báo',
                        'message': 'Đã gửi xác nhận đơn hàng cho khách hàng',
                        'type': 'success',  # types: success,warning,danger,info
                        'sticky': False,  # True/False will display for few seconds if false
                    },
                }
                return notification

        elif channel.s_zalo_sender_id:
            url_zalo = "{url_zalo}/oa/message/transaction".format(
                url_zalo=self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_zalo.s_url_endpoint_oa'))
            headers = {
                'Content-Type': 'application/json',
                "access_token": self.env['ir.config_parameter'].sudo().get_param(
                    "advanced_integrate_zalo.access_token")
            }
            payload_product = ""
            for r_product in self.order_line:
                r_payload_product = "Sản phẩm: %s\nSố lượng: %s\nĐơn giá: %s\n\n" % (
                    r_product.name, r_product.product_uom_qty,
                    (r_product.price_unit if r_product.price_unit >= 0 else r_product.price_unit * -1))
                payload_product += r_payload_product
            payload = json.dumps({
                "recipient": {
                    "user_id": channel.s_zalo_sender_id
                },
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "transaction_order",
                            "elements": [
                                {
                                    "type": "header",
                                    "content": "Xác nhận đơn hàng",
                                    "align": "left"
                                },
                                {
                                    "type": "text",
                                    "align": "left",
                                    "content": "• Cảm ơn bạn đã mua hàng tại cửa hàng.<br>• Thông tin đơn hàng của bạn như sau:"
                                },
                                {
                                    "type": "table",
                                    "content": [
                                        {
                                            "value": self.partner_id.name,
                                            "key": "Tên khách hàng"
                                        },
                                        {
                                            "value": '{name} {phone}, {street}, {street2}{city}, {postal_code}, {state}, {country}'.format(
                                                name=self.partner_id.name, phone=self.partner_id.phone,
                                                street=self.partner_id.street,
                                                street2=self.partner_id.street2 + ', ' if self.partner_id.street2 else "",
                                                city=self.partner_id.state_id.name, postal_code=self.partner_id.zip,
                                                state=self.partner_id.state_id.name,
                                                country=self.partner_id.country_id.name),
                                            "key": "Vận chuyển đến"
                                        },
                                        {
                                            "value": '{:,.0f}'.format(
                                                sum(self.carrier_id.mapped('fixed_price'), self.amount_total)),
                                            "key": "Tổng tiền"
                                        }
                                    ]
                                },
                                {
                                    "type": "text",
                                    "align": "center",
                                    "content": "📱Lưu ý điện thoại. Xin cảm ơn!"
                                }],
                            "buttons": [
                                {
                                    "title": "Xem lại giỏ hàng",
                                    "image_icon": "wZ753VDsR4xWEC89zNTsNkGZr1xsPs19vZF22VHtTbxZ8zG9g24u3FXjZrQvQNH2wMl1MhbwT5_oOvX5_szXLB8tZq--TY0Dhp61JRfsAWglCej8ltmg3xC_rqsWAdjRkctG5lXzAGVlQe9BhZ9mJcSYVIDsc7MoPMnQ",
                                    "type": "oa.query.show",
                                    "payload": payload_product
                                }
                            ]
                        }
                    }
                }
            })
            req_zalo = requests.post(
                url=url_zalo,
                headers=headers,
                data=payload,
                verify=False
            )
            if req_zalo.json()['error'] == 0:
                channel.message_post(
                    partner_ids=channel.s_assign_to.commercial_partner_id.ids,
                    body=body)
                notification = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Thông báo',
                        'message': 'Đã gửi xác nhận đơn hàng cho khách hàng',
                        'type': 'success',  # types: success,warning,danger,info
                        'sticky': False,  # True/False will display for few seconds if false
                    },
                }
                return notification
            else:
                raise ValidationError(req_zalo.json().get('message'))

    def create_order_m2(self):
        if not self.partner_id.street:
            raise ValidationError("Cần bổ sung street 1 trong contact")
        if not self.partner_id.state_id.name:
            raise ValidationError("Cần bổ sung state trong contact")
        if not self.partner_id.country_id.name:
            raise ValidationError("Cần bổ sung country trong contact")
        if not self.partner_id.email:
            raise ValidationError("Cần bổ sung email trong contact")
        url = "{base_url}/rest/default/V1/orders/create".format(
            base_url=self.env['ir.config_parameter'].sudo().get_param('magento.url'))
        headers = {
            'Content-Type': 'application/json',
            "Authorization": 'Bearer {token_m2}'.format(
                token_m2=self.env['ir.config_parameter'].sudo().get_param('magento.m2_long_live_token')),
            "User-Agent": "Boo"
        }
        item = []
        if len(self.partner_id.name.split()) == 1:
            first_name = last_name = self.name[0]
            if len(self.name) > 1:
                last_name = self.partner_id.name[1:]
        elif len(self.partner_id.name.split()) > 1:
            first_name = self.partner_id.name.split()[0]
            last_name = self.partner_id.name[len(first_name):]
        for line in self.order_line:
            if not line.is_delivery and not line.is_reward_line:
                item.append({
                    "base_original_price": line.price_unit,
                    "base_price": line.price_unit,
                    "row_total": line.s_lst_price,
                    "discount_amount": line.m2_total_line_discount,
                    "discount_percent": line.discount,
                    "name": line.name,
                    "product_type": "simple",
                    "original_price": line.price_unit,
                    "price": line.s_lst_price,
                    "product_id": line.product_id.id,
                    "qty_ordered": line.product_uom_qty,
                    "sku": line.product_id.default_code,
                    "tax_amount": line.price_tax,
                    "tax_percent": sum(line.tax_id.mapped('amount')),
                    "weight": line.product_id.weight,
                })
        payload = json.dumps({
            "entity": {
                "base_currency_code": self.currency_id.name,
                "base_grand_total": sum(self.carrier_id.mapped('fixed_price'), self.amount_total),
                "grand_total": sum(self.carrier_id.mapped('fixed_price'), self.amount_total),
                "customer_email": self.partner_id.email,
                "customer_firstname": self.partner_id.name,
                "global_currency_code": self.currency_id.name,
                "state": 'new',
                "status": 'pending',
                "store_currency_code": self.currency_id.name,
                "order_currency_code": self.currency_id.name,
                "shipping_amount": self.carrier_id.fixed_price,
                "shipping_incl_tax": self.carrier_id.fixed_price,
                "subtotal": self.amount_total,
                "items": item,
                "billing_address": {
                    "city": self.partner_id.state_id.name,
                    "country_id": self.partner_id.country_id.name,
                    "email": self.partner_id.email,
                    "firstname": first_name,
                    "lastname": last_name,
                    "postcode": self.partner_id.zip if self.partner_id.zip else None,
                    "street": [
                        self.partner_id.street
                    ],
                    "telephone": self.partner_id.phone
                },
                "payment": {
                    "method": "vnpay" if self.payment_method == "online" else "cashondelivery",
                    "amount_ordered": self.amount_total,
                    "base_amount_ordered": self.amount_total,
                    "base_shipping_amount": self.carrier_id.fixed_price,
                    "shipping_amount": self.carrier_id.fixed_price
                },
                "extension_attributes": {
                    "shipping_assignments": [
                        {
                            "shipping": {
                                "address": {
                                    "city": self.partner_shipping_id.state_id.name if self.partner_shipping_id.state_id.name else None,
                                    "country_id": self.partner_shipping_id.country_id.name if self.partner_shipping_id.country_id.name else None,
                                    "email": self.partner_shipping_id.email if self.partner_shipping_id.email else None,
                                    "firstname": first_name,
                                    "lastname": last_name,
                                    "postcode": self.partner_shipping_id.zip if self.partner_shipping_id.zip else None,
                                    "street": [
                                        self.partner_shipping_id.street if self.partner_shipping_id.street else None
                                    ],
                                    "telephone": self.partner_shipping_id.phone if self.partner_shipping_id.phone else None,
                                    "extension_attributes": {
                                        "city_id": self.partner_shipping_id.state_id.id if self.partner_shipping_id.state_id else None,
                                        "district": self.partner_shipping_id.district_id.name_with_type if self.partner_shipping_id.district_id else None,
                                        "district_id": self.partner_shipping_id.district_id.id if self.partner_shipping_id.district_id else None,
                                        "ward": self.partner_shipping_id.ward_id.name_with_type if self.partner_shipping_id.ward_id else None,
                                        "ward_id": self.partner_shipping_id.ward_id.id if self.partner_shipping_id.ward_id else None
                                    }
                                },
                                "method": "magenest_tablerates_magenest_tablerates",
                                "total": {
                                    "shipping_amount": self.carrier_id.fixed_price,
                                    "base_shipping_amount": self.carrier_id.fixed_price,
                                    "shipping_incl_tax": self.carrier_id.fixed_price,
                                    "base_shipping_incl_tax": self.carrier_id.fixed_price,
                                }
                            }
                        }
                    ],
                    "odoo_id": self.id,
                    "odoo_order_name": self.name
                }
            }
        })

        res = requests.put(url=url, headers=headers, data=payload)
        if res.status_code == 200 and "message" not in res.json():
            self.env['ir.logging'].sudo().create({
                'name': 'create_order_from_odoo_to_m2',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': payload,
                'func': 'create_order_m2',
                'line': '0',
            })
        else:
            self.env['ir.logging'].sudo().create({
                'name': 'create_order_from_odoo_to_m2',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': "status code: %s \t message: %s \t parameters: %s" % (
                    res.status_code, res.json().get('message'), res.json().get('parameters')),
                'func': 'create_order_m2',
                'line': '0',
            })
            notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thông báo',
                    'message': 'Tạo đơn hàng Magento Không thành công!',
                    'type': 'warning',  # types: success,warning,danger,info
                    'sticky': False,  # True/False will display for few seconds if false
                },
            }
            return notification
