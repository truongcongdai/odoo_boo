# -*- coding: utf-8 -*-
{
    'name': "Advanced Integrate Magento",

    'summary': """
        Advanced Integrate Magento""",

    'description': """
        Advanced Integrate Magento
    """,

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1.3',
    # any module necessary for this one to work correctly
    'depends': ['advanced_sale','advanced_pos', 'magento2x_odoo_bridge'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_inherit.xml',
        'views/pos_order_views.xml',
        'views/product_attribute_views.xml',
        'views/product_views.xml',
        'views/channel_order_mappings_views.xml',
        'views/channel_pick_mappings_views.xml',
        'views/channel_pos_mappings_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/s_channel_inventory_mappings_views.xml',
        'views/s_stock_ware_house_inherit_views.xml',
        'views/multi_channel_sale_views.xml',
        'views/magento_web_stock_views.xml',
        'views/view_partner_form_inherit.xml',
        'views/s_account_move_views.xml',
        'data/ir_cron_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
}
