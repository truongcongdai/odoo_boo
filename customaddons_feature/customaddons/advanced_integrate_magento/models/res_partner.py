from json import dumps
from urllib.parse import urljoin
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from ..tools.api_wrapper import _create_log
from ..tools.common import invalid_response

_logger = logging.getLogger(__name__)
import time
import re


class ResPartner(models.Model):
    _inherit = ['res.partner']
    is_warehouse = fields.Boolean(
        string='Là kho hàng', default=False)
    phone_delivery = fields.Char(string='Điện thoại giao hàng')
    fail_sync_cusomter_rank = fields.Boolean('Đồng bộ hạng m2 thất bại', default=False)
    is_partner_sync_m2 = fields.Boolean(string='Là khách hàng cần đồng bộ thông tin lên M2', default=False)

    @api.constrains('is_warehouse', 'phone')
    def check_unique_phone_for_customer(self):
        for rec in self:
            # Check contact là khách hàng
            if not rec.is_warehouse:
                if rec.phone:
                    phone = rec.env['res.partner'].search([('phone', '=', rec.phone), ('type', '=', 'contact')])
                    if len(phone) > 1:
                        raise ValidationError(_('Số điện thoại khách hàng đã tồn tại.'))
            #     else:
            #         raise UserError(_('Số điện thoại là trường bắt buộc'))
            # else:
            #     if not rec.phone:
            #         raise UserError(_('Số điện thoại là trường bắt buộc'))

    @api.model
    def get_record_to_sync_rank(self):
        limit_rank_size = self.env['ir.config_parameter'].get_param('advanced_pos.get_customer_rank_limit', '1000')
        return self.env['res.partner'].sudo().search(
            [
                ('check_sync_customer_rank', '=', False),
                ('phone', '!=', False),
                ('type', '=', 'contact'),
                ('fail_sync_cusomter_rank', '=', False),
            ],
            limit=int(limit_rank_size)
        ).filtered(lambda partner: len(
            partner.phone) > 0 and partner.customer_ranked and partner.sale_order_count >= 0 and not partner.check_sync_customer_rank)

    def _get_magento_customer_rank_url(self):
        self.ensure_one()
        if not self.phone:
            raise ValidationError('Customer phone is required to sync M2!')
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        # endpoint = f'/rest/{magento_odoo_bridge.store_code}/V1/magenest/rewardpoint/{self.phone}/updateRewardPoint'
        endpoint = f'/rest/{magento_odoo_bridge.store_code}/V1/magenest/odooIntegration/{self.phone}/updateCustomerRank'
        return urljoin(magento_odoo_bridge.url, endpoint)

    def _build_magento_customer_rank_data(self):
        self.ensure_one()
        # pos_order_ids = self.pos_order_ids.filtered(lambda am: am.state == 'paid' or am.state == 'invoiced')
        # amount_so = self.get_amount_so_invoice(self.sale_order_ids)
        # amount_pos_order = self.get_amount_pos_order(pos_order_ids)
        # total_amount = amount_so + amount_pos_order
        green_points = 0
        commercial_points = 0
        if self.history_green_points_ids:
            green_points += sum(self.history_green_points_ids.mapped('diem_cong'))
        if self.history_points_ids:
            commercial_points += sum(self.history_points_ids.mapped('diem_cong'))
        if self.s_history_loyalty_point_so_ids:
            commercial_points += sum(self.s_history_loyalty_point_so_ids.mapped('diem_cong'))
        if self.loyalty_points:
            return {
                'customer_rank': self.customer_ranked,
                'total_amount': int(self.loyalty_points),
                'commercial_points': commercial_points,
                'green_points': green_points
            }

    @api.model
    def cron_post_customer_rank_m2(self, auto_commit):
        start_time = time.time()
        try:
            count = 0
            ####Đồng bộ lại hạng thủ công bằng tay
            if len(self) > 0:
                customer_need_sync = self
            else:
                customer_need_sync = self.get_record_to_sync_rank()
            sdk = self.env.ref('magento2x_odoo_bridge.magento2x_channel').get_magento2x_sdk()['sdk']
            customer_to_unsync = self.browse([])
            fail_sync_customer_ranked = self.browse([])
            response_text = []
            if len(customer_need_sync) > 0:
                limit_while = len(customer_need_sync)
                while (time.time() - start_time) <= 60 and count <= 100:
                    try:
                        if count < limit_while:
                            sync_url = customer_need_sync[count]._get_magento_customer_rank_url()
                            sync_data = dumps(customer_need_sync[count]._build_magento_customer_rank_data())
                            resp = sdk._post_data(url=sync_url, data=sync_data)
                            # if resp.get('message'):
                            #     _create_log(
                            #         name=resp['message'],
                            #         message=f'{fields.Datetime.now().isoformat()} POST {sync_url}\n' +
                            #                 f'data={sync_data}\n' +
                            #                 f'response={resp}\n',
                            #         func='cron_post_customer_rank_m2'
                            #     )
                            #     continue
                            if resp.get('message'):
                                response = {
                                    'partner_id': customer_need_sync[count].id,
                                    'Tên khách hàng': customer_need_sync[count].name,
                                    'Số điện thoại': customer_need_sync[count].phone,
                                    'Error_message': resp.get('message')
                                }
                                response_text.append(response)
                                fail_sync_customer_ranked |= customer_need_sync[count]
                            else:
                                customer_to_unsync |= customer_need_sync[count]
                            count += 1
                        else:
                            break
                    except Exception as e:
                        _logger.error(e.args)
                        # _create_log(name='cron_sync_customer_rank_fail', message=e.args, func='cron_post_customer_rank_m2')
            # if customer_to_unsync:
            #     customer_to_unsync.write({'check_sync_customer_rank': True})
            if fail_sync_customer_ranked:
                fail_sync_customer_ranked.sudo().write({'fail_sync_cusomter_rank': True})
                self.env['ir.logging'].sudo().create({
                    'name': 'Khách hàng đồng bộ hạng thất bại',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'message': str(response_text),
                    'path': 'url',
                    'func': 'cron_post_customer_rank_m2',
                    'line': '0',
                })
            # else:
            #     if len(self) > 0 and customer_to_unsync:
            #         customer_to_unsync.write({'fail_sync_cusomter_rank': False})
            if auto_commit:
                self.env.cr.commit()
            check_time = time.time() - start_time
            if customer_to_unsync:
                customer_to_unsync.write({'check_sync_customer_rank': True})
            if not fail_sync_customer_ranked:
                if len(self) > 0 and customer_to_unsync:
                    customer_to_unsync.write({'fail_sync_cusomter_rank': False})
        except Exception as e:
            _logger.error(e.args)
            self.env['ir.logging'].sudo().create({
                'name': 'Cron Customer Rank',
                'message': str(e),
                'func': 'cron_post_customer_rank_m2',
            })

    def push_data_customer(self, phone, data, type):
        try:
            magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
            sdk = magento_odoo_bridge.get_magento2x_sdk()['sdk']
            sync_data = dumps(data)
            endpoint = None
            if type == 'updateRewardPoint':
                endpoint = urljoin(magento_odoo_bridge.url,
                                   f'/rest/{magento_odoo_bridge.store_code}/V1/magenest/rewardpoint/{phone}/updateRewardPoint')
            elif type == 'updateCurrentPoint':
                endpoint = urljoin(magento_odoo_bridge.url,
                                   f'/rest/{magento_odoo_bridge.store_code}/V1/magenest/rewardpoint/{phone}/updateCurrentPoint')
            if endpoint:
                resp = sdk._post_data(url=endpoint, data=sync_data)
        except Exception as e:
            _logger.error(e.args)
            # _create_log(name='cron_sync_customer_rank_fail', message=e.args, func='cron_post_customer_rank_m2')

    def _cron_sync_customer_loyalty_point_to_magento(self):
        loyalty_point_ids = self.env['s.customer.loyalty.points'].sudo().search([('type_points', '=', 'reward')],
                                                                                limit=1000)
        if loyalty_point_ids:
            for loyalty_point_id in loyalty_point_ids:
                if loyalty_point_id.partner_id and loyalty_point_id.partner_id.phone:
                    if loyalty_point_id.type_points == 'reward':
                        loyalty_points = {
                            "reward_points": {
                                "commercial_points": loyalty_point_id.commercial_points,
                                "commercial_points_comment": loyalty_point_id.commercial_points_comment,
                                "commercial_date": str(loyalty_point_id.commercial_date),
                                "green_points": int(loyalty_point_id.green_points),
                                "green_points_comment": loyalty_point_id.green_points_comment,
                                "green_date": str(loyalty_point_id.green_date),
                            }
                        }
                        self.push_data_customer(loyalty_point_id.partner_id.phone, loyalty_points, 'updateRewardPoint')
                    # elif loyalty_point_id.type_points == 'current':
                    #     loyalty_points = {
                    #         "current_points": loyalty_point_id.current_points,
                    #         "green_points": loyalty_point_id.green_points,
                    #         "commercial_points": loyalty_point_id.commercial_points
                    #     }
                    #     self.push_data_customer(loyalty_point_id.partner_id.phone, loyalty_points, 'updateCurrentPoint')
                    loyalty_point_id.sudo().unlink()
                    self._cr.commit()

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        if res.type == 'contact':
            res.sudo().write({
                'is_partner_sync_m2': True
            })
        return res


    def write(self, vals):
        if vals.get('loyalty_points'):
            green_points = 0
            commercial_points = 0
            current_points = 0
            partner_id = None
            # if self.type == 'contact' or (self.type == 'delivery' and not self.parent_id):
            #     if self.history_green_points_ids:
            #         green_points += sum(self.history_green_points_ids.mapped('diem_cong'))
            #     if self.history_points_ids:
            #         commercial_points += sum(self.history_points_ids.mapped('diem_cong'))
            #     if self.s_history_loyalty_point_so_ids:
            #         commercial_points += sum(self.s_history_loyalty_point_so_ids.mapped('diem_cong'))
            #     current_points = int(vals.get('loyalty_points'))
            #     partner_id = self.id
            # elif self.type == 'delivery' and self.parent_id and self.parent_id.type == 'contact':
            #     if self.parent_id.history_green_points_ids:
            #         green_points += sum(self.parent_id.history_green_points_ids.mapped('diem_cong'))
            #     if self.parent_id.history_points_ids:
            #         commercial_points += sum(self.parent_id.history_points_ids.mapped('diem_cong'))
            #     if self.parent_id.s_history_loyalty_point_so_ids:
            #         commercial_points += sum(self.parent_id.s_history_loyalty_point_so_ids.mapped('diem_cong'))
            #     current_points = self.parent_id.loyalty_points
            #     partner_id = self.parent_id.id
            # self.env['s.customer.loyalty.points'].sudo().create({
            #     "current_points": current_points,
            #     "green_points": green_points,
            #     "commercial_points": commercial_points,
            #     "partner_id": partner_id,
            #     "type_points": "current"
            # })
            # self.push_data_customer(self.phone, loyalty_points, 'updateCurrentPoint')
        res = super(ResPartner, self).write(vals)

        # logan update stock warehouse field
        data_update_sync_magento = ['name', 'zip', 'phone', 'country_id', 'street', 'city_id', 'district_id',
                                    'ward_id']
        if any([key in vals for key in data_update_sync_magento]):
            for rec in self:
                if rec.is_warehouse:
                    # related_stock_warehouse = self.env['stock.warehouse'].sudo().search([('partner_id', '=', rec.id)])
                    # if related_stock_warehouse:
                    if not rec.name:
                        raise UserError('Tên là trường bắt buộc')
                    if not rec.zip:
                        raise UserError('Zipcode là trường bắt buộc')
                    if not rec.phone:
                        raise UserError('Số điện thoại là trường bắt buộc')
                    if not rec.country_id:
                        raise UserError('Quốc gia là trường bắt buộc')
                    if not rec.street:
                        raise UserError('Địa chỉ là trường bắt buộc')
                    if not rec.city_id:
                        raise UserError('Thành phố là trường bắt buộc')
                    if not rec.district_id:
                        raise UserError('Quận huyện là trường bắt buộc')
                    if not rec.ward_id:
                        raise UserError('Thị xã là trường bắt buộc')
                    related_stock_warehouse = self.env['stock.warehouse'].sudo().search(
                        [('partner_id', '=', rec.id)])
                    if related_stock_warehouse:
                        related_stock_warehouse.force_update_magento_source_info()
        if not self.env.context.get('is_call_api'):
            data_check_sync_m2 = ['birthday', 'email', 'name', 'gender', 'phone']
            if any([key in vals for key in data_check_sync_m2]):
                partner_ids = self.filtered(lambda r: r.type == 'contact')
                if partner_ids:
                    for rec in partner_ids:
                        rec.sudo().write({
                            'is_partner_sync_m2': True
                        })
        return res

    def cron_sync_update_partner_data(self, limit_search=False):
        try:
            if not limit_search:
                limit_search = 1000
            partner_ids = self.sudo().search([('is_partner_sync_m2', '=', True),('email','!=',False)], limit=limit_search)
            if partner_ids:
                partner_ids.update_partner_sync_to_m2()
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'api-update-customer-m2',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'update_partner_sync_to_m2',
                'line': '0',
            })
            return invalid_response(head='update_customer_data_failures', message=e.args)

    def update_partner_sync_to_m2(self):
        try:
            sdk = self.env.ref('magento2x_odoo_bridge.magento2x_channel').get_magento2x_sdk()['sdk']
            magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
            endpoint = f'/rest/{magento_odoo_bridge.store_code}/V1/customers'
            url_update_partner_sync_to_m2 = urljoin(magento_odoo_bridge.url, endpoint)
            for partner_id in self:
                regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
                if (re.fullmatch(regex, partner_id.email)):
                    gender = 0
                    if partner_id.gender == 'male':
                        gender = 1
                    elif partner_id.gender == 'female':
                        gender = 2
                    if len(partner_id.name.split()) == 1:
                        first_name = last_name = partner_id.name[0]
                        if len(partner_id.name) > 1:
                            last_name = partner_id.name[1:]
                    elif len(partner_id.name.split()) > 1:
                        first_name = partner_id.name.split()[0]
                        last_name = partner_id.name[len(first_name):]

                    data_update_partner_sync_to_m2 = dumps({
                        "customer": {
                            "dob": str(partner_id.birthday) if partner_id.birthday else "",
                            "email": partner_id.email,
                            "firstname": first_name,
                            "lastname": last_name,
                            "middlename": False,
                            "gender": gender,
                            "store_id": "1",
                            "website_id": "1",
                            "custom_attributes": [
                                {
                                    "attribute_code": "telephone",
                                    "value": partner_id.phone
                                },
                                {
                                    "attribute_code": "odoo_id",
                                    "value": partner_id.id
                                },
                                {
                                    "attribute_code": "total_period_revenue",
                                    "value": partner_id.total_period_revenue
                                },
                                {
                                    "attribute_code": "total_reality_revenue",
                                    "value": partner_id.total_reality_revenue
                                },
                                {
                                    "attribute_code": "accumulation_points",
                                    "value": partner_id.loyalty_points
                                },
                                {
                                    "attribute_code": "customer_ranked",
                                    "value": partner_id.customer_ranked
                                }
                            ]
                        },
                        "password": "Abcd1234",
                        "redirectUrl": "string"
                    })
                    resp = sdk._post_data(url=url_update_partner_sync_to_m2, data=data_update_partner_sync_to_m2)
                    if resp.get('message'):
                        self.env['ir.logging'].sudo().create({
                            'name': 'api-update-customer-m2',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'path': 'url',
                            'message': resp.get('message'),
                            'func': 'update_partner_sync_to_m2',
                            'line': '0',
                        })
                    else:
                        partner_id.sudo().write({
                            'is_partner_sync_m2': False
                        })
                else:
                    partner_id.sudo().write({
                        'is_partner_sync_m2': False
                    })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'api-update-customer-m2',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'update_partner_sync_to_m2',
                'line': '0',
            })
            return invalid_response(head='update_customer_data_failures', message=e.args)

    def _compute_update_data_partner_delivery(self):
        for r in self:
            if r.type == 'delivery':
                if not r.parent_id and not r.name and r.phone:
                    self._cr.execute(
                        """UPDATE res_partner SET name = %s WHERE id = %s""", (r.phone, r.id))
                if r.name and len(r.name) > 30:
                    self._cr.execute(
                        """UPDATE res_partner SET partner_note = %s WHERE id = %s""", (str(r.name), r.id))
                    self._cr.execute(
                        """UPDATE res_partner SET name = %s WHERE id = %s""", (r.name[0:29], r.id))
                if not r.phone and r.parent_id:
                    self._cr.execute(
                        """UPDATE res_partner SET name = %s WHERE id = %s""",
                        (r.parent_id.name, r.id))
                    if not r.phone_delivery:
                        self._cr.execute(
                            """UPDATE res_partner SET phone_delivery = %s WHERE id = %s""",
                            (r.parent_id.phone, r.id))
                if r.parent_id and r.phone:
                    if not r.name and r.parent_id.name:
                        if len(r.parent_id.name) > 30:
                            self._cr.execute(
                                """UPDATE res_partner SET partner_note = %s WHERE id = %s""",
                                (str(r.parent_id.name), r.id))
                            self._cr.execute(
                                """UPDATE res_partner SET name = %s WHERE id = %s""", (r.parent_id.name[0:29], r.id))
                        else:
                            self._cr.execute(
                                """UPDATE res_partner SET name = %s WHERE id = %s""", (r.parent_id.name, r.id))
                    self._cr.execute(
                        """UPDATE res_partner SET phone_delivery = %s WHERE id = %s""", (r.phone, r.id))
                    self._cr.execute(
                        """UPDATE res_partner SET phone = NULL WHERE id = %s""", (r.id,))
                if not r.parent_id.pos_order_ids and not r.parent_id.sale_order_ids and (
                        r.pos_order_ids or r.sale_order_ids) or not r.parent_id:
                    if r.parent_id.phone != r.phone:
                        self._cr.execute("""UPDATE res_partner SET type = 'contact' WHERE id = %s""", (r.id,))

    def mass_action_sync_customer_rank(self):
        customer_to_unsync = self.browse([])
        for r in self:
            if not r.check_sync_customer_rank and r.phone and r.customer_ranked:
                sdk = self.env.ref('magento2x_odoo_bridge.magento2x_channel').get_magento2x_sdk()['sdk']
                sync_url = r._get_magento_customer_rank_url()
                sync_data = dumps(r._build_magento_customer_rank_data())
                resp = sdk._post_data(url=sync_url, data=sync_data)
                customer_to_unsync |= r
        if customer_to_unsync:
            customer_to_unsync.write({'check_sync_customer_rank': True})
