# -*- coding: utf-8 -*-
{
    'name': "Advanced Employee ",

    'summary': """
        Advanced Employee
        """,

    'description': """
        Advanced Employee
    """,

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'advanced_sale'],

    # always loaded
    'data': [
        'views/s_hr_employee_views.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
    ],
}
