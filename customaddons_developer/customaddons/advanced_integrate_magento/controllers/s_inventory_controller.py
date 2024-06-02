from odoo import http, SUPERUSER_ID
from odoo.http import request
from ..tools.api_wrapper import validate_integrate_token
from ..tools.common import invalid_response
from odoo.exceptions import ValidationError


class InventoryMagento(http.Controller):

    @validate_integrate_token
    @http.route('/inventory_mappings', methods=['GET'], auth='public', type='json', csrf=False)
    def get_inventory_mappings(self, *args, **kwargs):
        try:
            stock_warehouse = request.env['stock.warehouse'].sudo().search([('partner_id', '!=', False),
                                                                            ('status_stock_warehouse', '=', True)])
            channel_inventory_mappings = request.env['s.channel.inventory.mappings'].sudo()
            magento_sale_channel = request.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
            if not magento_sale_channel:
                return invalid_response(head='channel_not_supported', message='Magento2x Sale Channel is not defined!',
                                        status=500)
            res = []
            if stock_warehouse:
                for warehouse in stock_warehouse:
                    res.append({
                        'id': warehouse.id,
                        'name': warehouse.name,
                        'code': warehouse.code,
                        'address': warehouse.partner_id.read(['street', 'street2', 'ward_id', 'district_id', 'city_id',
                                                              'state_id', 'zip', 'country_id'])
                    })

                    channel_inventory_mappings.with_user(SUPERUSER_ID).create([{
                        'name': warehouse.name,
                        'code': warehouse.code,
                        'partner_id': warehouse.partner_id.id,
                        'channel_id': magento_sale_channel.id,
                    }])
            request.env['ir.logging'].sudo().create({
                'name': 'api-inventory-mappings-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(res),
                'func': 'api_call_inventory_mappings',
                'line': '0',
            })
            return res
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-inventory-mappings-magento',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'api_call_inventory_mappings',
                'line': '0',
            })
            return invalid_response(head='channel_not_supported', message='Magento2x Inventory Channel is not defined!',
                                    status=500)

    @validate_integrate_token
    @http.route('/check_product_available_quantity/<sku>', method=['GET'], auth='public', type='json', csrf=False)
    def check_product_available_quantity(self, sku, *args, **kwargs):
        try:
            product_id = request.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
            if product_id:
                data = []
                stock_quant_ids = product_id.stock_quant_ids.filtered(
                    lambda st: st.location_id.usage == 'internal' and st.location_id.s_is_transit_location == False and
                               st.location_id.scrap_location == False)
                if stock_quant_ids:
                    for stock_quant_id in stock_quant_ids:
                        if stock_quant_id.location_id:
                            if stock_quant_id.location_id.warehouse_id:
                                if stock_quant_id.location_id.warehouse_id.source_code_name:
                                    data.append({
                                        'source': stock_quant_id.location_id.warehouse_id.source_code_name,
                                        'available_quantity': stock_quant_id.available_quantity
                                    })
                request.env['ir.logging'].sudo().create({
                    'name': 'api-check-product-available-quantity',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'path': 'url',
                    'message': sku + ' - available_quantity = ' + str(data),
                    'func': 'api_check_product_available_quantity',
                    'line': '0',
                })
                return {
                    'sku': sku,
                    'data': data
                }
            else:
                raise ValidationError('Sản phẩm không tồn tại!')
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-check-product-available-quantity',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e),
                'func': 'api_check_product_available_quantity',
                'line': '0',
            })
            return invalid_response(head='magento_odoo_bridge_not_found', message=e.args, status=500)
