# -*- coding: utf-8 -*-
{
    'name': "advanced_inventory",
    'summary': """
    Advanced Inventory
        """,
    'description': """
        Advanced Inventory
    """,
    'author': "Magenest JSC",
    'website': "http://www.magenest.com",
    'category': 'Uncategorized',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'advanced_pos', 'advanced_sale', 'hr', 'advanced_integrate_magento'],
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/product_attribute_value_views.xml',
        'views/s_internal_transfer.xml',
        'views/s_internal_transfer_line.xml',
        'views/stock_location.xml',
        'views/s_stock_delivery_type_sequence.xml',
        'views/s_stock_picking.xml',
        'views/s_stock_picking_package.xml',
        'views/package_report.xml',
        'views/s_report_internal_transfer.xml',
        'views/stock_quant_views.xml',
        'views/s_product_brand.xml',
        'views/dong_hang.xml',
        'views/s_product_material_views.xml',
        'views/s_product_season.xml',
        'views/s_product_species.xml',
        'views/s_product_collection.xml',
        'views/s_product_color.xml',
        'views/s_product_size.xml',
        'views/s_product_gender.xml',
        'views/s_stock_move_line.xml',
        'views/s_stock_picking_return.xml',
        'views/s_stock_scrap.xml',
        'views/s_stock_valuation_layer.xml',
        'views/s_stock_move.xml',
        'views/s_product_category.xml',
        'views/product_template_views.xml',
        'report/s_report_deliveryslip.xml',
        'report/s_report_stockpicking_operations.xml',
        'wizard/s_choice_stock_package.xml',
        'data/advanced_inventory_cron.xml',
        'data/sequence.xml',
        'wizard/s_location_inventory_report_view.xml',
        'wizard/s_report_internal_transfer_wizard.xml',
        'wizard/s_report_stock_quantity.xml',

    ],
    'assets': {
        'stock.assets': [
            'advanced_inventory/static/src/css/**/*',
        ],

    },
}
