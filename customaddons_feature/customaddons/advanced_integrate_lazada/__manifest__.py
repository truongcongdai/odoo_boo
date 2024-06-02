{
    'name': 'Lazada Integration',
    'version': '15.0.0.1.0',
    'summary': 'API for Lazada',
    'description': '''
API list
========

- Customer data
    ''',
    'author': 'Magenest JSC',
    'website': 'https://magenest.com/en/',
    'depends': ['base', 'stock', 'product', 'sale', 'advanced_integrate_magento', 'advanced_marketplace'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_lazada.xml',
        'data/data_lazada.xml',
        'views/s_res_config_setting.xml',
        'views/s_stock_warehouse.xml',
        'views/s_product_product.xml',
        'views/s_stock_picking.xml',
        'views/s_sale_order.xml',
        'wizard/infor_customer.xml',
        'views/s_sale_order_lazada_error.xml'
    ]
}
