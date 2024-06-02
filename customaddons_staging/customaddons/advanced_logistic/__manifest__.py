# -*- coding: utf-8 -*-
{
    'name': "Advanced Logistic",
    'summary': """
        Advanced Logistic""",
    'description': """
        Advanced Logistic
    """,
    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1.2',
    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'advanced_pos', 'advanced_sale', 'hr', 'advanced_integrate_magento'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/stock_picking.xml',
        # 'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/s_logistic_report_views.xml',
        'views/s_logistic_tracking_views.xml',
        'report/s_stock_picking_report.xml',
        'report/s_stock_report_views.xml',
        'wizards/s_mass_action_infor_receiver.xml',
        # 'report/s_hide_report_print_picking.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # ('remove', 'stock_barcode/static/src/models/barcode_picking_model.js'),
            # 'advanced_logistic/static/src/js/s_barcode_picking_model.js',
            'advanced_logistic/static/src/js/*.js',
        ],
        'web.assets_qweb': [
            'advanced_logistic/static/src/**/*.xml',
        ],
    },

}
