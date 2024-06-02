from odoo import fields, models, api


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def _compute_invoice_policy_delivery_carrier(self):
        for r in self:
            if r.invoice_policy == 'real':
                r.invoice_policy = 'estimated'
