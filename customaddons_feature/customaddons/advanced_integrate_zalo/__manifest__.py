{
    'name': "Advanced Integrate Zalo",

    'summary': """
        Advanced Integrate Zalo
        """,

    'description': """
        Advanced Integrate Zalo
    """,

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'marketing_automation'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/s_res_config_settings.xml',
        'views/s_template_register_member_zalo.xml',
        'data/cronjob_refresh_token.xml',
        'wizard/s_base_partner_merge.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'advanced_integrate_zalo/static/src/css/s_template_register_member.css',
            'advanced_integrate_zalo/static/src/js/s_district_filter.js',
        ],
    }
}
