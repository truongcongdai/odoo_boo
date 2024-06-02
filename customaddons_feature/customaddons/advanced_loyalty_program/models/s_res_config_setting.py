from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import pytz
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    s_period_reset_customer_rank = fields.Datetime(string='Chu kỳ reset hạng', config_parameter='loyalty.period_reset_customer_rank')
    s_value_config_period = fields.Integer(string='Sau', config_parameter='loyalty.value_config_period', default=1)
