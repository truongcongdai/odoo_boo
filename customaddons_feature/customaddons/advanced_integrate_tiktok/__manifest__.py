# -*- coding: utf-8 -*-
{
    'name': "Advanced Integrate Tiktok",

    'summary': """
        Advanced Integrate Tiktok
        """,

    'description': """""",

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'advanced_pos', 'advanced_sale', 'advanced_inventory', 'advanced_integrate_magento', 'advanced_marketplace'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/s_product_product_views.xml',
        'views/s_res_config_setting_views.xml',
        'views/s_sale_order_views.xml',
        'views/s_stock_warehouse.xml',
        'views/s_stock_picking.xml',
        'views/s_template_connect_tiktok.xml',
        'views/s_sale_order_error_views.xml',
        'wizards/mass_action_infor_customer.xml',
        # 'wizards/s_shipping_label_tiktok.xml',
        'wizards/s_shipping_method.xml',
        'data/ir_cronjob_data.xml',
        'data/s_res_partner.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
    ],
    'assets': {
        'point_of_sale.assets': [
        ],

        'web.assets_qweb': [
        ],
    },
}
