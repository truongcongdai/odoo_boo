# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'RFM Analysis - Marketing Strategy',
    'version': '15.1',
    'price': 199,
    'currency': 'EUR',
    'category': 'sale',
    'summary': """	
		RFM Analysis - A powerful marketing strategy
        RFM analysis increases business sales. It enables personalized marketing, increases engagement, and allows you to create specific, relevant offers to the right groups of customers.        
        RFM analysis allows marketers to target specific clusters of customers with communications that are much more relevant for their particular behavior – and thus generate much higher rates of response, plus increased loyalty and customer lifetime value.

        eCommerce sales analysis with RFM technique
        RFM analysis is a data driven customer behavior segmentation technique. 
        RFM analysis increases eCommerce sales. It enables personalized marketing, increases engagement, and allows you to create specific, relevant offers to the right groups of customers.
        It helps eCommerce sellers, online stores, marketplaces to boost their sales
        Directly integrated with Email Marketing, Automated mailing list generation feature
        Dynamic rules can be created for Sales Team and Company wise, according to that customer will be assigned a RFM segment at a company level as well as sales team level.
		""",
    'website': 'https://www.setuconsulting.com',
    'support': 'apps@setuconsulting.com',
    'description': """
        RFM analysis is a data driven customer behavior segmentation technique.
        RFM stands for recency, frequency, and monetary value.
        RFM is a method used for analyzing customer value.
        As you can gauge, RFM analysis is a handy method to find your best customers, understand their behavior and then run targeted email / marketing campaigns to increase sales, satisfaction and customer lifetime value.

        RFM analysis increases eCommerce sales.
        It enables personalized marketing, increases engagement, and allows you to create specific, relevant offers to the right groups of customers.
        RFM analysis allows marketers to target specific clusters of customers with communications that are much more relevant for their particular behavior – and thus generate much higher rates of response, plus increased loyalty and customer lifetime value.

        RFM Analysis, our solution helps you to run targeted email / marketing campaigns to increase sales, satisfaction and customer lifetime value.
        With our solution you can easily bifurcate your customers by RFM segments which gives you a clear idea about your marketing strategy.  
    """,
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'maintainer': 'Setu Consulting Services Private Limited',
    'license': 'OPL-1',
    'sequence': 25,
    'depends': ['sale_stock', 'mass_mailing_sale', 'sale_crm'],
    'images': ['static/description/banner.gif'],
    'data': [
        'security/setu_rfm_analysis_security.xml',
        'security/ir.model.access.csv',
        'data/base_setup_data.xml',
        'views/setu_rfm_analysis_dashboard_views.xml',
        'views/company.xml',
        'views/rfm_segment.xml',
        'views/setu_rfm_configuration.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner.xml',
        'views/team_customer_segment.xml',
        'views/update_customer_segment.xml',
        'views/rfm_quotation.xml',
        'views/global_rules_conf.xml',
        'views/copy_rules_wizard.xml',
        'views/rfm_segment_configuration.xml',
        'views/rfm_segment_team_configuration.xml',
        'views/rfm_partner_history.xml',
        'views/crm_team.xml',
        # 'data/db_operation.xml',
        'data/rfm_segment.xml',
        'data/rfm_score.xml',
        'data/ir_cron.xml',
        'db_function/gather_sales_data.sql',
        'db_function/get_sales_data_for_rfm.sql',
        'db_function/get_rfm_analysis_data_static.sql',
        'db_function/get_rfm_analysis_data_dynamic.sql',
        'db_function/set_rfm_segment_values_company.sql',
        'db_function/set_rfm_segment_values_team.sql',
        'db_function/overall_company_customer_data.sql',
        'db_function/overall_company_data.sql',
        'db_function/overall_team_data.sql',
        'db_function/compute_sp.sql',
        'db_function/update_customer_rfm_segment.sql',
        'reports/rfm_yearly_analysis_by_segment.xml',
        'views/search_views.xml'

    ],
    'qweb': [
        'static/src/xml/dashboard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/setu_rfm_analysis/static/src/js/rfm_dashboard.js',
            'setu_rfm_analysis/static/src/scss/graph.scss'
        ],
        'web.assets_qweb': [
            'setu_rfm_analysis/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    # 'pre_init_hook': 'pre_init',
    #'live_test_url': 'http://95.111.225.133:5929/web/login',
}
