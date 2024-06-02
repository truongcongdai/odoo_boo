from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    warehouses = env['stock.warehouse'].search([])
    warehouses._compute_source_code_name()
