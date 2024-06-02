from ast import literal_eval
from collections import defaultdict
import functools
import itertools
import logging
import psycopg2
import datetime

from odoo import api, fields, models, Command
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


_logger = logging.getLogger('odoo.addons.base.partner.merge')

class SMergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    is_merge_partner = fields.Boolean(string='Xác nhận gộp', default=False)

    def action_merge(self):
        if self.is_merge_partner:
            return super(SMergePartnerAutomatic, self.with_context({MODULE_UNINSTALL_FLAG: True})).action_merge()
        else:
            return super(SMergePartnerAutomatic, self).action_merge()