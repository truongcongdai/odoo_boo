# -*- coding: utf-8 -*-
{
    'name': "advanced_helpdesk",

    'summary': """
        Integrate Facebook, Zalo in module Helpdesk""",

    'description': """
        Integrate Facebook, Zalo in module Helpdesk
    """,

    'author': "Magenest JSC",
    'website': "https://magenest.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'helpdesk', 'sale_management', 'advanced_integrate_magento','advanced_integrate_zalo'],

    # always loaded
    'data': [
        'security/groups.xml',
        'data/ir_cronjob_data.xml',
        'data/utm_source.xml',
        'views/helpdesk_team.xml',
        'views/res_config_settings.xml',
        'views/s_helpdesk_ticket.xml',
        'views/s_mail_channel.xml',
        'views/sale_order.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'assets': {
        'mail.assets_discuss_public': [
            'advanced_helpdesk/static/src/components/*/*',
        ],
        'web.assets_qweb': [
            'advanced_helpdesk/static/src/components/*/*.xml',
        ],
        'web.assets_backend': [
            'advanced_helpdesk/static/src/components/*/*.js',
        ],
    }

}
