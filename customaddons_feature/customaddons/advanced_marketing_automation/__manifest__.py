# -*- coding: utf-8 -*-
{
    'name': "Advanced Marketing Automation",

    'summary': """
        Advanced Marketing Automation
        """,

    'description': """
        Marketing Automation
    """,

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sms', 'marketing_automation', 'advanced_integrate_magento', 'mass_mailing', 'point_of_sale',
                'mass_mailing_sms', 'marketing_automation_sms', 'advanced_integrate_zalo'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        "views/s_res_partner.xml",
        "views/s_mailing_mailing.xml",
        "views/s_marketing_campaign.xml",
        "views/s_marketing_activity.xml",
        "views/mailing_trace.xml",
        "views/s_marketing_participant_views.xml",
        "views/s_res_config_settings.xml",
        "wizard/mailing_sms_test_views.xml",
        'data/cronjob_data_res_partner.xml'
    ],

}
