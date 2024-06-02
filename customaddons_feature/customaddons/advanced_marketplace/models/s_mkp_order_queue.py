import json
import ast
from datetime import date, timedelta, datetime
from odoo.exceptions import ValidationError, _logger
from odoo import fields, models, api
from odoo.tests import Form


class SMarketPlaceQueue(models.Model):
    _name = 's.mkp.order.queue'
    _rec_name = 's_mkp_order_id'

    s_mkp_payload = fields.Char('Payload')
    s_mkp_order_id = fields.Char(string='Order Id')
    s_is_mkp_tiktok = fields.Boolean(string='Là data Tiktok')
    s_is_mkp_shopee = fields.Boolean(string='Là data Shopee')
    s_is_mkp_lazada = fields.Boolean(string='Is Lazada order')
    s_mkp_order_type = fields.Selection(
        string='S_mkp_order_type',
        selection=[('create', 'Create'),
                   ('update', 'Update'), ])
    s_wh_code = fields.Char(string='Webhook code')

    def s_cronjob_create_data_queue(self):
        mkp_order_queue_ids = self.search([], limit=50)
        # check model order error xem co loi chua, co roi thi xoa
        if len(mkp_order_queue_ids) > 0:
            for rec in mkp_order_queue_ids:
                if rec.s_is_mkp_tiktok:
                    # check order error exist
                    tiktok_order_error_id = self.env['s.sale.order.error'].sudo().search(
                        [('tiktok_order_id', '=', rec.s_mkp_order_id)], limit=1)
                    if not tiktok_order_error_id:
                        payload = ast.literal_eval(rec.s_mkp_payload)
                        if payload:
                            tiktok_order_id = self.env['sale.order'].sudo().search(
                                [('tiktok_order_id', '=', rec.s_mkp_order_id), ('is_tiktok_order', '=', True)], limit=1)
                            if tiktok_order_id:
                                self.s_update_order_tiktok(tiktok_order_id, payload)
                            else:
                                if payload.get('type') == 1:
                                    self.s_create_order_tiktok(payload, rec.s_mkp_order_id)
                elif rec.s_is_mkp_shopee:
                    # check order error exist
                    shopee_order_error_id = self.env['s.sale.order.shopee.error'].sudo().search(
                        [('s_shopee_id_order', '=', rec.s_mkp_order_id)], limit=1)
                    if not shopee_order_error_id:
                        s_mkp_payload = ast.literal_eval(rec.s_mkp_payload)
                        if s_mkp_payload:
                            # check shopee order exist
                            shopee_order_id = self.env['sale.order'].sudo().search(
                                [('s_shopee_id_order', '=', rec.s_mkp_order_id), ('s_shopee_is_order', '=', True)],
                                limit=1)
                            if len(shopee_order_id) > 0:
                                s_mkp_payload = ast.literal_eval(rec.s_mkp_payload)
                                if s_mkp_payload.get('data'):
                                    self.s_update_order_shopee(shopee_order_id, rec.s_mkp_order_id,
                                                               s_mkp_payload.get('data'),
                                                               int(rec.s_wh_code))
                            else:
                                self.s_create_order_shopee(rec.s_mkp_order_id)
                elif rec.s_is_mkp_lazada:
                    data = ast.literal_eval(rec.s_mkp_payload)
                    lazada_order_id = self.env['sale.order'].sudo().search(
                            [('lazada_order_id', '=', rec.s_mkp_order_id)], limit=1)
                    if len(lazada_order_id) > 0:
                        self.env['sale.order'].sudo().build_order_lazada(lazada_order_id, data)
                    else:
                        self.env['sale.order'].sudo().sync_order_lazada(data)

                rec.unlink()

    def s_create_order_tiktok(self, pay_load, order_id):
        orders_detail = self.env['sale.order'].sudo().get_order_details(order_id)
        if orders_detail is not None:
            customer_tiktok = self.env.ref('advanced_integrate_tiktok.s_res_partner_tiktok')
            if orders_detail.get('order_list') and pay_load.get('data'):
                body = self._grooming_sale_order_data_tiktok(pay_load, orders_detail, customer_tiktok)
                get_shipping = {}
                if body is not None:
                    # if body.get('get_shipping'):
                    #     get_shipping = body.get('get_shipping')
                    #     body.pop('get_shipping')
                    created_order = self.env['sale.order'].sudo().create(body)
                    ###Bỏ line phí ship đơn marketplace
                    # if len(get_shipping):
                    #     shipping_price = orders_detail.get('order_list')[0].get('payment_info').get(
                    #         'shipping_fee')
                    #     is_delivery_line = created_order._create_delivery_line(
                    #         get_shipping.get('carrier_id'),
                    #         shipping_price)
                    #     if is_delivery_line:
                    #         is_delivery_line.sudo().write({
                    #             'price_unit': shipping_price
                    #         })
                    ###confirm SO
                    created_order.sudo().action_confirm()

                    ###mapping package_status and package_tiktok_id
                    if len(orders_detail.get('order_list')) > 0:
                        if orders_detail.get('order_list')[0].get('package_list'):
                            self.env['stock.picking'].sudo().s_get_package_id_tiktok(orders_detail, created_order)
                    ###Sau khi order confirm mới cho write date_order
                    if body.get('date_order'):
                        created_order.sudo().write({
                            'date_order': body.get('date_order')
                        })
                    if (created_order.marketplace_tiktok_order_status in ['121', '112', '122', '130']
                            and created_order.picking_ids and created_order.picking_ids.state not in (
                                    'done', 'cancel')):
                        if created_order.picking_ids.state == 'confirmed':
                            created_order.picking_ids.action_assign()
                        created_order.picking_ids.action_set_quantities_to_reservation()
                        created_order.picking_ids.button_validate()
                    elif created_order.marketplace_tiktok_order_status == '140':
                        picking_sale = created_order.picking_ids.filtered(
                            lambda r: r.transfer_type == 'out' and r.location_id.usage == 'internal')
                        if picking_sale and picking_sale.state in ('assigned', 'confirmed'):
                            created_order.picking_ids.action_cancel()
                            created_order.action_cancel()
                    if not created_order.completed_date and body.get('completed_date'):
                        created_order.sudo().write({
                            'completed_date': body.get('completed_date')
                        })

            else:
                self.env['s.sale.order.error'].sudo().create({
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'message': "order_list không có trong orders_detail or data không có trong pay_load" + "\t" + "orders_detail: %s \n payload: %s" % (
                        str(orders_detail), str(pay_load)),
                    'tiktok_order_id': pay_load['data']['order_id'],
                    'order_status': pay_load['data']['order_status'],
                })
        else:
            self.env['s.sale.order.error'].sudo().create({
                'dbname': 'boo',
                'level': 'ERROR',
                'message': 'Order details is None',
                'tiktok_order_id': pay_load['data']['order_id'],
                'order_status': pay_load['data']['order_status'],
            })

    def _grooming_sale_order_data_tiktok(self, pay_load, orders_detail, customer_tiktok):
        created_error = False
        for rec in orders_detail.get('order_list'):
            # original_total_product_price = orders_detail.get('order_list')[0].get('payment_info').get(
            #     'original_total_product_price')
            # sub_total = orders_detail.get('order_list')[0].get('payment_info').get('sub_total')
            # discount_price = 0
            query_warehouse = self._cr.execute(
                """SELECT id FROM stock_warehouse WHERE s_warehouse_tiktok_id IS NOT NULL AND s_warehouse_tiktok_id = %s AND is_mapping_warehouse=TRUE limit 1""",
                (rec['warehouse_id'],))
            result_query_warehouse = [item[0] for item in self._cr.fetchall()]
            address_detail = None
            address_line_list = None
            city = None
            district = None
            full_address = None
            name = None
            phone = None
            region = None
            state = None
            town = None
            if rec.get('recipient_address'):
                if rec.get('recipient_address').get('address_detail'):
                    address_detail = rec.get('recipient_address').get('address_detail')
                if rec.get('recipient_address').get('address_line_list'):
                    address_line_list = rec.get('recipient_address').get('address_line_list')
                if rec.get('recipient_address').get('city'):
                    city = rec.get('recipient_address').get('city')
                if rec.get('recipient_address').get('district'):
                    district = rec.get('recipient_address').get('district')
                if rec.get('recipient_address').get('full_address'):
                    full_address = rec.get('recipient_address').get('full_address')
                if rec.get('recipient_address').get('name'):
                    name = rec.get('recipient_address').get('name')
                if rec.get('recipient_address').get('phone'):
                    phone = rec.get('recipient_address').get('phone')
                if rec.get('recipient_address').get('region'):
                    region = rec.get('recipient_address').get('region')
                if rec.get('recipient_address').get('state'):
                    state = rec.get('recipient_address').get('state')
                if rec.get('recipient_address').get('town'):
                    town = rec.get('recipient_address').get('town')
            if len(result_query_warehouse) > 0:
                note = "Thông tin khách hàng:\naddress_detail: %s\naddress_line_list: %s\ncity: %s\ndistrict: %s\nfull_address : %s\nname : %s\nphone: %s\nregion : %s\nstate: %s\ntown : %s" % (
                    address_detail, address_line_list,
                    city, district,
                    full_address, name,phone, region,state, town)

                product_orders = []
                order = dict()
                list_seller_sku = []
                for line in rec.get('order_line_list'):
                    list_product = []
                    product_uom_qty = len([i for i in rec.get('order_line_list') if i.get('seller_sku') == line.get('seller_sku')])
                    if "," in line.get('seller_sku'):
                        seller_sku = line.get('seller_sku').split(',')
                        for r in seller_sku:
                            if r not in list_seller_sku:
                                product_product = self.env['product.product'].sudo().search(
                                    [('marketplace_sku', '=', line.get('seller_sku')),
                                     ('default_code', '=', (r.encode('ascii', 'ignore')).decode("utf-8")),
                                     ('to_sync_tiktok', '=', True)])
                                if product_product:
                                    stock_quant = product_product.stock_quant_ids.filtered(
                                        lambda r: r.location_id.warehouse_id.id == result_query_warehouse[
                                            0] and r.available_quantity > 0 and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id)
                                    stock_available = stock_quant.available_quantity
                                    if stock_available and stock_available > 0:
                                        if stock_available >= product_uom_qty and len(list_product) == 0:
                                            product = {
                                                'product_id': product_product.id,
                                                'name': product_product.name,
                                                'stock_available': product_uom_qty,
                                                'uom_id': product_product.uom_id.id
                                            }
                                            list_seller_sku.append(r)
                                            list_product.append(product)
                                            product_uom_qty = 0
                                            break
                                        elif (stock_available < product_uom_qty) or len(list_product):
                                            if product_uom_qty > 0:
                                                if stock_available < product_uom_qty:
                                                    product = {
                                                        'product_id': product_product.id,
                                                        'name': product_product.name,
                                                        'stock_available': stock_available,
                                                        'uom_id': product_product.uom_id.id
                                                    }
                                                    list_seller_sku.append(r)
                                                    product_uom_qty -= stock_available
                                                    list_product.append(product)
                                                else:
                                                    product = {
                                                        'product_id': product_product.id,
                                                        'name': product_product.name,
                                                        'stock_available': product_uom_qty,
                                                        'uom_id': product_product.uom_id.id
                                                    }
                                                    list_seller_sku.append(r)
                                                    product_uom_qty = 0
                                                    list_product.append(product)
                                            else:
                                                break
                            else:
                                product_uom_qty = 0
                        if product_uom_qty > 0:
                            created_error = True
                            self.env['s.sale.order.error'].sudo().create({
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'message': "product: %s [%s] không đủ tồn" % (
                                    line.get('product_name'), line.get('seller_sku')),
                                'tiktok_order_id': pay_load['data']['order_id']
                            })
                            break
                    else:
                        product_product = self.env['product.product'].sudo().search(
                            [('default_code', '=', line.get('seller_sku')), ('to_sync_tiktok', '=', True)])
                        if product_product:
                            stock_available = product_product.stock_quant_ids.filtered(
                                lambda r: r.location_id.warehouse_id.id == result_query_warehouse[
                                    0] and r.available_quantity > 0 and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).available_quantity
                            if stock_available and stock_available >= product_uom_qty:
                                product = {
                                    'product_id': product_product.id,
                                    'name': product_product.name,
                                    'stock_available': product_uom_qty,
                                    'uom_id': product_product.uom_id.id
                                }
                                if line.get('seller_sku') not in list_seller_sku:
                                    list_seller_sku.append(line.get('seller_sku'))
                                    list_product.append(product)
                            else:
                                created_error = True
                                self.env['s.sale.order.error'].sudo().create({
                                    'dbname': 'boo',
                                    'level': 'ERROR',
                                    'message': "product: %s [%s] không đủ tồn" % (line.get('product_name'), line.get('seller_sku')),
                                    'tiktok_order_id': pay_load['data']['order_id']
                                })
                        else:
                            created_error = True
                            self.env['s.sale.order.error'].sudo().create({
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'message': "Không có sản phẩm nào khớp với Tiktok trên odoo",
                                'tiktok_order_id': pay_load['data']['order_id']
                            })
                    if list_product:
                        ###Kiểm tra price_unit xem sản phẩm có được chiết khấu không
                        if not line.get('seller_discount'):
                            s_price_unit = line.get('original_price')
                        else:
                            s_price_unit = line.get('original_price') - line.get('seller_discount')
                        for record in list_product:
                            product_orders.append(
                                {
                                    "product_id": record.get('product_id'),
                                    "name": record.get('name'),
                                    "product_uom": record.get('uom_id'),
                                    "product_uom_qty": record.get('stock_available'),
                                    "price_unit": s_price_unit,
                                    "s_lst_price": line.get('original_price'),
                                })

                if len(product_orders) > 0 and len(product_orders) >= len(list_seller_sku) and not created_error:
                    source_id = self.env.ref('advanced_integrate_tiktok.utm_source_tiktok')
                    order['partner_id'] = customer_tiktok.id
                    order['partner_invoice_id'] = customer_tiktok.id
                    order['partner_shipping_id'] = customer_tiktok.id
                    order['tiktok_order_id'] = rec['order_id']
                    order['note'] = note
                    order['is_tiktok_order'] = True
                    order['marketplace_tiktok_order_status'] = str(rec['order_status'])
                    order['warehouse_id'] = result_query_warehouse[0]
                    order['currency_id'] = self.env.company.currency_id.id
                    order['source_id'] = source_id.id
                    order['payment_method'] = "cod" if rec.get('is_cod') else "online"
                    ####update ngày đặt hàng (create_time)
                    if rec.get('create_time'):
                        if len(str(rec.get('create_time'))) == 13:
                            order['date_order'] = datetime.fromtimestamp(int(rec.get('create_time')) / 1000)
                        else:
                            order['date_order'] = datetime.fromtimestamp(int(rec.get('create_time')))
                    order_lines = []
                    if str(rec['order_status']) in ('122', '130', '140') and rec.get('update_time'):
                        order['completed_date'] = datetime.fromtimestamp(int(rec.get('update_time')))
                    for product_order in product_orders:
                        order_lines.append((0, 0, {
                            'product_id': product_order['product_id'],
                            'name': product_order['name'],
                            'product_uom_qty': product_order['product_uom_qty'],
                            'product_uom': product_order['product_uom'],
                            'price_unit': product_order['price_unit'],
                            's_lst_price': product_order['s_lst_price'],
                            'is_product_reward': False
                        }))
                    ###Bỏ line chiết khấu đơn marketplace
                    ##Check chiết khấu của sàn tiktok
                    # if rec.get('payment_info').get('platform_discount') is not None:
                    #     discount_price = int(rec.get('payment_info').get('platform_discount'))
                    #     if discount_price > 0:
                    #         is_discount_line = self.env['sale.order'].sudo()._get_line_discount_tiktok(discount_price)
                    #         if is_discount_line:
                    #             order_lines.append((0, 0, is_discount_line))
                    if len(order_lines) > 0:
                        order['order_line'] = order_lines
                    ###Bỏ line phí ship sàn marketplace
                    # if 'shipping_provider' in orders_detail.get('order_list')[0]:
                    #     shipping_provider = orders_detail.get('order_list')[0]['shipping_provider']
                    #     shipping_price = orders_detail.get('order_list')[0]['payment_info']['shipping_fee']
                    #     get_shipping = self.env['s.sale.order.error'].sudo()._get_shipping_method_tiktok(
                    #         shipping_provider, shipping_price)
                    #     if get_shipping:
                    #         order['get_shipping'] = get_shipping
                            # is_delivery_line = order._create_delivery_line(get_shipping['carrier_id'], shipping_price)
                            # if is_delivery_line:
                            #     is_delivery_line.sudo().write({
                            #         'price_unit': shipping_price
                            #     })
                    return order
            else:
                self.env['s.sale.order.error'].sudo().create({
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'message': "Chưa có kho tương thích với tiktok",
                    'tiktok_order_id': pay_load['data']['order_id']
                })

    def s_create_order_shopee(self, ordersn):
        created_error = False
        api_detail = self.env['sale.order'].sudo().get_order_details_shopee(ordersn)
        api_detail_json = api_detail.json()
        if api_detail.status_code == 200:
            if not api_detail_json.get('error'):
                self.env['ir.logging'].sudo().create({
                    'name': '#Shopee: get_webhook_order_shopee',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'Order_Detail',
                    'path': 'url',
                    'message': str(api_detail_json),
                    'func': 'get_webhook_order_shopee',
                    'line': '0',
                })
                customer_shopee = self.env.ref('advanced_integrate_shopee.s_res_partner_shopee')
                create_order = dict()
                order_income = {}
                if api_detail_json.get('response'):
                    orders_detail = api_detail_json.get('response')
                    if orders_detail.get('order_list'):
                        for rec in orders_detail['order_list']:
                            price_total_items = 0
                            shipping_price = 0
                            phi_bao_hiem = 0
                            try:
                                note = "Thông tin khách hàng:\nname: %s\nphone: %s\ntown: %s\ndistrict: %s\ncity : %s\nstate : %s\nregion: %s\nzipcode : %s\nfull_address: %s" % (
                                    rec['recipient_address']['name'], rec['recipient_address']['phone'],
                                    rec['recipient_address']['town'], rec['recipient_address']['district'],
                                    rec['recipient_address']['city'], rec['recipient_address']['state'],
                                    rec['recipient_address']['region'], rec['recipient_address']['zipcode'],
                                    rec['recipient_address']['full_address'])
                                product_orders = []
                                shipping = self.env['sale.order'].sudo().get_escrow_detail(ordersn)
                                shipping_json = shipping.json()
                                if shipping.status_code == 200:
                                    if shipping_json.get('response'):
                                        response = shipping_json.get('response')
                                        if response.get('order_income'):
                                            order_income = response.get('order_income')
                                            if order_income.get('items'):
                                                for rec_product in order_income.get('items'):
                                                    list_product, search_product = [], []
                                                    product_uom_qty = rec_product.get('quantity_purchased')
                                                    model_sku = rec_product.get('model_sku') if rec_product.get(
                                                        'model_sku') is not None else ""
                                                    item_sku = rec_product.get('item_sku') if rec_product.get(
                                                        'item_sku') is not None else ""
                                                    if "," in model_sku or "," in item_sku:
                                                        if model_sku != "":
                                                            seller_sku = model_sku.split(',')
                                                        elif item_sku != "":
                                                            seller_sku = item_sku.split(',')
                                                        for r in seller_sku:
                                                            search_product_product = self.env[
                                                                'product.product'].sudo().search(
                                                                ['|', '&', '&', ('s_shopee_to_sync', '=', True),
                                                                 ('default_code', '=', (r.encode('ascii', 'ignore')).decode("utf-8")),
                                                                 ('marketplace_sku', '=', model_sku), '&', ('s_shopee_to_sync', '=', True),
                                                                 ('marketplace_sku', '=', item_sku)])

                                                            if search_product_product:
                                                                search_product.append(search_product_product.id)
                                                                stock_available = search_product_product.stock_quant_ids.filtered(lambda
                                                                                                                                      r: r.location_id.warehouse_id and r.quantity > 0 and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True
                                                                                                                                         and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).available_quantity
                                                                if stock_available and stock_available > 0:
                                                                    if stock_available >= product_uom_qty and len(
                                                                            list_product) == 0:
                                                                        product = {
                                                                            'product_id': search_product_product.id,
                                                                            'stock_available': product_uom_qty,
                                                                        }
                                                                        list_product.append(product)
                                                                        product_uom_qty = 0
                                                                        break
                                                                    elif (stock_available < product_uom_qty) or len(
                                                                            list_product):
                                                                        if product_uom_qty > 0:
                                                                            if stock_available < product_uom_qty:
                                                                                product = {
                                                                                    'product_id': search_product_product.id,
                                                                                    'stock_available': stock_available
                                                                                }
                                                                                product_uom_qty -= stock_available
                                                                                list_product.append(product)
                                                                            else:
                                                                                product = {
                                                                                    'product_id': search_product_product.id,
                                                                                    'stock_available': product_uom_qty
                                                                                }
                                                                                product_uom_qty = 0
                                                                                list_product.append(product)
                                                                        else:
                                                                            break
                                                        if product_uom_qty != 0:
                                                            created_error = True
                                                            if len(search_product) > 0:
                                                                self.env['s.sale.order.shopee.error'].sudo().create({
                                                                    'dbname': 'boo',
                                                                    'level': 'ERROR',
                                                                    'message': "product: %s không đủ tồn" % rec_product.get(
                                                                        'item_name'),
                                                                    's_shopee_id_order': ordersn
                                                                })
                                                            else:
                                                                self.env['s.sale.order.shopee.error'].sudo().create({
                                                                    'dbname': 'boo',
                                                                    'level': 'ERROR',
                                                                    'message': "product: %s Không có trên odoo" % rec_product.get(
                                                                        'item_name'),
                                                                    's_shopee_id_order': ordersn
                                                                })
                                                    else:
                                                        search_product_product = self.env['product.product'].sudo().search(
                                                            [('default_code', '=', model_sku),
                                                             ('s_shopee_to_sync', '=', True)]) if model_sku != "" else self.env[
                                                            'product.product'].sudo().search(
                                                            [('default_code', '=', item_sku), ('s_shopee_to_sync', '=', True)])
                                                        if search_product_product:
                                                            stock_available = search_product_product.stock_quant_ids.filtered(lambda
                                                                                                                                  r: r.location_id.warehouse_id and r.quantity > 0 and r.location_id.warehouse_id.s_shopee_is_mapping_warehouse == True and r.location_id.warehouse_id.lot_stock_id.id == r.location_id.id).available_quantity
                                                            if stock_available and stock_available >= product_uom_qty:
                                                                product = {
                                                                    'product_id': search_product_product.id,
                                                                    'stock_available': product_uom_qty,
                                                                }
                                                                list_product.append(product)
                                                            else:
                                                                created_error = True
                                                                self.env['s.sale.order.shopee.error'].sudo().create({
                                                                    'dbname': 'boo',
                                                                    'level': 'ERROR',
                                                                    'message': "product: %s không đủ tồn" % search_product_product.name,
                                                                    's_shopee_id_order': ordersn
                                                                })
                                                        else:
                                                            created_error = True
                                                            self.env['s.sale.order.shopee.error'].sudo().create({
                                                                'dbname': 'boo',
                                                                'level': 'ERROR',
                                                                'message': "product: %s Không có trên odoo" % rec_product.get('item_name'),
                                                                's_shopee_id_order': ordersn
                                                            })
                                                    # if id_product:
                                                    #     product_orders.append(
                                                    #         {
                                                    #             "product_id": id_product,
                                                    #             "product_uom_qty": rec_product.get('quantity_purchased'),
                                                    #             "price_unit": (rec_product.get('discounted_price') if rec_product.get('discounted_price') else rec_product.get('original_price')) / rec_product.get('quantity_purchased')
                                                    #         })
                                                    if list_product:
                                                        for record in list_product:
                                                            product_orders.append(
                                                                {
                                                                    "product_id": record.get('product_id'),
                                                                    "product_uom_qty": record.get('stock_available'),
                                                                    "price_unit": (rec_product.get('discounted_price') if rec_product.get('discounted_price') else rec_product.get('original_price')) / rec_product.get('quantity_purchased')
                                                                })
                                            else:
                                                self.env['ir.logging'].sudo().create({
                                                    'name': '#Shopee: get_webhook_order_shopee',
                                                    'type': 'server',
                                                    'dbname': 'boo',
                                                    'level': 'ERROR',
                                                    'path': 'url',
                                                    'message': "items không nằm trong order_income, shipping_json: %s" % str(shipping_json),
                                                    'func': 'get_webhook_order_shopee',
                                                    'line': '0',
                                                })
                                                self.env['s.sale.order.shopee.error'].sudo().create({
                                                    'dbname': 'boo',
                                                    'level': 'ERROR',
                                                    'message': "Không lấy được payment của đơn hàng",
                                                    's_shopee_id_order': ordersn
                                                })
                                        else:
                                            self.env['ir.logging'].sudo().create({
                                                'name': '#Shopee: get_webhook_order_shopee',
                                                'type': 'server',
                                                'dbname': 'boo',
                                                'level': 'ERROR',
                                                'path': 'url',
                                                'message': "order_income không nằm trong response, shipping_json: %s" % str(shipping_json),
                                                'func': 'get_webhook_order_shopee',
                                                'line': '0',
                                            })
                                            self.env['s.sale.order.shopee.error'].sudo().create({
                                                'dbname': 'boo',
                                                'level': 'ERROR',
                                                'message': "Không lấy được payment của đơn hàng",
                                                's_shopee_id_order': ordersn
                                            })
                                    else:
                                        self.env['ir.logging'].sudo().create({
                                            'name': '#Shopee: get_webhook_order_shopee',
                                            'type': 'server',
                                            'dbname': 'boo',
                                            'level': 'ERROR',
                                            'path': 'url',
                                            'message': "response không nằm trong shipping_json, shipping_json: %s" % str(shipping_json),
                                            'func': 'get_webhook_order_shopee',
                                            'line': '0',
                                        })
                                        self.env['s.sale.order.shopee.error'].sudo().create({
                                            'dbname': 'boo',
                                            'level': 'ERROR',
                                            'message': "Không lấy được payment của đơn hàng",
                                            's_shopee_id_order': ordersn
                                        })
                                else:
                                    self.env['ir.config_parameter'].sudo().set_param(
                                        'advanced_integrate_shopee.is_error_token_shopee', 'True')
                                    vals = {
                                        'dbname': 'boo',
                                        'level': 'ERROR',
                                        'message': shipping_json.get('message'),
                                        's_shopee_id_order': ordersn
                                    }
                                    if shipping_json.get('error'):
                                        if 'error_auth' in shipping_json.get('error'):
                                            vals.update({
                                                's_error_token_shopee': True
                                            })
                                    self.env['s.sale.order.shopee.error'].sudo().create(vals)
                                if len(product_orders) > 0 and len(product_orders) >= len(
                                        rec['item_list']) and not created_error:
                                    source_id = self.env.ref('advanced_integrate_shopee.utm_source_shopee')
                                    create_order['partner_id'] = customer_shopee.id
                                    create_order['partner_invoice_id'] = customer_shopee.id
                                    create_order['partner_shipping_id'] = customer_shopee.id
                                    create_order['s_shopee_id_order'] = rec['order_sn']
                                    create_order['note'] = note
                                    create_order['s_shopee_is_order'] = True
                                    create_order['marketplace_shopee_order_status'] = rec['order_status']
                                    create_order['warehouse_id'] = self.env['stock.warehouse'].sudo().search(
                                        [('s_shopee_is_mapping_warehouse', '=', True)]).id
                                    create_order['currency_id'] = self.env.company.currency_id.id
                                    create_order['source_id'] = source_id.id
                                    create_order['payment_method'] = "cod" if rec.get('cod') else "online"
                                    carrier_id = False
                                    ####update ngày đặt hàng (create_time)
                                    if rec.get('create_time'):
                                        if len(str(rec.get('create_time'))) == 13:
                                            create_order['date_order'] = datetime.fromtimestamp(
                                                int(rec.get('create_time')) / 1000)
                                        else:
                                            create_order['date_order'] = datetime.fromtimestamp(
                                                int(rec.get('create_time')))
                                    order_lines = []
                                    if str(rec['order_status']) in (
                                            'TO_CONFIRM_RECEIVE', 'COMPLETED', 'CANCELLED', 'TO_RETURN'):
                                        create_order['completed_date'] = datetime.fromtimestamp(
                                            int(rec.get('update_time')))
                                    for product_order in product_orders:
                                        order_lines.append((0, 0, {
                                            'product_id': product_order['product_id'],
                                            'product_uom_qty': product_order['product_uom_qty'],
                                            'price_unit': product_order['price_unit'],
                                            'is_product_reward': False
                                        }))

                                    # shipping = self.env['sale.order'].sudo().get_escrow_detail(ordersn)
                                    # shipping_json = shipping.json()
                                    # if shipping.status_code == 200:
                                    #     if shipping_json.get('response'):
                                    #         response = shipping_json.get('response')
                                    #         if response.get('order_income'):
                                    #             order_income = response.get('order_income')
                                    #             if order_income.get('buyer_paid_shipping_fee'):
                                    #                 shipping_price = abs(order_income.get('buyer_paid_shipping_fee'))
                                    #                 phi_bao_hiem = abs(order_income.get(
                                    #                     'final_product_protection')) if order_income.get(
                                    #                     'final_product_protection') else 0

                                    # line phi bao hiem shopee
                                    # if phi_bao_hiem:
                                    #     phi_bao_hiem_id, param_phi_bao_hiem = self.env['sale.order'].sudo()._get_shipping_method_shopee("phi bao hiem", phi_bao_hiem)
                                    #     if param_phi_bao_hiem:
                                    #         order_lines.append((0, 0, param_phi_bao_hiem))

                                    # Line discount Shopee
                                    discount_price = order_income.get('voucher_from_seller') if order_income.get('voucher_from_seller') >= sum([res.get('discount_from_voucher_seller') for res in order_income.get('items')]) else sum([res.get('discount_from_voucher_seller') for res in order_income.get('items')])
                                    if discount_price > 0:
                                        get_promotion = self.env['sale.order'].sudo()._get_line_discount_shopee(
                                            discount_price)
                                        if get_promotion:
                                            order_lines.append((0, 0, get_promotion))


                                    # # Line phí vận chuyển Shopee
                                    # if rec.get('package_list') and len(rec.get('package_list')) > 0:
                                    #     if rec.get('package_list')[0].get('shipping_carrier'):
                                    #         shipping_carrier = rec.get('package_list')[0].get('shipping_carrier')
                                    #         if shipping_carrier and shipping_price and shipping_price > 0:
                                    #             carrier_id, order_line_delivery = self.env[
                                    #                 'sale.order'].sudo()._get_shipping_method_shopee(
                                    #                 shipping_carrier, shipping_price)
                                    #             if order_line_delivery:
                                    #                 order_lines.append((0, 0, order_line_delivery))
                                    if len(order_lines) > 0:
                                        create_order['order_line'] = order_lines
                                    if carrier_id:
                                        create_order['s_carrier_id'] = carrier_id
                                    order = self.env['sale.order'].sudo().create(create_order)
                                    if order:
                                        order.sudo().action_confirm()
                                        ###Sau khi order confirm mới cho write date_order
                                        if create_order.get('date_order'):
                                            order.sudo().write({
                                                'date_order': create_order.get('date_order')
                                            })
                                        if rec.get('package_list') and len(rec.get('package_list')) > 0:
                                            shopee_package_list = rec.get('package_list')[0]
                                            if order.picking_ids:
                                                order.picking_ids[0].sudo().write({
                                                    's_shopee_package_number': shopee_package_list.get('package_number')
                                                })
                                        # update order status
                                        if order.marketplace_shopee_order_status in (
                                                "PROCESSED", "RETRY_SHIP", "SHIPPED", "TO_CONFIRM_RECEIVE", "TO_RETURN",
                                                "COMPLETED"):
                                            picking_ids = order.picking_ids.filtered(
                                                lambda p: p.state not in ('done', 'cancel'))
                                            if len(order.picking_ids) > 0 and len(picking_ids) > 0:
                                                for picking in picking_ids:
                                                    if picking.state == 'confirmed':
                                                        picking.action_assign()
                                                    if picking.state == 'assigned':
                                                        picking.action_set_quantities_to_reservation()
                                                        picking.button_validate()
                                        elif order.marketplace_shopee_order_status == "CANCELLED":
                                            for picking in order.picking_ids:
                                                if picking:
                                                    picking.action_cancel()
                                            order.action_cancel()
                                        if create_order.get('completed_date') and not order.completed_date:
                                            order.sudo().write({
                                                'completed_date': create_order['completed_date']
                                            })
                            except Exception as e:
                                self.env['s.sale.order.shopee.error'].sudo().create({
                                    'dbname': 'boo',
                                    'level': 'ERROR',
                                    'message': str(e),
                                    's_shopee_id_order': ordersn
                                })
                    else:
                        self.env['ir.logging'].sudo().create({
                            'name': '#Shopee: get_webhook_order_shopee',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'path': 'url',
                            'message': "order_list not in orders_detail, orders_detail: %s" % str(orders_detail),
                            'func': 'get_webhook_order_shopee',
                            'line': '0',
                        })
            else:
                self.env['s.sale.order.shopee.error'].sudo().create({
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'message': api_detail_json.get('message'),
                    's_shopee_id_order': ordersn
                })
        else:
            self.env['ir.config_parameter'].sudo().set_param(
                'advanced_integrate_shopee.is_error_token_shopee', 'True')
            vals = {
                'dbname': 'boo',
                'level': 'ERROR',
                'message': api_detail_json.get('message'),
                's_shopee_id_order': ordersn
            }
            if api_detail_json.get('error'):
                if 'error_auth' in api_detail_json.get('error'):
                    vals.update({
                        's_error_token_shopee': True
                    })
            self.env['s.sale.order.shopee.error'].sudo().create(vals)

    def s_update_order_shopee(self, sale_order, ordersn, data, code):
        # code=3 update order status
        if code == 3:
            try:
                if data.get('status'):
                    order_status = self.env['sale.order'].sudo().check_order_status(data, sale_order)
                    if sale_order.sudo().marketplace_shopee_order_status == 'TO_RETURN' and order_status == 'COMPLETED':
                        if not sale_order.sudo().return_order_ids:
                            if sale_order.sudo().s_shopee_time_return:
                                time_return = sale_order.sudo().s_shopee_time_return
                                list_return = self.env['sale.order'].sudo()._get_return_list_shopee(update_time=time_return)
                                list_return_json = list_return.json()
                                if list_return.status_code == 200:
                                    if not list_return_json.get('error'):
                                        if list_return_json.get('response'):
                                            list_order_return = list_return_json.get('response')
                                            if len(list_order_return.get('return')) > 0:
                                                for order_return in list_order_return.get('return'):
                                                    if order_return.get('order_sn') == ordersn:
                                                        status_return = order_return.get('status')
                                                        if status_return in ['PROCESSING', 'CLOSED', 'CANCELLED',
                                                                             'ACCEPTED', 'REFUND_PAID']:
                                                            self.env[
                                                                'sale.order'].sudo()._create_so_return_shopee(
                                                                ordersn, order_return)
                    if order_status:
                        sale_order.sudo().marketplace_shopee_order_status = order_status
                    if sale_order.sudo().marketplace_shopee_order_status in ['TO_CONFIRM_RECEIVE',
                                                                             'CANCELLED',
                                                                             'COMPLETED',
                                                                             'TO_RETURN']:
                        ###Update completed_date
                        if not sale_order.completed_date:
                            sale_order.completed_date = datetime.fromtimestamp(
                                data['update_time'])
                    if sale_order.sudo().marketplace_shopee_order_status == 'TO_RETURN':
                        sale_order.sudo().s_shopee_time_return = data.get('update_time')
                        list_return = self.env['sale.order'].sudo()._get_return_list_shopee(
                            update_time=data.get('update_time'))
                        list_return_json = list_return.json()
                        if list_return.status_code == 200:
                            if not list_return_json.get('error'):
                                if list_return_json.get('response'):
                                    list_order_return = list_return_json.get('response')
                                    if len(list_order_return.get('return')) > 0:
                                        for order_return in list_order_return.get('return'):
                                            if order_return.get('order_sn') == ordersn:
                                                status_return = order_return.get('status')
                                                if status_return in ['PROCESSING', 'CLOSED', 'CANCELLED',
                                                                     'ACCEPTED', 'REFUND_PAID']:
                                                    self.env[
                                                        'sale.order'].sudo()._create_so_return_shopee(
                                                        ordersn, order_return)
                            else:
                                self.env['s.sale.order.shopee.error'].sudo().create({
                                    'dbname': 'boo',
                                    'level': 'STATUS_ERROR',
                                    'message': list_return_json.get('message'),
                                    's_shopee_id_order': ordersn,
                                    'payload': str(data),
                                    'order_status': data['status']
                                })
                        else:
                            self.env['s.sale.order.shopee.error'].sudo().create({
                                'dbname': 'boo',
                                'level': 'STATUS_ERROR',
                                'message': list_return_json.get('message'),
                                's_shopee_id_order': ordersn,
                                'payload': str(data),
                                'order_status': data['status']
                            })
                    if sale_order.marketplace_shopee_order_status in (
                            "PROCESSED", "RETRY_SHIP", "SHIPPED", "TO_CONFIRM_RECEIVE", "COMPLETED", "TO_RETURN"):
                        picking_ids = sale_order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                        if len(sale_order.picking_ids) > 0 and len(picking_ids) > 0:
                            for picking in picking_ids:
                                if picking.state in ["confirmed"]:
                                    picking.action_assign()
                                if picking.state == 'assigned':
                                    picking.action_set_quantities_to_reservation()
                                    picking.button_validate()

                    status_logistics_shopee = sale_order.picking_ids.filtered(
                        lambda r: r.transfer_type == 'out').s_shopee_logistics_status
                    # Fake status shipment để test
                    if data.get('test_shipment_status') is not None:
                        status_logistics_shopee = data.get(
                            'test_shipment_status').get(
                            'logistics_status')
                    else:
                        # Lưu trạng thái DO Shopee
                        logistics_status = self.env['stock.picking'].sudo()._get_tracking_info(ordersn)
                        if logistics_status is not None:
                            if status_logistics_shopee != logistics_status.get(
                                    'logistics_status'):
                                status_logistics_shopee = logistics_status.get(
                                    'logistics_status')
                    if sale_order.marketplace_shopee_order_status == "CANCELLED":
                        picking_done_ids = sale_order.picking_ids.filtered(
                            lambda p: p.state in ['done'] and p.transfer_type == 'out')
                        if picking_done_ids:
                            for picking_done_id in picking_done_ids:
                                return_picking_old_id = sale_order.picking_ids.filtered(
                                    lambda p: picking_done_id.name in p.origin)
                                if return_picking_old_id:
                                    break
                                # Tao lenh return DO
                                return_picking_id = self.env['stock.return.picking'].create(
                                    {'picking_id': picking_done_id.id})
                                # Them san pham vao return DO
                                return_picking_id.sudo()._onchange_picking_id()
                                # tao phieu return DO
                                if len(return_picking_id.product_return_moves) > 0:
                                    result_return_picking = return_picking_id.sudo().create_returns()
                                    if result_return_picking:
                                        picking_return = sale_order.picking_ids.filtered(
                                            lambda r: r.id == result_return_picking.get(
                                                'res_id'))
                                        if picking_return.state == 'assigned':
                                            picking_return.action_set_quantities_to_reservation()
                                            # picking_return.button_validate()
                                        boo_do_return = self.env['stock.picking'].search(
                                            [('id', '=', result_return_picking.get('res_id'))])
                                        if boo_do_return and not boo_do_return.is_boo_do_return:
                                            boo_do_return.write({'is_boo_do_return': True})
                        else:
                            picking_not_done_ids = sale_order.picking_ids.filtered(
                                lambda p: p.state not in ['done',
                                                          'cancel'] and p.transfer_type == 'out')
                            if picking_not_done_ids:
                                for picking_not_done_id in picking_not_done_ids:
                                    picking_not_done_id.action_cancel()
                            sale_order.sudo().with_context(api_cancel_do=True)._action_cancel()
                        sale_order.sudo().write({
                            'sale_order_status': 'huy'
                        })
                    self.env['ir.logging'].sudo().create({
                        'name': '#Shopee: get_webhook_order_shopee',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': '3',
                        'path': 'url',
                        'message': str(data),
                        'func': 'get_webhook_order_shopee',
                        'line': '0',
                    })
                else:
                    self.env['s.sale.order.shopee.error'].sudo().create({
                        'dbname': 'boo',
                        'level': 'STATUS_ERROR',
                        'message': "status not in payload, payload: %s" % str(data),
                        's_shopee_id_order': ordersn,
                        'payload': str(data),
                        'order_status': data['status']
                    })
                # else:
                #     self.env['s.sale.order.shopee.error'].sudo().create({
                #         'dbname': 'boo',
                #         'level': 'STATUS_ERROR',
                #         'message': "data not in payload, payload: %s" % str(pay_load),
                #         's_shopee_id_order': ordersn,
                #         'payload': pay_load,
                #         'order_status': data['status']
                #     })
            except Exception as e:
                self.env['ir.logging'].sudo().create({
                    'name': '#Shopee: s_update_order_shopee',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'STATUS ERROR',
                    'path': 'url',
                    'message': str(e) + "\t" + str(data),
                    'func': 's_update_order_shopee',
                    'line': '0',
                })

        elif code == 4:
            if data:
                if data.get('package_number'):
                    sale_order.picking_ids.s_shopee_package_number = data.get(
                        'package_number')
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': '#Shopee: get_webhook_order_shopee',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': '4',
                        'path': 'url',
                        'message': "không có package_number, package_number: %s" % str(data),
                        'func': 'get_webhook_order_shopee',
                        'line': '0',
                    })
            else:
                self.env['ir.logging'].sudo().create({
                    'name': '#Shopee: get_webhook_order_shopee',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': '4',
                    'path': 'url',
                    'message': "không có data, data: %s" % str(data),
                    'func': 'get_webhook_order_shopee',
                    'line': '0',
                })

    def s_update_order_tiktok(self, sale_order, payload):
        if payload.get('type') == 1:
            try:
                if payload.get('data'):
                    data = payload.get('data')
                    vals = {}
                    convert_order_status = 0
                    if not sale_order.picking_ids[0].package_tiktok_id:
                        ###Thêm package_id cho DO
                        self.env['stock.picking']._mapping_package_shipping(sale_order, payload)
                    if data.get('order_status'):
                        convert_order_status = self.check_mkp_tiktok_order_status(sale_order, data)
                        completed_date = None
                        if data['order_status'] == "DELIVERED":
                            if sale_order.marketplace_tiktok_order_status not in ['100', '111', '114', '130', '140']:
                                completed_date = datetime.fromtimestamp(data['update_time'])
                        if data['order_status'] == "COMPLETED":
                            if sale_order.sudo().sale_order_status not in ['hoan_thanh_1_phan', 'giao_hang_that_bai']:
                                completed_date = datetime.fromtimestamp(data['update_time'])
                        if data['order_status'] == "CANCEL":
                            if sale_order.marketplace_tiktok_order_status not in ['122', '130']:
                                completed_date = datetime.fromtimestamp(data['update_time'])
                                is_tiktok_customer_canceled = self.user_canceled_order(sale_order=sale_order,
                                                                                       payload=payload)
                                vals['is_tiktok_customer_canceled'] = is_tiktok_customer_canceled
                        if completed_date:
                            if not sale_order.completed_date:
                                vals['completed_date'] = completed_date
                        if convert_order_status != 0:
                            vals['marketplace_tiktok_order_status'] = str(convert_order_status)
                        if convert_order_status in ['121', '112', '122', '130']:
                            if len(sale_order.picking_ids) > 0:
                                picking_ids = sale_order.picking_ids.filtered(lambda p: p.state not in (
                                    'done', 'cancel'))
                                if len(picking_ids) > 0:
                                    for picking in picking_ids:
                                        if picking.state == 'confirmed':
                                            picking.action_assign()
                                            picking.sudo().action_set_quantities_to_reservation()
                                        if picking.state == 'assigned':
                                            picking.sudo().button_validate()
                        elif convert_order_status == '140':
                            picking_sale = sale_order.picking_ids.filtered(
                                lambda r: r.transfer_type == 'out' and r.location_id.usage in ('internal',))
                            if picking_sale:
                                for picking in picking_sale:
                                    if picking.state in ('assigned', 'confirmed'):
                                        sale_order.picking_ids.action_cancel()
                                        sale_order.action_cancel()
                                    elif picking.state == 'done':
                                        return_do_picking = self._grooming_return_order(sale_order, picking)
                        if vals:
                            sale_order.sudo().write(vals)
                    else:
                        self.env['s.sale.order.error'].sudo().create({
                            'dbname': 'boo',
                            'level': 'STATUS ERROR',
                            'message': "Không có order_status trong data: %s" % str(payload),
                            'tiktok_order_id': data.get('order_id'),
                            'order_status': data.get('order_status'),
                            'update_time': data.get('update_time'),
                        })
                else:
                    self.env['s.sale.order.error'].sudo().create({
                        'dbname': 'boo',
                        'level': 'STATUS ERROR',
                        'message': "Không có data trong payload: %s" % str(payload),
                        'tiktok_order_id': payload['data']['order_id'],
                        'order_status': payload['data']['order_status'],
                        'update_time': payload['data']['update_time'],
                    })
            except Exception as e:
                self.env['ir.logging'].sudo().create({
                    'name': '#Tiktok: s_update_order_tiktok',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'STATUS ERROR',
                    'path': 'url',
                    'message': str(e) + "\t" + str(payload),
                    'func': 's_update_order_tiktok',
                    'line': '0',
                })
        elif payload.get('type') == 2:
            if payload.get('data'):
                data = payload.get('data')
                if data:
                    if data['reverse_type'] == 1 and data['reverse_order_status'] != 1:
                        if data['reverse_order_status'] == 51:
                            picking_sale = sale_order.picking_ids.filtered(
                                lambda r: r.transfer_type == 'out' and r.location_id.usage in ('internal',))
                            if picking_sale:
                                for picking in picking_sale:
                                    if sale_order.marketplace_tiktok_order_status in (
                                            '111', '100') and picking.state == 'assigned':
                                        picking.action_cancel()
                                        sale_order.action_cancel()
                                    elif sale_order.marketplace_tiktok_order_status in (
                                            '111', '112', '121') and picking_sale.state == 'done':
                                        return_do_picking = self._grooming_return_order(sale_order, picking)
                            else:
                                self.env['ir.logging'].sudo().create({
                                    'name': '#Tiktok: get_webhook_url',
                                    'type': 'server',
                                    'dbname': 'boo',
                                    'level': 'ERROR',
                                    'path': 'url',
                                    'message': "Không có DO ",
                                    'func': 'get_webhook_url',
                                    'line': '0',
                                })
                        else:
                            self.env['ir.logging'].sudo().create({
                                'name': '#Tiktok: get_webhook_url',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'path': 'url',
                                'message': "reverse_order_status != 51. Payload:%s" % str(
                                    data),
                                'func': 'get_webhook_url',
                                'line': '0',
                            })
                    elif data['reverse_type'] == 2 and data['reverse_order_status'] != 1:
                        ### start create SO return tiktok
                        if data['reverse_order_status'] in (4, 99, 100):
                            reverse_order_id = data.get('reverse_order_id')
                            # reverse_order = self.env['sale.order'].sudo()._get_reverse_order_list(reverse_order_id)
                            if reverse_order_id:
                                reverse_order = self.env['sale.order'].sudo()._get_reverse_order_list(
                                    reverse_order_id)
                                if reverse_order.get('reverse_list'):
                                    create_return_so = self.env['sale.order'].sudo().create_return_and_refund_sale_order_tiktok(
                                        reverse_order.get('reverse_list')[0], sale_order,
                                        data.get('reverse_order_status'))
                        else:
                            self.env['ir.logging'].sudo().create({
                                'name': '#Tiktok: get_webhook_url',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'path': 'url',
                                'message': "reverse_order_status không ở trạng thái 4,99,100. Payload:%s" % str(
                                    data),
                                'func': 'get_webhook_url',
                                'line': '0',
                            })
                        ### end create SO return tiktok
                    elif data['reverse_type'] == 3 and data[
                        'reverse_order_status'] != 1:
                        # if data['reverse_order_status'] == 4:
                        #     create_return_so = sale_order.create_return_sale_order()
                        ### start create SO return tiktok
                        if data.get('reverse_order_status') in (3, 4, 99, 100):
                            reverse_order_id = data.get('reverse_order_id')
                            if reverse_order_id:
                                reverse_order = self.env['sale.order'].sudo()._get_reverse_order_list(
                                    reverse_order_id)
                                if reverse_order:
                                    if reverse_order.get('reverse_list'):
                                        create_reverse_order = self.env['sale.order'].sudo().create_return_and_refund_sale_order_tiktok(
                                        reverse_order.get('reverse_list')[0], sale_order,
                                        data.get('reverse_order_status'))
                        else:
                            self.env['ir.logging'].sudo().create({
                                'name': '#Tiktok: get_webhook_url',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'path': 'url',
                                'message': "reverse_order_status không ở trạng thái 4,99,100. Payload:%s" % str(
                                    data),
                                'func': 'get_webhook_url',
                                'line': '0',
                            })
                        ### end start create SO return tiktok
                    elif data['reverse_type'] == 4 and not len(sale_order.return_order_ids) and \
                            data['reverse_order_status'] != 1:
                        if data['reverse_order_status'] == 51:
                            if len(sale_order.picking_ids) > 0:
                                for picking in sale_order.picking_ids:
                                    if picking.package_status in ("1", "2") and picking.state in (
                                            'assigned'):
                                        self.user_canceled_order(sale_order=sale_order, payload=payload)
                                        picking.action_cancel()
                                        sale_order.sudo().write({
                                            'sale_order_status': 'huy',
                                            'marketplace_tiktok_order_status': '140'
                                        })
                                    elif picking.package_status in (
                                            "1", "2") and picking.state in ('done'):
                                        self.user_canceled_order(sale_order=sale_order, payload=payload)
                                        sale_order.sudo().write({
                                            'sale_order_status': 'huy',
                                            'marketplace_tiktok_order_status': '140'
                                        })
                                        if picking.origin == sale_order.name:
                                            return_do_picking = self._grooming_return_order(sale_order, picking)
                                    elif picking.package_status not in (
                                            "1", "2") and picking.state in ('done'):
                                        if picking.origin == sale_order.name:
                                            return_do_picking = self._grooming_return_order(sale_order, picking)
                                    else:
                                        self.env['ir.logging'].sudo().create({
                                            'name': '#Tiktok: get_webhook_url',
                                            'type': 'server',
                                            'dbname': 'boo',
                                            'level': 'ERROR',
                                            'path': 'url',
                                            'message': "state DO: %s \t Package_status: %s" % (
                                                str(picking.state),
                                                str(picking.package_status)),
                                            'func': 'get_webhook_url',
                                            'line': '0',
                                        })
                    else:
                        self.env['ir.logging'].sudo().create({
                            'name': '#Tiktok: get_webhook_url',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'path': 'url',
                            'message': "data['reverse_type'] không ở trạng thái 1,2,3,4 or data['reverse_order_status'] =1. Payload:%s" % str(
                                data),
                            'func': 'get_webhook_url',
                            'line': '0',
                        })

    def check_mkp_tiktok_order_status(self, sale_order, data):
        if data[
            'order_status'] == "UNPAID" and sale_order.marketplace_tiktok_order_status not in [
            '111', '112', '114', '121', '122', '130', '140']:
            return '100'
        elif data[
            'order_status'] == "AWAITING_SHIPMENT" and sale_order.marketplace_tiktok_order_status not in [
            '112', '114', '121', '122', '130', '140']:
            return '111'
        elif data[
            'order_status'] == "AWAITING_COLLECTION" and sale_order.marketplace_tiktok_order_status not in [
            '100', '114', '121', '122', '130', '140']:
            return '112'
        # elif data['order_status'] == "PARTIALLY_SHIPPING":
        #     return 114
        elif data[
            'order_status'] == "IN_TRANSIT" and sale_order.marketplace_tiktok_order_status not in [
            '100', '111', '114', '122', '130', '140']:
            return '121'
        elif data[
            'order_status'] == "DELIVERED" and sale_order.marketplace_tiktok_order_status not in [
            '100', '111', '114', '130', '140']:
            return '122'
        elif data[
            'order_status'] == "COMPLETED" and sale_order.sudo().sale_order_status not in [
            'hoan_thanh_1_phan', 'giao_hang_that_bai']:
            return '130'
        elif data[
            'order_status'] == "CANCEL" and sale_order.marketplace_tiktok_order_status not in [
            '122',
            '130']:
            return '140'
        else:
            return 0

    # Phân biệt đơn cancel do người bán hoặc người mua hủy khi đơn đang ở trạng thái awaiting shipment, awaiting collection
    def user_canceled_order(self, sale_order, payload):
        owner = 1
        customer = 2
        awaiting_shipment_status = '111'
        awaiting_collection_status = '112'
        if sale_order.marketplace_tiktok_order_status in [awaiting_shipment_status, awaiting_collection_status]:
            if payload.get('type') == owner:
                return False
            if payload.get('type') == customer:
                return True

    def _grooming_return_order(self, sale_order, picking_sale):
        picking_return = sale_order.picking_ids.filtered(lambda r: picking_sale.name in r.origin)
        if not picking_return:
            return_form = Form(self.env['stock.return.picking'].with_context(active_id=picking_sale.id,
                                                                             active_model='stock.picking'))
            wizard = return_form.save()
            return_do_picking = wizard.create_returns()
            if picking_sale.package_status == '5':
                sale_order.sudo().write({'sale_order_status': 'giao_hang_that_bai'})
            if return_do_picking:
                picking_return = sale_order.picking_ids.filtered(
                    lambda r: r.id == return_do_picking.get('res_id'))
                picking_return.action_set_quantities_to_reservation()
                # picking_return.button_validate()
                order_tiktok_do_return = self.env['stock.picking'].sudo().search(
                    [('id', '=', return_do_picking.get('res_id'))])
                if order_tiktok_do_return and not order_tiktok_do_return.is_tiktok_do_return:
                    order_tiktok_do_return.write({'is_tiktok_do_return': True})
            return return_do_picking

    ####function để hotfix tạo lại đơn hàng cancel tiktok
    def s_create_cancel_order(self, order_id=False):
        if order_id:
            for rec in order_id:
                tiktok_order_id = self.env['sale.order'].sudo().search(
                    [('tiktok_order_id', '=', rec), ('is_tiktok_order', '=', True)], limit=1)
                if not tiktok_order_id:
                    orders_detail = self.env['sale.order'].sudo().get_order_details(str(rec))
                    if not orders_detail.get('code'):
                        customer_tiktok = self.env.ref('advanced_integrate_tiktok.s_res_partner_tiktok')
                        if orders_detail.get('order_list'):
                            if orders_detail.get('order_list')[0].get('order_status') == 140:
                                body = self._grooming_data_cancel_so_tiktok(orders_detail, customer_tiktok)
                                get_shipping = {}
                                if body is not None:
                                    # if body.get('get_shipping'):
                                    #     get_shipping = body.get('get_shipping')
                                    #     body.pop('get_shipping')
                                    created_order = self.env['sale.order'].sudo().create(body)
                                    # if len(get_shipping):
                                    #     shipping_price = orders_detail.get('order_list')[0].get('payment_info').get(
                                    #         'shipping_fee')
                                    #     is_delivery_line = created_order._create_delivery_line(
                                    #         get_shipping.get('carrier_id'),
                                    #         shipping_price)
                                    #     if is_delivery_line:
                                    #         is_delivery_line.sudo().write({
                                    #             'price_unit': shipping_price
                                    #         })
                                    ###confirm SO
                                    created_order.sudo().action_confirm()

                                    ###mapping package_status and package_tiktok_id
                                    if len(orders_detail.get('order_list')) > 0:
                                        if orders_detail.get('order_list')[0].get('package_list'):
                                            self.env['stock.picking'].sudo().s_get_package_id_tiktok(orders_detail,
                                                                                                     created_order)
                                    ###Sau khi order confirm mới cho write date_order
                                    if body.get('date_order'):
                                        created_order.sudo().write({
                                            'date_order': body.get('date_order')
                                        })
                                    if created_order.marketplace_tiktok_order_status == '140':
                                        picking_sale = created_order.picking_ids.filtered(
                                            lambda r: r.transfer_type == 'out' and r.location_id.usage == 'internal')
                                        if picking_sale and picking_sale.state in ('assigned', 'confirmed'):
                                            created_order.picking_ids.action_cancel()
                                            created_order.action_cancel()
                                    if not created_order.completed_date and body.get('completed_date'):
                                        created_order.sudo().write({
                                            'completed_date': body.get('completed_date')
                                        })
                            else:
                                self.env['ir.logging'].sudo().create({
                                    'name': '###Tiktok - Đơn hàng cancel',
                                    'type': 'server',
                                    'dbname': 'boo',
                                    'level': 'ERROR',
                                    'message': 'Đơn hàng %s không phải là đơn ở trạng thái cancel' % str(rec),
                                    'path': 'url',
                                    'func': '_post_data_bravo',
                                    'line': '0',
                                })
                    else:
                        self.env['s.sale.order.error'].sudo().create({
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'message': "",
                            'tiktok_order_id': rec,
                            # 'order_status': pay_load['data']['order_status'],
                        })

    def _grooming_data_cancel_so_tiktok(self, orders_detail, customer_tiktok):
        created_error = False
        for rec in orders_detail.get('order_list'):
            query_warehouse = self._cr.execute(
                """SELECT id FROM stock_warehouse WHERE s_warehouse_tiktok_id IS NOT NULL AND s_warehouse_tiktok_id = %s AND is_mapping_warehouse=TRUE limit 1""",
                (rec['warehouse_id'],))
            result_query_warehouse = [item[0] for item in self._cr.fetchall()]
            address_detail = None
            address_line_list = None
            city = None
            district = None
            full_address = None
            name = None
            phone = None
            region = None
            state = None
            town = None
            if rec.get('recipient_address'):
                if rec['recipient_address'].get('address_detail'):
                    address_detail = rec['recipient_address']['address_detail']
                if rec['recipient_address'].get('address_line_list'):
                    address_line_list = rec['recipient_address']['address_line_list']
                if rec['recipient_address'].get('city'):
                    city = rec['recipient_address']['city']
                if rec['recipient_address'].get('district'):
                    district = rec['recipient_address']['district']
                if rec['recipient_address'].get('full_address'):
                    full_address = rec['recipient_address']['full_address']
                if rec['recipient_address'].get('name'):
                    name = rec['recipient_address']['name']
                if rec['recipient_address'].get('phone'):
                    phone = rec['recipient_address']['phone']
                if rec['recipient_address'].get('region'):
                    region = rec['recipient_address']['region']
                if rec['recipient_address'].get('state'):
                    state = rec['recipient_address']['state']
                if rec['recipient_address'].get('town'):
                    town = rec['recipient_address']['town']
            if len(result_query_warehouse) > 0:
                note = "Thông tin khách hàng:\naddress_detail: %s\naddress_line_list: %s\ncity: %s\ndistrict: %s\nfull_address : %s\nname : %s\nphone: %s\nregion : %s\nstate: %s\ntown : %s" % (
                    address_detail, address_line_list,
                    city, district,full_address, name,phone, region,state, town)

                product_orders = []
                order = dict()
                for rec_product in rec['item_list']:
                    list_product = []
                    product_uom_qty = rec_product['quantity']
                    if "," in rec_product['seller_sku']:
                        seller_sku = rec_product['seller_sku'].split(',')
                        for r in seller_sku:
                            product_product = self.env['product.product'].sudo().search(
                                [('marketplace_sku', '=', rec_product['seller_sku']),
                                 ('default_code', '=', (r.encode('ascii', 'ignore')).decode("utf-8")),
                                 ('to_sync_tiktok', '=', True)])
                            if product_product:
                                product = {
                                    'product_id': product_product.id,
                                    'name': product_product.name,
                                    'stock_available': product_uom_qty,
                                    'uom_id': product_product.uom_id.id
                                }
                                list_product.append(product)
                            else:
                                created_error = True
                                self.env['s.sale.order.error'].sudo().create({
                                    'dbname': 'boo',
                                    'level': 'ERROR',
                                    'message': "Không có sản phẩm nào khớp với Tiktok trên odoo",
                                    'tiktok_order_id': rec
                                })
                    else:
                        product_product = self.env['product.product'].sudo().search(
                            [('default_code', '=', rec_product.get('seller_sku')), ('to_sync_tiktok', '=', True)])
                        if product_product:
                            product = {
                                'product_id': product_product.id,
                                'name': product_product.name,
                                'stock_available': product_uom_qty,
                                'uom_id': product_product.uom_id.id
                            }
                            list_product.append(product)
                        else:
                            created_error = True
                            self.env['s.sale.order.error'].sudo().create({
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'message': "Không có sản phẩm nào khớp với Tiktok trên odoo",
                                'tiktok_order_id': rec
                            })
                    if list_product:
                        ###Kiểm tra price_unit xem sản phẩm có được chiết khấu không
                        if not rec_product.get('sku_seller_discount'):
                            s_price_unit = rec_product.get('sku_original_price')
                        else:
                            s_price_unit = rec_product.get('sku_original_price') - rec_product.get('sku_seller_discount')
                        for record in list_product:
                            product_orders.append(
                                {
                                    "product_id": record.get('product_id'),
                                    "name": record.get('name'),
                                    "product_uom": record.get('uom_id'),
                                    "product_uom_qty": record.get('stock_available'),
                                    "price_unit": s_price_unit,
                                    "s_lst_price": rec_product['sku_original_price'],
                                })
                if len(product_orders) > 0 and len(product_orders) >= len(rec['item_list']) and not created_error:
                    source_id = self.env.ref('advanced_integrate_tiktok.utm_source_tiktok')
                    order['partner_id'] = customer_tiktok.id
                    order['partner_invoice_id'] = customer_tiktok.id
                    order['partner_shipping_id'] = customer_tiktok.id
                    order['tiktok_order_id'] = rec['order_id']
                    order['note'] = note
                    order['is_tiktok_order'] = True
                    order['marketplace_tiktok_order_status'] = str(rec['order_status'])
                    order['warehouse_id'] = result_query_warehouse[0]
                    order['currency_id'] = self.env.company.currency_id.id
                    order['source_id'] = source_id.id
                    order['payment_method'] = "cod" if rec.get('is_cod') else "online"
                    ####update ngày đặt hàng (create_time)
                    if rec.get('create_time'):
                        if len(str(rec.get('create_time'))) == 13:
                            order['date_order'] = datetime.fromtimestamp(int(rec.get('create_time')) / 1000)
                        else:
                            order['date_order'] = datetime.fromtimestamp(int(rec.get('create_time')))
                    order_lines = []
                    if str(rec['order_status']) in ('122', '130', '140') and rec.get('update_time'):
                        order['completed_date'] = datetime.fromtimestamp(int(rec.get('update_time')))
                    for product_order in product_orders:
                        order_lines.append((0, 0, {
                            'product_id': product_order['product_id'],
                            'name': product_order['name'],
                            'product_uom_qty': product_order['product_uom_qty'],
                            'product_uom': product_order['product_uom'],
                            'price_unit': product_order['price_unit'],
                            's_lst_price': product_order['s_lst_price'],
                            'is_product_reward': False
                        }))
                    ###Check chiết khấu của sàn tiktok
                    # if rec.get('payment_info').get('platform_discount') is not None:
                    #     discount_price = int(rec.get('payment_info').get('platform_discount'))
                    #     if discount_price > 0:
                    #         is_discount_line = self.env['sale.order'].sudo()._get_line_discount_tiktok(discount_price)
                    #         if is_discount_line:
                    #             order_lines.append((0, 0, is_discount_line))
                    if len(order_lines) > 0:
                        order['order_line'] = order_lines
                    # if 'shipping_provider' in orders_detail.get('order_list')[0]:
                    #     shipping_provider = orders_detail.get('order_list')[0]['shipping_provider']
                    #     shipping_price = orders_detail.get('order_list')[0]['payment_info']['shipping_fee']
                    #     get_shipping = self.env['s.sale.order.error'].sudo()._get_shipping_method_tiktok(
                    #         shipping_provider, shipping_price)
                    #     if get_shipping:
                    #         order['get_shipping'] = get_shipping
                    return order
            else:
                self.env['s.sale.order.error'].sudo().create({
                    'dbname': 'boo',
                    'level': 'ERROR',
                    'message': "Chưa có kho tương thích với tiktok",
                    'tiktok_order_id': orders_detail.get('order_list')[0].get('order_id')
                })

