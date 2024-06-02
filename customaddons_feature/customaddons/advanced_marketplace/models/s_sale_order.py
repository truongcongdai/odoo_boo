from odoo import fields, models, api


class SSaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    # is_ecommerce_order = fields.Boolean()
    is_lazada_order = fields.Boolean("Là đơn hàng Lazada")
    s_shopee_is_order = fields.Boolean("Là Đơn Hàng Shopee", readonly=True)
    is_tiktok_order = fields.Boolean("Là Đơn Hàng Tiktok", readonly=True)

    def _compute_order_marketplace(self):
        for r in self:
            if not r.is_lazada_order and r.return_order_id.is_lazada_order:
                r.is_lazada_order = True
            elif not r.s_shopee_is_order and r.return_order_id.s_shopee_is_order:
                r.s_shopee_is_order = True
            elif not r.is_tiktok_order and r.return_order_id.is_tiktok_order:
                r.is_tiktok_order = True

    def _compute_source_id_sale_order(self):
        for r in self:
            sale_source_id = self.env.ref('advanced_sale.utm_source_sale')
            ban_buon_source_id = self.env.ref('advanced_sale.utm_source_sell_wholesale')
            magento_source_id = self.env.ref('advanced_sale.utm_source_magento_order')
            tiktok_source_id = self.env.ref('advanced_integrate_tiktok.utm_source_tiktok')
            lazada_source_id = self.env.ref('advanced_integrate_lazada.utm_source_lazada')
            shopee_source_id = self.env.ref('advanced_integrate_shopee.utm_source_shopee')
            if not r.return_order_id:
                if not r.is_sell_wholesale and not r.is_magento_order and not r.is_tiktok_order and not r.is_lazada_order and sale_source_id:
                    r.sudo().write({
                        'source_id': sale_source_id.id
                    })
                elif r.is_sell_wholesale and ban_buon_source_id:
                    r.sudo().write({
                        'source_id': ban_buon_source_id.id
                    })
                elif r.is_magento_order and magento_source_id:
                    r.sudo().write({
                        'source_id': magento_source_id.id
                    })
                elif r.is_lazada_order:
                    r.sudo().write({
                        'source_id': lazada_source_id.id
                    })
            else:
                if r.return_order_id.is_tiktok_order and tiktok_source_id:
                    r.sudo().write({
                        'source_id': tiktok_source_id.id
                    })
                elif r.return_order_id.is_lazada_order and lazada_source_id:
                    r.sudo().write({
                        'source_id': lazada_source_id.id
                    })
                elif r.return_order_id.s_shopee_is_order and shopee_source_id:
                    r.sudo().write({
                        'source_id': shopee_source_id.id
                    })

    def _compute_marketplace_order_id(self):
        # Compute Lazada order
        lazada_orders = self.env['sale.order'].sudo().search([('is_return_order_lazada', '=', True)])
        if lazada_orders:
            for order in lazada_orders:
                if order.picking_ids:
                    for pickng_id in order.picking_ids:
                        pickng_id.sudo().write({
                            'lazada_order_id': order.return_order_id.lazada_order_id
                        })
        #compute Tiktok Shopee
        for rec in self:
            so_return = rec.return_order_ids
            if so_return:
                for r in so_return:
                    if r.is_return_order_shopee and not r.s_shopee_id_order:
                        r.s_shopee_id_order = rec.s_shopee_id_order
                    elif r.is_return_order_tiktok and not r.tiktok_order_id:
                        r.tiktok_order_id = rec.tiktok_order_id

    def _compute_mkp_payment_method(self):
        for rec in self:
            if rec.tiktok_order_id and rec.is_tiktok_order:
                orders_detail = self.sudo().get_order_details(rec.tiktok_order_id)
                if orders_detail is not None:
                    if orders_detail.get('order_list')[0]:
                        if orders_detail.get('order_list')[0].get('is_cod') is not None:
                            if orders_detail.get('order_list')[0].get('is_cod'):
                                payment_mkp_method = 'cod'
                            else:
                                payment_mkp_method = 'online'
                            ####Dùng query để update tránh làm thay đổi write_date của order
                            self._cr.execute("""
                                UPDATE sale_order SET payment_method=%s WHERE id=%s
                            """, (payment_mkp_method, rec.id))
            if rec.is_lazada_order and not rec.is_return_order_lazada:
                order_item = self.env['sale.order'].sudo().get_lazada_order(rec.lazada_order_id)
                if order_item:
                    payment_method = 'online'
                    if order_item.get('payment_method'):
                        if order_item.get('payment_method') == 'COD':
                            payment_method = 'cod'
                        ####Dùng query để update tránh làm thay đổi write_date của order
                        self._cr.execute("""
                            UPDATE sale_order SET payment_method=%s WHERE id=%s
                        """, (payment_method, rec.id))

    def cron_compute_mkp_order(self):
        source_tiktok_id = self.env.ref('advanced_integrate_tiktok.utm_source_tiktok')
        source_shopee_id = self.env.ref('advanced_integrate_shopee.utm_source_shopee')
        source_lazada_id = self.env.ref('advanced_integrate_lazada.utm_source_lazada')
        logging = self.env['ir.logging'].search(
            ['|', '|', '|', ('name', '=', '_compute_mkp_order'), ('name', '=', 'return_compute_mkp_order'),
             ('name', '=', 'khong_co_tiktok_reverse_order_id'), ('name', '=', 'khong_co_s_shopee_return_sn')]).mapped(
            'dbname')
        mkp_order = self.env['sale.order'].search(
            [('source_id', 'in', [source_shopee_id.id, source_tiktok_id.id, source_lazada_id.id]),
             ('lazada_order_id', 'not in', logging),
             ('tiktok_order_id', 'not in', logging),
             ('s_shopee_id_order', 'not in', logging),
             ('name', 'not in', logging), ('is_return_order', '=', False)], limit=500)
        if mkp_order:
            for order in mkp_order:
                order._compute_mkp_order()
                self._cr.commit()

    def _compute_mkp_order(self):
        """
            Compute MKP order:
                - Chi lay discount cua Seller, khong lay cac discount cua san
                - Khong lay phi ship
                - Lay cac thong tin bao gom: Gia san pham truoc khi chiet khau va discount cua seller
        """
        for rec in self:
            source_tiktok_id = self.env.ref('advanced_integrate_tiktok.utm_source_tiktok')
            source_shopee_id = self.env.ref('advanced_integrate_shopee.utm_source_shopee')
            source_lazada_id = self.env.ref('advanced_integrate_lazada.utm_source_lazada')
            if rec.source_id.id == source_shopee_id.id:
                rec.compute_order_shopee()
            elif rec.source_id.id == source_tiktok_id.id:
                rec.compute_order_tiktok()
            elif rec.source_id.id == source_lazada_id.id:
                rec.compute_order_lazada()

    def compute_order_lazada(self):
        for rec in self:
            if not rec.is_return_order:
                order_items = self.env['sale.order'].sudo().get_lazada_order_item(rec.lazada_order_id)
                print(order_items)
                line_exist = []
                voucher_seller_items = 0
                # mapping order line Shopee va Odoo
                if len(order_items) > 0:
                    self.env['ir.logging'].sudo().create({
                        'name': '_compute_mkp_order',
                        'type': 'server',
                        'dbname': str(rec.lazada_order_id),
                        'level': 'INFO',
                        'path': 'lazada',
                        'message': str(order_items),
                        'func': '_compute_mkp_order',
                        'line': '0',
                    })
                    for item in order_items:
                        voucher_seller_items += item.get('voucher_seller')
                        for line in rec.order_line:
                            product_sku = None
                            if line.product_id:
                                if line.product_id.is_merge_product:
                                    product_sku = line.product_id.marketplace_sku
                                else:
                                    product_sku = line.product_id.default_code
                            if product_sku:
                                if product_sku == item.get('sku'):
                                    lazada_product_qty = len(
                                        [i for i in order_items if i.get('sku') == item.get('sku')])
                                    if lazada_product_qty != abs(line.product_uom_qty):
                                        self.env['ir.logging'].sudo().create({
                                            'name': 'compute_order_lazada',
                                            'type': 'server',
                                            'dbname': 'boo',
                                            'level': 'ERROR',
                                            'path': 'chenh_lech_so_luong',
                                            'message': str(rec.name) + 'SKU' + str(
                                                item.get('model_sku')) + 'chenh lech so luong',
                                            'func': '_compute_mkp_order',
                                            'line': '0',
                                        })
                                    line.write({
                                        'price_unit': item.get('item_price'),
                                    })
                                    line_exist.append(line.id)
                    product_coupon_program = None
                    if voucher_seller_items > 0:
                        # lay line discount
                        reward_line = rec.order_line.filtered(lambda l: l.is_ecommerce_reward_line)
                        if len(reward_line) > 0:
                            reward_line[0].write({
                                'product_uom_qty': 1,
                                'price_unit': - abs(voucher_seller_items)
                            })
                            line_exist.append(reward_line[0].id)
                        else:
                            if voucher_seller_items > 0:
                                product_coupon_program = self.env['product.product'].sudo().create({
                                    'name': 'Discount Shopee',
                                    'detailed_type': 'service',
                                    'lst_price': - abs(voucher_seller_items),
                                })
                                rec.write({
                                    'order_line': [(0, 0, {
                                        'product_id': product_coupon_program.id,
                                        'product_uom_qty': 1,
                                        'price_unit': - abs(voucher_seller_items),
                                        'is_ecommerce_reward_line': True,
                                        'is_line_coupon_program': True,
                                    })]
                                })

                    if line_exist:
                        if product_coupon_program:
                            line_remove = [line for line in rec.order_line if
                                           line.id not in line_exist and line.product_id.id != product_coupon_program.id]
                        else:
                            line_remove = [line for line in rec.order_line if line.id not in line_exist]
                        if len(line_remove) > 0:
                            for remove in line_remove:
                                remove.write({
                                    'product_uom_qty': 0,
                                })
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': 'compute_order_lazada',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'khong_co_order',
                        'message': str(order_items),
                        'func': '_compute_mkp_order',
                        'line': '0',
                    })
            else:
                lazada_order_data = self.env['sale.order'].sudo().get_order_reverse_return_detail(
                    {'data': {'reverse_order_id': rec.reverse_order_id}})
                if lazada_order_data.get('data'):
                    data = lazada_order_data.get('data')
                    if len(data.get('reverseOrderLineDTOList')) > 0:
                        self.env['ir.logging'].sudo().create({
                            'name': 'return_compute_mkp_order',
                            'type': 'server',
                            'dbname': str(rec.reverse_order_id),
                            'level': 'INFO',
                            'path': 'lazada',
                            'message': str(lazada_order_data),
                            'func': '_compute_mkp_order',
                            'line': '0',
                        })
                        # mapping order line Shopee va Odoo
                        items = data.get('reverseOrderLineDTOList')
                        line_exist = []
                        voucher_seller_items = 0
                        for item in items:
                            if rec.return_order_id:
                                for line in rec.return_order_id.order_line:
                                    product_sku = None
                                    if line.product_id:
                                        if line.product_id.is_merge_product:
                                            product_sku = line.product_id.marketplace_sku
                                        else:
                                            product_sku = line.product_id.default_code
                                    if product_sku:
                                        if product_sku == item.get('seller_sku_id'):
                                            product_return = rec.order_line.filtered(
                                                lambda p: p.product_id.id == line.product_id.id)
                                            lazada_return_product_qty = [i for i in items if
                                                                         i.get('seller_sku_id') == item.get(
                                                                             'seller_sku_id')]
                                            if product_return:
                                                if len(lazada_return_product_qty) != abs(
                                                        product_return.product_uom_qty):
                                                    self.env['ir.logging'].sudo().create({
                                                        'name': 'compute_order_lazada',
                                                        'type': 'server',
                                                        'dbname': 'boo',
                                                        'level': 'ERROR',
                                                        'path': 'chenh_lech_so_luong',
                                                        'message': str(rec.name) + 'SKU' + str(
                                                            item.get('model_sku')) + 'chenh lech so luong',
                                                        'func': '_compute_mkp_order',
                                                        'line': '0',
                                                    })
                                                product_return.write({
                                                    's_lst_price': line.s_lst_price,
                                                    'price_unit': line.price_unit,
                                                })
                                                line_exist.append(product_return.id)
                                            else:
                                                rec.write({
                                                    'order_line': [(0, 0, {
                                                        'product_id': line.product_id.id,
                                                        's_lst_price': line.s_lst_price,
                                                        'price_unit': line.price_unit,
                                                        'product_uom_qty': -len(lazada_return_product_qty),
                                                        'refunded_orderline_id': line.id,
                                                    })]
                                                })
                                                return_order_line = rec.order_line.filtered(
                                                    lambda l: l.refunded_orderline_id.id == line.id)
                                                line_exist.append(return_order_line.id)
                                            if len(lazada_return_product_qty) > 0:
                                                voucher_seller_items += line.boo_total_discount_percentage * len(
                                                    lazada_return_product_qty) / product_return.product_uom_qty
                        product_coupon_program = None
                        if voucher_seller_items:
                            # lay line discount
                            reward_line = rec.order_line.filtered(lambda l: l.is_ecommerce_reward_line)
                            if len(reward_line) > 0:
                                reward_line[0].write({
                                    'product_uom_qty': -1,
                                    'price_unit': - abs(voucher_seller_items),
                                })
                                line_exist.append(reward_line[0].id)
                            else:
                                if voucher_seller_items > 0:
                                    product_coupon_program = self.env['product.product'].sudo().create({
                                        'name': 'Discount Shopee',
                                        'detailed_type': 'service',
                                        'lst_price': - abs(voucher_seller_items),
                                    })
                                    rec.write({
                                        'order_line': [(0, 0, {
                                            'product_id': product_coupon_program.id,
                                            'product_uom_qty': -1,
                                            'price_unit': - abs(voucher_seller_items),
                                            'is_ecommerce_reward_line': True,
                                            'is_line_coupon_program': True,
                                        })]
                                    })
                        if line_exist:
                            if product_coupon_program:
                                line_remove = [line for line in rec.order_line if
                                               line.id not in line_exist and line.product_id.id != product_coupon_program.id]
                            else:
                                line_remove = [line for line in rec.order_line if
                                               line.id not in line_exist]
                            if len(line_remove) > 0:
                                for remove in line_remove:
                                    remove.write({
                                        'product_uom_qty': 0,
                                    })

    def compute_order_tiktok(self):
        for rec in self:
            if not rec.is_return_order:
                orders_detail = self.env['sale.order'].get_order_details(rec.tiktok_order_id)
                # orders_detail = self.env['sale.order'].get_order_details(rec.tiktok_order_id)
                print(orders_detail)
                # shopee_order = self.env['sale.order'].sudo().get_escrow_detail(rec.s_shopee_id_order)
                # shopee_order_data = shopee_order.json()
                line_exist = []
                voucher_seller_items = 0
                if orders_detail.get('order_list')[0]:
                    order_list = orders_detail.get('order_list')[0]
                    if order_list:
                        order_line_list = order_list.get('order_line_list')
                        # mapping order line Shopee va Odoo
                        if len(order_line_list) > 0:
                            self.env['ir.logging'].sudo().create({
                                'name': '_compute_mkp_order',
                                'type': 'server',
                                'dbname': str(rec.tiktok_order_id),
                                'level': 'INFO',
                                'path': 'tiktok',
                                'message': str(orders_detail),
                                'func': '_compute_mkp_order',
                                'line': '0',
                            })
                            # items = order_income.get('items')
                            for item in order_line_list:
                                # voucher_seller_items += item.get('discount_from_voucher_seller')
                                for line in rec.order_line:
                                    product_sku = None
                                    seller_sku = []
                                    if line.product_id:
                                        if line.product_id.is_merge_product:
                                            product_sku = line.product_id.marketplace_sku
                                            if ',' not in item.get('seller_sku'):
                                                odoo_sku = line.product_id.marketplace_sku.split(
                                                    ',')
                                                if item.get('seller_sku') in odoo_sku:
                                                    seller_sku.append(line.product_id.marketplace_sku)
                                        else:
                                            product_sku = line.product_id.default_code
                                            if ',' in item.get('seller_sku'):
                                                seller_sku = item.get('seller_sku').split(',')
                                    # so luong tren tiktok
                                    tiktok_product_qty = len(
                                        [i for i in order_line_list if i.get('seller_sku') == item.get('seller_sku')])
                                    if product_sku:
                                        if product_sku == item.get('seller_sku') or product_sku in seller_sku:
                                            if tiktok_product_qty != line.product_uom_qty:
                                                self.env['ir.logging'].sudo().create({
                                                    'name': 'compute_order_tiktok',
                                                    'type': 'server',
                                                    'dbname': 'boo',
                                                    'level': 'ERROR',
                                                    'path': 'chenh_lech_so_luong',
                                                    'message': str(rec.name) + 'SKU' + str(
                                                        item.get('seller_sku')) + 'chenh lech so luong',
                                                    'func': '_compute_mkp_order',
                                                    'line': '0',
                                                })
                                            line.write({
                                                'price_unit': item.get('original_price') - item.get('seller_discount'),
                                            })
                                            line_exist.append(line.id)
                            if line_exist:
                                line_remove = [line for line in rec.order_line if line.id not in line_exist]
                                if len(line_remove) > 0:
                                    for remove in line_remove:
                                        remove.write({
                                            'product_uom_qty': 0,
                                        })
                                    # rec.order_line = [(2, line) for line in line_remove]
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': 'compute_order_tiktok',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'ERROR',
                        'path': 'khong_co_order',
                        'message': str(orders_detail),
                        'func': '_compute_mkp_order',
                        'line': '0',
                    })
            else:
                if rec.tiktok_reverse_order_id:
                    orders_detail = self.env['sale.order']._get_reverse_order_list(rec.tiktok_reverse_order_id)
                    print('orders_detail')
                    print(orders_detail)
                    # mapping order line Shopee va Odoo
                    if len(orders_detail.get('reverse_list')) > 0:
                        self.env['ir.logging'].sudo().create({
                            'name': 'return_compute_mkp_order',
                            'type': 'server',
                            'dbname': str(rec.tiktok_reverse_order_id),
                            'level': 'INFO',
                            'path': 'tiktok',
                            'message': str(orders_detail),
                            'func': '_compute_mkp_order',
                            'line': '0',
                        })
                        items = orders_detail.get('reverse_list')[0]['return_item_list']
                        line_exist = []
                        for item in items:
                            if rec.return_order_id:
                                for line in rec.return_order_id.order_line:
                                    product_sku = None
                                    seller_sku = []
                                    if line.product_id:
                                        if line.product_id.is_merge_product:
                                            product_sku = line.product_id.marketplace_sku
                                            if ',' not in item.get('seller_sku'):
                                                odoo_sku = line.product_id.marketplace_sku.split(
                                                    ',')
                                                if item.get('seller_sku') in odoo_sku:
                                                    seller_sku.append(line.product_id.marketplace_sku)
                                        else:
                                            product_sku = line.product_id.default_code
                                            if ',' in item.get('seller_sku'):
                                                seller_sku = item.get('seller_sku').split(',')
                                    if product_sku:
                                        if product_sku == item.get('seller_sku') or product_sku in seller_sku:
                                            product_return = rec.order_line.filtered(
                                                lambda p: p.product_id.id == line.product_id.id)
                                            if product_return:
                                                if item.get('return_quantity') != abs(product_return.product_uom_qty):
                                                    self.env['ir.logging'].sudo().create({
                                                        'name': 'compute_order_tiktok',
                                                        'type': 'server',
                                                        'dbname': 'boo',
                                                        'level': 'ERROR',
                                                        'path': 'chenh_lech_so_luong',
                                                        'message': str(rec.name) + 'SKU' + str(
                                                            item.get('seller_sku')) + 'chenh lech so luong',
                                                        'func': '_compute_mkp_order',
                                                        'line': '0',
                                                    })
                                                product_return.write({
                                                    's_lst_price': line.s_lst_price,
                                                    'price_unit': line.price_unit,
                                                })
                                                line_exist.append(product_return.id)
                                            else:
                                                rec.write({
                                                    'order_line': [(0, 0, {
                                                        'product_id': line.product_id.id,
                                                        's_lst_price': line.s_lst_price,
                                                        'price_unit': line.price_unit,
                                                        'product_uom_qty': - item.get('return_quantity'),
                                                        'refunded_orderline_id': line.id,
                                                    })]
                                                })
                                                return_order_line = rec.order_line.filtered(
                                                    lambda l: l.refunded_orderline_id.id == line.id)
                                                line_exist.append(return_order_line.id)
                        if line_exist:
                            line_remove = [line for line in rec.order_line if line.id not in line_exist]
                            if len(line_remove) > 0:
                                for remove in line_remove:
                                    remove.write({
                                        'product_uom_qty': 0,
                                    })
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': 'compute_order_tiktok',
                        'type': 'server',
                        'dbname': str(rec.name),
                        'level': 'ERROR',
                        'path': 'khong_co_tiktok_reverse_order_id',
                        'message': str(rec.name) + ' không có tiktok_reverse_order_id',
                        'func': '_compute_mkp_order',
                        'line': '0',
                    })

    def compute_order_shopee(self):
        for rec in self:
            if not rec.is_return_order:
                if rec.s_shopee_id_order:
                    shopee_order = self.env['sale.order'].sudo().get_escrow_detail(rec.s_shopee_id_order)
                    shopee_order_data = shopee_order.json()
                    print('shopee_order_data')
                    print(shopee_order_data)
                    line_exist = []
                    voucher_seller_items = 0
                    if shopee_order_data.get('response'):
                        response = shopee_order_data.get('response')
                        if response.get('order_income'):
                            order_income = response.get('order_income')
                            # mapping order line Shopee va Odoo
                            if len(order_income.get('items')) > 0:
                                self.env['ir.logging'].sudo().create({
                                    'name': '_compute_mkp_order',
                                    'type': 'server',
                                    'dbname': str(rec.s_shopee_id_order),
                                    'level': 'INFO',
                                    'path': 'shopee',
                                    'message': str(shopee_order_data),
                                    'func': '_compute_mkp_order',
                                    'line': '0',
                                })
                                items = order_income.get('items')
                                for item in items:
                                    voucher_seller_items += item.get('discount_from_voucher_seller')
                                    for line in rec.order_line:
                                        product_sku = None
                                        seller_sku = []
                                        if line.product_id:
                                            if line.product_id.is_merge_product:
                                                product_sku = line.product_id.marketplace_sku
                                                if ',' not in item.get('model_sku'):
                                                    odoo_sku = line.product_id.marketplace_sku.split(
                                                        ',')
                                                    if item.get('model_sku') in odoo_sku:
                                                        seller_sku.append(line.product_id.marketplace_sku)
                                            else:
                                                product_sku = line.product_id.default_code

                                                if ',' in item.get('model_sku'):
                                                    seller_sku = item.get('model_sku').split(',')
                                        if product_sku:
                                            if product_sku == item.get('model_sku') or product_sku in seller_sku:
                                                if item.get('quantity_purchased') != abs(line.product_uom_qty):
                                                    self.env['ir.logging'].sudo().create({
                                                        'name': 'compute_order_shopee',
                                                        'type': 'server',
                                                        'dbname': 'boo',
                                                        'level': 'ERROR',
                                                        'path': 'chenh_lech_so_luong',
                                                        'message': str(rec.name) + 'SKU' + str(
                                                            item.get('model_sku')) + 'chenh lech so luong',
                                                        'func': '_compute_mkp_order',
                                                        'line': '0',
                                                    })
                                                line.write({
                                                    'price_unit': item.get('discounted_price') / item.get(
                                                        'quantity_purchased'),
                                                })
                                                line_exist.append(line.id)
                                # truong hop don return voucher_from_seller = 0 or voucher_seller_items > voucher_from_seller
                                if order_income.get('voucher_from_seller') > 0 and order_income.get(
                                        'voucher_from_seller') >= voucher_seller_items:
                                    voucher_from_seller = order_income.get('voucher_from_seller')
                                else:
                                    voucher_from_seller = voucher_seller_items
                                    self.env['ir.logging'].sudo().create({
                                        'name': 'check_voucher_from_seller',
                                        'type': 'server',
                                        'dbname': 'boo',
                                        'level': 'ERROR',
                                        'path': 'url',
                                        'message': 'order_id:' + str(rec.id) + str(shopee_order_data),
                                        'func': '_compute_mkp_order',
                                        'line': '0',
                                    })
                                product_coupon_program = None
                                # lay line discount
                                reward_line = rec.order_line.filtered(lambda l: l.is_ecommerce_reward_line)
                                if voucher_from_seller > 0:
                                    if len(reward_line) > 0:
                                        reward_line[0].write({
                                            'product_uom_qty': 1,
                                            'price_unit': - voucher_from_seller
                                        })
                                        line_exist.append(reward_line[0].id)
                                    else:
                                        if voucher_from_seller > 0:
                                            product_coupon_program = self.env['product.product'].sudo().create({
                                                'name': 'Discount Shopee',
                                                'detailed_type': 'service',
                                                'lst_price': voucher_from_seller,
                                            })
                                            rec.write({
                                                'order_line': [(0, 0, {
                                                    'product_id': product_coupon_program.id,
                                                    'product_uom_qty': 1,
                                                    'price_unit': - voucher_from_seller,
                                                    'is_ecommerce_reward_line': True,
                                                    'is_line_coupon_program': True,
                                                })]
                                            })

                                if line_exist:
                                    if product_coupon_program:
                                        line_remove = [line for line in rec.order_line if
                                                       line.id not in line_exist and line.product_id.id != product_coupon_program.id]
                                    else:
                                        line_remove = [line for line in rec.order_line if
                                                       line.id not in line_exist]
                                    if len(line_remove) > 0:
                                        for remove in line_remove:
                                            remove.write({
                                                'product_uom_qty': 0,
                                            })
                        else:
                            self.env['ir.logging'].sudo().create({
                                'name': 'compute_order_shopee',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'ERROR',
                                'path': 'khong_co_order',
                                'message': str(shopee_order_data),
                                'func': '_compute_mkp_order',
                                'line': '0',
                            })
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': 'khong_co_s_shopee_return_sn',
                        'type': 'server',
                        'dbname': str(rec.name),
                        'level': 'ERROR',
                        'path': 'khong_co_s_shopee_id_order',
                        'message': str(rec.name) + ' không có s_shopee_id_order',
                        'func': '_compute_mkp_order',
                        'line': '0',
                    })
            else:
                if rec.s_shopee_return_sn:
                    shopee_order_data = self.env['sale.order'].sudo()._get_detail_so_return_shopee(
                        rec.s_shopee_return_sn)
                    # shopee_order_data = {'image': ['http://mms.img.susercontent.com/vn-11134004-7r98o-ln05qq3ciu5v54'], 'buyer_videos': [], 'reason': 'DIFFERENT_DESCRIPTION', 'text_reason': 'khác nhau màu', 'return_sn': '23101809SV2BVRE', 'refund_amount': 309000, 'currency': 'VND', 'create_time': 1697637824, 'update_time': 1698170446, 'status': 'CANCELLED', 'due_date': 1697810624, 'tracking_number': '811100347229', 'needs_logistics': True, 'amount_before_discount': 354500, 'user': {'username': 'nguyenxuanpong', 'email': '************07@gmail.com', 'portrait': 'http://mms.img.susercontent.com/198cc25d2dc4600007555336cdf00b82'}, 'item': [{'item_id': 20869971474, 'model_id': 175419359079, 'name': 'Áo Cardigan BOO Nỉ GWP 3 Bích Đi Trước', 'images': ['http://mms.img.susercontent.com/sg-11134201-22120-ui0uxunijmlved', 'http://mms.img.susercontent.com/sg-11134201-22120-5xuu8unijmlv65', 'http://mms.img.susercontent.com/sg-11134201-22120-tp2trvnijmlv4c', 'http://mms.img.susercontent.com/sg-11134201-22120-oe0j3e3ijmlv9f'], 'amount': 1, 'item_price': 353000, 'is_add_on_deal': False, 'is_main_item': False, 'item_sku': '1.2.19.3.06.002.222.23', 'variation_sku': '8930000970602', 'add_on_deal_id': 0}], 'order_sn': '23101522MCM7Y5', 'return_ship_due_date': 1698156242, 'return_seller_due_date': 0, 'activity': [], 'seller_proof': {'seller_proof_status': '', 'seller_evidence_deadline': None}, 'seller_compensation': {'seller_compensation_status': '', 'seller_compensation_due_date': None, 'compensation_amount': None}, 'negotiation': {'negotiation_status': '', 'latest_solution': '', 'latest_offer_amount': None, 'latest_offer_creator': '', 'counter_limit': None, 'offer_due_date': None}, 'logistics_status': 'LOGISTICS_REQUEST_CREATED', 'return_pickup_address': {'address': '', 'name': '', 'phone': '', 'town': '', 'district': '', 'city': '', 'state': '', 'region': '', 'zipcode': ''}}

                    print(shopee_order_data)
                    # mapping order line Shopee va Odoo
                    if len(shopee_order_data.get('item')) > 0:
                        self.env['ir.logging'].sudo().create({
                            'name': 'return_compute_mkp_order',
                            'type': 'server',
                            'dbname': str(rec.s_shopee_return_sn),
                            'level': 'INFO',
                            'path': 'shopee',
                            'message': str(shopee_order_data),
                            'func': '_compute_mkp_order',
                            'line': '0',
                        })
                        items = shopee_order_data.get('item')
                        line_exist = []
                        voucher_seller_items = 0
                        for item in items:
                            if rec.return_order_id:
                                for line in rec.return_order_id.order_line:
                                    product_sku = None
                                    seller_sku = []
                                    if line.product_id:
                                        if line.product_id.is_merge_product:
                                            product_sku = line.product_id.marketplace_sku
                                            if ',' not in item.get('variation_sku'):
                                                odoo_sku = line.product_id.marketplace_sku.split(
                                                    ',')
                                                if item.get('variation_sku') in odoo_sku:
                                                    seller_sku.append(line.product_id.marketplace_sku)
                                        else:
                                            product_sku = line.product_id.default_code
                                            if ',' in item.get('variation_sku'):
                                                seller_sku = item.get('variation_sku').split(',')
                                    if product_sku:
                                        if product_sku == item.get('variation_sku') or product_sku in seller_sku:
                                            product_return = rec.order_line.filtered(
                                                lambda p: p.product_id.id == line.product_id.id)
                                            if product_return:
                                                if item.get('amount') != abs(product_return.product_uom_qty):
                                                    self.env['ir.logging'].sudo().create({
                                                        'name': 'compute_order_shopee',
                                                        'type': 'server',
                                                        'dbname': 'boo',
                                                        'level': 'ERROR',
                                                        'path': 'chenh_lech_so_luong',
                                                        'message': str(rec.name) + 'SKU' + str(
                                                            item.get('model_sku')) + 'chenh lech so luong',
                                                        'func': '_compute_mkp_order',
                                                        'line': '0',
                                                    })
                                                product_return.write({
                                                    's_lst_price': line.s_lst_price,
                                                    'price_unit': line.price_unit,
                                                })
                                                line_exist.append(product_return.id)
                                            else:
                                                rec.write({
                                                    'order_line': [(0, 0, {
                                                        'product_id': line.product_id.id,
                                                        's_lst_price': line.s_lst_price,
                                                        'price_unit': line.price_unit,
                                                        'product_uom_qty': -item.get('amount'),
                                                        'refunded_orderline_id': line.id,
                                                    })]
                                                })
                                                return_order_line = rec.order_line.filtered(
                                                    lambda l: l.refunded_orderline_id.id == line.id)
                                                line_exist.append(return_order_line.id)
                                            if item.get('amount') > 0:
                                                voucher_seller_items += line.boo_total_discount_percentage * item.get(
                                                    'amount') / product_return.product_uom_qty
                        product_coupon_program = None
                        if voucher_seller_items:
                            # lay line discount
                            reward_line = rec.order_line.filtered(lambda l: l.is_ecommerce_reward_line)
                            if len(reward_line) > 0:
                                reward_line[0].write({
                                    'product_uom_qty': -1,
                                    'price_unit': -abs(voucher_seller_items),
                                })
                                line_exist.append(reward_line[0].id)
                            else:
                                if voucher_seller_items > 0:
                                    product_coupon_program = self.env['product.product'].sudo().create({
                                        'name': 'Discount Shopee',
                                        'detailed_type': 'service',
                                        'lst_price': -abs(voucher_seller_items),
                                    })
                                    rec.write({
                                        'order_line': [(0, 0, {
                                            'product_id': product_coupon_program.id,
                                            'product_uom_qty': -1,
                                            'price_unit': -abs(voucher_seller_items),
                                            'is_ecommerce_reward_line': True,
                                            'is_line_coupon_program': True,
                                        })]
                                    })
                        if line_exist:
                            if product_coupon_program:
                                line_remove = [line for line in rec.order_line if
                                               line.id not in line_exist and line.product_id.id != product_coupon_program.id]
                            else:
                                line_remove = [line for line in rec.order_line if
                                               line.id not in line_exist]
                            if len(line_remove) > 0:
                                for remove in line_remove:
                                    remove.write({
                                        'product_uom_qty': 0,
                                    })
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': 'khong_co_s_shopee_return_sn',
                        'type': 'server',
                        'dbname': str(rec.name),
                        'level': 'ERROR',
                        'path': 'khong_co_s_shopee_return_sn',
                        'message': str(rec.name) + ' không có s_shopee_return_sn',
                        'func': '_compute_mkp_order',
                        'line': '0',
                    })
