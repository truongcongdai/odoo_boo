import base64
from datetime import date
import urllib.parse
import requests
from odoo import fields, models, api
from odoo.exceptions import ValidationError, _logger
from werkzeug.urls import url_encode
from odoo.http import request


class SMailMessage(models.Model):
    _inherit = 'mail.message'

    s_helpdesk_message_id = fields.Char()
