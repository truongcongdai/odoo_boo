import base64

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    s_facebook_sender_id = fields.Char()
    s_zalo_sender_id = fields.Char()

    def create_res_partner_helpdesk(self, name, s_facebook_sender_id=None, s_zalo_sender_id=None):
        partner = {
            'name': name
        }
        if not s_facebook_sender_id is None:
            with open("customaddons/advanced_helpdesk/static/src/img/logo_facebook.jpg", "rb") as image_file:
                data = base64.b64encode(image_file.read())
            partner.update({
                'email': '%s@facebook.com' % s_facebook_sender_id,
                'image_1920': data,
                's_facebook_sender_id': s_facebook_sender_id,
            })
        if not s_zalo_sender_id is None:
            with open("customaddons/advanced_helpdesk/static/src/img/logo_zalo.jpg", "rb") as image_file:
                data = base64.b64encode(image_file.read())
            partner.update({
                'email': '%s@zalo.com' % s_zalo_sender_id,
                'image_1920': data,
                's_zalo_sender_id': s_zalo_sender_id,
            })
        self.env['res.partner'].sudo().create(partner)
