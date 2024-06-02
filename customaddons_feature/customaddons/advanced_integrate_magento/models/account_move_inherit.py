from odoo import fields, models, api


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'
    _description = 'Description'

    magento_do_id = fields.Char()
    payment_method = fields.Char()

    def action_direct_register_payment(self):
        if self.state == 'posted':
            journal_id = self.env['account.journal'].sudo().search([('type', '=', 'cash')], limit=1).id
            # Setting Context for Payment Wizard
            register_wizard = self.env['account.payment.register'].with_context({
                'active_model': 'account.move',
                'active_ids': [self.id]
            })
            register_wizard_obj = register_wizard.create({
                'journal_id': journal_id
            })
            register_wizard_obj.sudo().action_create_payments()
