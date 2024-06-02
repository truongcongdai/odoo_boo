# -*- coding: utf-8 -*-
{
    'name': "User lock",

    'summary': """
        Module Advanced contacts customize by Magenest""",

    'description': """
        Module Advanced contacts customize by Magenest
    """,

    'author': "Magenest.JSC",
    'website': "http://www.magenest.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.1.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'auth_signup', 'hr'],
    'data': [
        'views/additional_res_users_views.xml',
        'views/res_users_view_form_profile_inherit.xml'
    ],
}
