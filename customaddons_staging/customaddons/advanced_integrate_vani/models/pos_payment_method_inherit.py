from odoo import models,fields, _


class VaniPosPaymentMethodInherit(models.Model):
    _inherit = 'pos.payment.method'
    is_e_wallet = fields.Boolean('E-Wallet')
    is_card = fields.Boolean('Card')
    is_cod = fields.Boolean('COD')