# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

from . import controllers
from . import models
from . import tools
from . import wizards

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    m2_keys = env['ir.config_parameter'].search([('key', 'like', 'magento.')])
    if m2_keys:
        m2_keys.unlink()
