from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    channels = env['multi.channel.sale'].search([])
    if channels:
        channels.set_info_urls()
    multi_channel_sale_menu = env.ref('odoo_multi_channel_sale.parent_menu_multi_channel')
    multi_channel_sale_menu.write({
        'groups_id': [(6, 0, env.ref('base.group_no_one').ids)]
    })
