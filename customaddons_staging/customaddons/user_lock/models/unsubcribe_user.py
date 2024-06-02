from odoo import models


class InheritResUser(models.Model):
    _inherit = 'res.users'

    # def unlink(self):
    #     list_user_delete = []
    #     project = self.env['project.project'].search([])
    #     for rec in self:
    #         list_user_delete.append(rec.partner_id.id)
    #     for rec in project:
    #         rec.sudo().message_unsubscribe(partner_ids=list_user_delete)
    #     return super(InheritResUser, self).unlink()
    #
    # def write(self, vals):
    #     if 'active' in vals:
    #         list_user_delete = []
    #         project = self.env['project.project'].search([])
    #         for rec in self:
    #             list_user_delete.append(rec.partner_id.id)
    #         for rec in project:
    #             rec.sudo().message_unsubscribe(partner_ids=list_user_delete)
    #
    #     return super(InheritResUser, self).write(vals)



