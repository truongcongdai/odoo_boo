# -*- coding: utf-8 -*-
import werkzeug.urls
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SocialLogin(models.Model):
    _inherit = 'res.users'

    # @api.onchange('email', 'login')
    # def change_email(self):
    #
    #     if not self.env.user.has_group('base.group_system') and 3 not in self.env.user.groups_id.ids:
    #         raise UserError(_("The requested operation cannot be completed due to security restrictions. Please contact your system administrator."))
    #
    # @api.model
    # def signup(self, values, token=None):
    #     if token:
    #         # signup with a token: find the corresponding partner id
    #         partner = self.env['res.partner']._signup_retrieve_partner(token, check_validity=True, raise_exception=True)
    #         # invalidate signup token
    #         partner.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False})
    #
    #         partner_user = partner.user_ids and partner.user_ids[0] or False
    #
    #         # avoid overwriting existing (presumably correct) values with geolocation data
    #         if partner.country_id or partner.zip or partner.city:
    #             values.pop('city', None)
    #             values.pop('country_id', None)
    #         if partner.lang:
    #             values.pop('lang', None)
    #
    #         if partner_user:
    #             # user exists, modify it according to values
    #             if partner_user.login != values.get('login'):
    #                 url = "/web/login?oauth_error=2"
    #                 return werkzeug.utils.redirect(url, 303)
    #             values.pop('login', None)
    #             values.pop('name', None)
    #             partner_user.write(values)
    #             if not partner_user.login_date:
    #                 partner_user._notify_inviter()
    #             return (self.env.cr.dbname, partner_user.login, values.get('password'))
    #         else:
    #             # user does not exist: sign up invited user
    #             values.update({
    #                 'name': partner.name,
    #                 'partner_id': partner.id,
    #                 'email': values.get('email') or values.get('login'),
    #             })
    #             if partner.company_id:
    #                 values['company_id'] = partner.company_id.id
    #                 values['company_ids'] = [(6, 0, [partner.company_id.id])]
    #             partner_user = self._signup_create_user(values)
    #             partner_user._notify_inviter()
    #     else:
    #         # no token, sign up an external user
    #         values['email'] = values.get('email') or values.get('login')
    #         self._signup_create_user(values)
    #
    #     return (self.env.cr.dbname, values.get('login'), values.get('password'))
