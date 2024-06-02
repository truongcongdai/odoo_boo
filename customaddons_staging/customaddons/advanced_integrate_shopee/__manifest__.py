{
    'name': "Advanced Integrate Shopee",

    'summary': """
        Advanced Integrate Shopee
        """,

    'description': """""",

    'author': "Magenest JSC",
    'website': "https://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'advanced_pos', 'advanced_sale', 'advanced_inventory', 'advanced_integrate_magento', 'advanced_marketplace'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/s_product_template.xml',
        'views/s_res_config_setting_views.xml',
        'views/s_stock_warehouse.xml',
        'views/s_product_product.xml',
        'views/s_stock_picking_views.xml',
        'views/s_shopee_delivery_method_views.xml',
        'views/s_sale_order.xml',
        'views/s_sale_order_error_views.xml',
        # 'views/s_sale_order_error_views.xml',
        'wizards/s_mass_action_infor_customer.xml',
        'wizards/s_action_print_shipping_label.xml',
        # 'wizards/s_shipping_method.xml',
        'data/ir_cronjob_data.xml',
        'data/s_res_partner.xml'
    ]
}
