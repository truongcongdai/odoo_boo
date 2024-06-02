# -*- coding: utf-8 -*-
{
    'name': "Advanced Marketplace",

    'summary': """
        Advanced Marketplace
        """,

    'description': """""",

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'advanced_pos', 'advanced_sale', 'advanced_inventory', 'advanced_integrate_magento'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/s_stock_picking.xml',
        'views/s_product_product.xml',
        'wizards/s_shipping_label_tiktok.xml',
        'views/s_marketplace_mapping_product.xml',
        'views/s_sale_order_views.xml',
        'views/s_mkp_resync_product.xml',
        'data/ir_cron_data.xml'
    ],
}
