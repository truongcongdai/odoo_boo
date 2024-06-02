import base64
import json
from datetime import datetime

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'
    s_zalo_contact_customer = fields.Text('Địa chỉ khách hàng theo Zalo')

    def create_res_partner_zalo_oa(self, info, s_zalo_sender_id=None):
        if s_zalo_sender_id:
            address, phone, name, city, district, is_edit_customer = "", "", "", None, None, False
            customer = self.env['res.partner'].sudo().search([('s_zalo_sender_id', '=', s_zalo_sender_id)], limit=1)
            if info.get('phone'):
                if str(info.get('phone')).startswith('84'):
                    phone = str(info.get('phone')).replace('84', '0', 1) if info.get('phone') else ""
                else:
                    phone = str(info.get('phone'))
            elif info.get('so_dien_thoai'):
                if str(info.get('so_dien_thoai')).startswith('84'):
                    phone = str(info.get('so_dien_thoai')).replace('84', '0', 1) if info.get('so_dien_thoai') else ""
                else:
                    phone = str(info.get('so_dien_thoai'))
            old_customer = self.env['res.partner'].sudo().search([('phone', '=', phone)], limit=1)
            if info.get('address'):
                address = info.get('address')
            elif info.get('dia_chi'):
                address = info.get('dia_chi')
            if info.get('name'):
                name = info.get('name')
            elif info.get('ho_ten'):
                name = info.get('ho_ten')
            if info.get('city'):
                search_city = self.env['res.country.state'].sudo().search([('name', 'ilike', info.get('city'))],
                                                                          limit=1)
                if search_city:
                    city = search_city.id
            elif info.get('city_id'):
                search_city = self.env['res.country.address'].search([('id', '=', int(info.get('city_id')))])
                if search_city:
                    city = search_city.state_id.id
            if info.get('district'):
                search_district = self.env['res.country.address'].sudo().search(
                    ['|', ('name_with_type', 'ilike', info.get('district')), ('name', 'ilike', info.get('district'))],
                    limit=1)
                if search_district:
                    district = search_district.id
            elif info.get('country_district_id'):
                district = self.env['res.country.address'].search([('code', '=', info.get('country_district_id'))]).id
            email = info.get('email')
            dob = datetime.strptime(info.get('dob'), "%d/%m/%Y").date() if info.get('dob') else None
            if not old_customer:
                if info:
                    if not customer:
                        customer = self.env['res.partner'].sudo().create({
                            'street': address,
                            'name': name,
                            'state_id': city,
                            'district_id': district,
                            'ward_id': None,
                            'zip': None,
                            'country_id': None,
                            'email': email,
                            'birthday': dob,
                            'phone': phone,
                            's_zalo_sender_id': s_zalo_sender_id,
                            's_zalo_contact_customer': "Địa chỉ khách hàng theo Zalo:\naddress: %s\ncity: %s\ndistrict: %s\nward : %s" % (
                                address, city, district, str(info.get('ward'))),
                        })
                        rank = self.env['s.customer.rank'].sudo().search(
                            [('total_amount', '<=', customer.loyalty_points)])
                        if rank:
                            customer.sudo().write({
                                'customer_ranked': rank.rank
                            })
                        is_edit_customer=True
                    else:
                        if not customer.phone and not customer.birthday and not customer.state_id and not customer.district_id:
                            customer.write({
                                'street': address,
                                'state_id': city,
                                'district_id': district,
                                'ward_id': None,
                                'zip': None,
                                'email': email,
                                'birthday': dob,
                                'country_id': None,
                                'phone': phone,
                                's_zalo_contact_customer': "Địa chỉ khách hàng theo Zalo:\naddress: %s\ncity: %s\ndistrict: %s\nward : %s" % (
                                    address, city, district, str(info.get('ward'))),
                            })
                            is_edit_customer = True
                        else:
                            customer_new = self.env['res.partner'].sudo().create({
                                'street': address,
                                'name': name,
                                'state_id': city,
                                'district_id': district,
                                'ward_id': None,
                                'zip': None,
                                'country_id': None,
                                'email': email,
                                'birthday': dob,
                                'phone': phone,
                                's_zalo_sender_id': s_zalo_sender_id,
                                's_zalo_contact_customer': "Địa chỉ khách hàng theo Zalo:\naddress: %s\ncity: %s\ndistrict: %s\nward : %s" % (
                                    address, city, district, str(info.get('ward'))),
                            })
                            customer.sudo().write({
                                's_zalo_sender_id': False
                            })
                            is_edit_customer = True
                else:
                    # tạo logging
                    self.env['ir.logging'].sudo().create({
                        'name': '###Zalo_OA: Create_res_partner_zalo_oa',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': 'info is None',
                        'func': 'create_res_partner_zalo_oa',
                        'line': '0',
                    })
            else:
                # If there is an old customer and a new customer, merge them
                if not customer:
                    old_customer.sudo().write(
                        {
                            's_zalo_sender_id': str(s_zalo_sender_id),
                            'street': address,
                            'state_id': city,
                            'district_id': district,
                            'ward_id': None,
                            'email': email,
                            'birthday': dob,
                            'zip': None,
                            'country_id': None,
                            's_zalo_contact_customer': "Địa chỉ khách hàng theo Zalo:\naddress: %s\ncity: %s\ndistrict: %s\nward : %s" % (
                                address, city, district, str(info.get('ward'))),
                        }
                    )
                    is_edit_customer=True
                elif customer and old_customer:
                    old_customer.sudo().write(
                        {
                            's_zalo_sender_id': info.get('s_zalo_sender_id'),
                            'street': address,
                            'state_id': city,
                            'district_id': district,
                            'ward_id': None,
                            'zip': None,
                            'email': email,
                            'birthday': dob,
                            'country_id': None,
                            's_zalo_contact_customer': "Địa chỉ khách hàng theo Zalo:\naddress: %s\ncity: %s\ndistrict: %s\nward : %s" % (
                                address, city, district, str(info.get('ward'))),
                        }
                    )
                    if customer.id != old_customer.id:
                        customer.sudo().write({
                            's_zalo_sender_id': False
                        })
                    is_edit_customer = True
                    # else:
                    #     old_customer.sudo().write(
                    #         {
                    #             's_zalo_sender_id': info.get('s_zalo_sender_id'),
                    #             'street': address,
                    #             'state_id': city,
                    #             'district_id': district,
                    #             'ward_id': None,
                    #             'zip': None,
                    #             'email': email,
                    #             'birthday': dob,
                    #             'country_id': None,
                    #             's_zalo_contact_customer': "Địa chỉ khách hàng theo Zalo:\naddress: %s\ncity: %s\ndistrict: %s\nward : %s" % (
                    #                 address, city, district, str(info.get('ward'))),
                    #         }
                    #     )
                    #     is_edit_customer=True
                else:
                    # tạo logging
                    self.env['ir.logging'].sudo().create({
                        'name': '###Zalo_OA: Create_res_partner_zalo_oa',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'url',
                        'message': str(customer.id) + ' ' + str(old_customer.id),
                        'func': 'create_res_partner_zalo_oa',
                        'line': '0',
                    })
            self.env['ir.logging'].sudo().create({
                'name': '###Zalo_OA: Create_res_partner_zalo_oa',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': "info: " + str(info) + " - " + " s_zalo_sender_id: " + str(
                    s_zalo_sender_id) + " - " + " phone: " + str(phone) + " - " + " old_customer: " + str(
                    old_customer.id) + " - " + " customer: " + str(customer.id) + " - is_edit_customer: " + str(is_edit_customer),
                'func': 'create_res_partner_zalo_oa',
                'line': '0',
            })
            return is_edit_customer
