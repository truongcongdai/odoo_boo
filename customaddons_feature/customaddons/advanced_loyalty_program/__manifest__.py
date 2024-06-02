# -*- coding: utf-8 -*-
{
    'name': "Advanced Loyalty Program",

    'summary': """
        Advanced Loyalty Program
        """,

    'description': """""",

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'advanced_pos', 'advanced_sale', 'advanced_inventory', 'advanced_integrate_magento', 'sms'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/s_loyalty_program.xml',
        'views/s_res_partner.xml',
        'views/s_loyalty_reward.xml',
        'views/s_res_config_setting.xml',
        'views/s_product_product.xml',
        'data/ir_cronjob_data.xml',
        'data/ir_config_parameter_data.xml',
        'views/s_customer_rank.xml',
        'views/s_res_partner_otp.xml',
        'views/s_sale_order_view.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            ('remove', 'advanced_pos/static/src/js/ProductScreen/s_product_item_list.js'),
            'advanced_loyalty_program/static/src/js/ProductScreen/s_product_screen.js',
            'advanced_loyalty_program/static/src/js/PaymentScreen/s_payment_screen.js',
            'advanced_loyalty_program/static/src/css/PaymentScreen/s_payment_method.css',
            'advanced_loyalty_program/static/src/js/**/*',
            'advanced_loyalty_program/static/src/css/**/*',
        ],
        'web.assets_qweb': [
            'advanced_loyalty_program/static/src/xml/PaymentScreen/s_payment_screen.xml',
            'advanced_loyalty_program/static/src/xml/ClientDetails/s_sale_order_list.xml',
            'advanced_loyalty_program/static/src/xml/**/*',
        ],
    },
}
