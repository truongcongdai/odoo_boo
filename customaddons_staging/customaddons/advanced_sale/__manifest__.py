# -*- coding: utf-8 -*-
{
    'name': "Advanced Sales",
    'summary': """
        Advanced POS""",
    'description': """
        Advanced POS
    """,
    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'advanced_pos', 'base', 'hr', 'account','coupon', 'odoo_multi_channel_sale', 'sale_coupon','sale_stock', 'delivery'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/group.xml',
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
        'views/res_config_settings_views.xml',
        'views/product_product.xml',
        'views/s_stock_picking_views.xml',
        'wizards/display_order_line_data.xml',
        'wizards/order_line_data_report.xml',
        # 'views/boo_sale_report.xml',
        'views/s_report_dashboard_order_views.xml',
        'views/sell_wholesale_views.xml',
        'views/account_move_view_form_inherit.xml',
        'views/s_sale_order_loyalty_program_views.xml',
        'views/s_sale_report_views.xml',
        'views/report_sale_order_with_program_views.xml',
        'data/ir_cron_data.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'advanced_sale/static/src/css/s_client_view.css',

        ],
    },
}
