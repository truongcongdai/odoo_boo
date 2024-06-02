# -*- coding: utf-8 -*-
{
    'name': "advanced_reload_program",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ["coupon", "point_of_sale",'pos_coupon'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config.xml',
        'wizard/action_set_pos_program.xml',
        'data/ir_cron.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'advanced_reload_program/static/src/js/ControlButtons/ReloadCouponsButton.js',
            'advanced_reload_program/static/src/js/ControlButtons/ReloadProgramsButton.js',
        ],
        'web.assets_qweb': [
            'advanced_reload_program/static/src/xml/**/*',
        ],
    },
}
