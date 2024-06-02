from datetime import datetime, timedelta
from odoo import models, fields, api
import json
import ast
class ClearDataLogging(models.Model):
    _inherit = 'ir.logging'

    @api.model
    def delete_old_logs(self):
        limit_date = datetime.now() - timedelta(days=15)
        old_logs = self.search([('create_date', '<', limit_date)])
        if old_logs:
            old_logs.unlink()

    def _compute_amount_total_order_mkp(self):
        for rec in self:
            if rec.message:
                data = ast.literal_eval(rec.message)
                return data
