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
    'depends': ['base','marketing_automation'],

    # always loaded
    'data': [
        'views/s_res_config_settings.xml',
        'data/cronjob_refresh_token.xml'
    ],
}