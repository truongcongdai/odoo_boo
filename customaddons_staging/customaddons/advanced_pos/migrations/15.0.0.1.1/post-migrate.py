from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'active_test': False})
    # env = api.Environment(cr, SUPERUSER_ID, {})
    langs = env['res.lang'].search([])
    langs.date_format = '%d-%m-%Y'
