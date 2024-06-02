{
    'name': 'Bravo Integration',
    'version': '15.0.0.1.0',
    'summary': 'API for Bravo',
    'description': '''
API list
========

- Invoice details (out_invoice, out_refund)
- Stock details (internal-out, internal-in)
- Online sales stock details
- Online success sale account stock details
- Online fail sale stock details
- Outgoing stock details
- Adjustment stock details
    ''',
    'author': 'Magenest JSC',
    'website': 'https://magenest.com/en/',
    'depends': ['advanced_integrate_magento', 'advanced_inventory', 'odoo_multi_channel_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'data/s_product_gender_data.xml',
        'data/s_res_partner_data.xml',
        'data/s_location_online.xml',
        'views/res_config_settings_views.xml',
        'views/s_product_brand_bravo_mapping.xml',
        'views/stock_location_views.xml',
        'views/product_attribute_views.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_warehouse.xml',
        'views/pos_order_views.xml',
        'views/bravo_mappings/bravo_stock_picking_mapping.xml',
        'views/sale_order_views.xml',
        'wizard/create_multi_product_attributes_views.xml',
    ]
}
