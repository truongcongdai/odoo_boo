# -*- coding: utf-8 -*-
{
    'name': "Advanced POS",
    'summary': """
        Advanced POS""",
    'description': """
        Advanced POS
    """,
    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1.2',
    # any module necessary for this one to work correctly
    'depends': ['base', 'pos_coupon', 'gift_card', 'pos_gift_card', 'contacts', 'mail'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/gift_card_inherit_views.xml',
        'views/product_template_inherit.xml',
        'views/res_partner_inherit.xml',
        'views/pos_config_inherit.xml',
        'views/coupon_coupon_inherit.xml',
        'views/coupon_program_views.xml',
        'views/s_order_not_bag.xml',
        'views/s_pos_order.xml',
        'views/s_gift_card_inherit.xml',
        'views/pos_order_inherit.xml',
        'views/s_pos_config_views.xml',
        'views/s_pos_order_report.xml',
        'views/s_product_product.xml',
        'wizard/mass_insert_coupon_program_views.xml',
        'wizard/mass_insert_pricelist.xml',
        'wizard/mass_import_coupon_coupon_views.xml',
        'data/pos_payment_method_data.xml',
        'data/ir_cron_data.xml',
        'views/s_import_coupon_coupon_views.xml',
        'views/s_product_pricelist.xml',
        'views/s_lost_bill_views.xml',
        'views/product_template_attribute_line_inherit.xml',
        'views/s_pos_payment_views_inherit.xml',
        'views/s_pos_payment_method_views.xml',
        'views/report_pos_order_with_program_views.xml',
        'views/s_report_saledetails.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            ('remove', 'point_of_sale/static/src/js/Misc/NumberBuffer.js'),
            ('remove', 'point_of_sale/static/src/js/Screens/ProductScreen/ProductScreen.js'),
            # ('remove', '/pos_coupon/static/src/js/coupon.js'),
            # ('remove', '/point_of_sale/static/src/js/models.js'),
            'advanced_pos/static/src/js/**/*',
            'advanced_pos/static/src/js/*',
            'advanced_pos/static/src/css/**/*',

        ],

        'web.assets_qweb': [
            'advanced_pos/static/src/xml/**/*',
        ],
    },

}
