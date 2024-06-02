# -*- coding: utf-8 -*-
{
    'name': "Advanced Integrate Vani",

    'summary': """
        Advanced Integrate Vani
        """,

    'description': """
        API of Vani
    """,

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'advanced_pos', 'advanced_integrate_magento', 'point_of_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'views/request_vani_history.xml',
        'views/res_config_settings_views.xml',
        'views/s_res_partner_inherit.xml',
        'views/s_pos_order_inherit.xml',
        'views/s_pos_payment_method.xml',
        'data/s_res_partner_action_server.xml',
        'views/s_coupon_program_views.xml',
        'views/s_coupon_promotion_program_form.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
    ],
    'assets': {
        'point_of_sale.assets': [
            'advanced_integrate_vani/static/src/js/*',
        ],

        'web.assets_qweb': [
            'advanced_integrate_vani/static/src/xml/*',
        ],
    },
}
