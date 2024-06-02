from odoo import fields, models, api, _
from odoo.exceptions import UserError

class SReportInternalTransferWizard(models.Model):
    _name = 's.report.internal.transfer.wizard'
    _description = ''

    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')

    def confirm_export(self):
        if self.date_from <= self.date_to:
            internal_transfer_ids = self.env['s.internal.transfer.line'].search([('create_date', '>=', self.date_from),('create_date', '<=', self.date_to)])
        else:
            raise UserError(_('Ngày bắt đầu phải nhỏ hơn ngày kết thúc'))
        return {
            'name': _('# Báo cáo lệnh điều chuyển'),
            'view_mode': 'tree',
            'res_model': 's.internal.transfer.line',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('advanced_inventory.s_report_internal_transfer_tree_view').id,
            'domain': [('id', 'in', internal_transfer_ids.ids)],
            'target': 'current',
            'context': {'create': False, 'edit': False, 'delete': False},
        }