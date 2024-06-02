from odoo.exceptions import ValidationError
from odoo.http import request
from odoo import http
from odoo.osv.expression import AND
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token
from odoo.addons.advanced_integrate_magento.tools.common import invalid_response
from odoo.addons.advanced_integrate_bravo.controllers.bravo_api_controllers import (
    _build_domain_limit_offset, get_location_code_or_complete_name, _build_domain_limit_offset_stock
)
import json
from datetime import datetime, timedelta
import time


def format_gender(customer):
    customer_gender = -1
    if customer.gender == 'female':
        customer_gender = 1
    if customer.gender == 'male':
        customer_gender = 2
    if customer.gender == 'other':
        customer_gender = 3
    return customer_gender


def get_marketplace_order(domain, api_type):
    marketplace_order = request.env['ir.config_parameter'].get_param('integrate.marketplace_order', False)
    if marketplace_order == 'False':
        if api_type == 'api_sale_order':
            domain = AND([domain, [('is_lazada_order', '=', False), ('s_shopee_is_order', '=', False),
                                   ('is_tiktok_order', '=', False)]])
        elif api_type == 'api_order_detail':
            domain = AND([domain, [('order_id.is_lazada_order', '=', False), ('order_id.s_shopee_is_order', '=', False),
                                       ('order_id.is_tiktok_order', '=', False)]])
    return domain


class AdvancedIntegrateDataWareHouse(http.Controller):

    @staticmethod
    def _format_stock_data(domain, limit, offset):
        stock_domain = [('location_id.usage', '=', 'internal'),
                        ('location_id.s_is_transit_location', '=', False), ('location_id.scrap_location', '=', False)]
        domain = AND([domain, stock_domain])
        stock_quant_ids = request.env['stock.quant'].sudo().search(domain, limit=limit, offset=offset)

        total_stock_quant_records = request.env['stock.quant'].sudo().search_count(domain)

        res = []
        if len(stock_quant_ids):
            for stock_quant in stock_quant_ids:
                if stock_quant.location_id:
                    stock_incoming = request.env['stock.move'].sudo().read_group(
                        [('state', '=', 'assigned'), ('location_dest_id', '=', stock_quant.location_id.id)],
                        ['product_id', 'product_uom_qty',
                         'location_dest_id.name'], ['product_id'])
                    vals = {'id': stock_quant.product_id.id if stock_quant.product_id.id else None,
                            'sku': stock_quant.product_id.default_code if stock_quant.product_id and stock_quant.product_id.default_code else None,
                            'name': stock_quant.product_id.name if stock_quant.product_id.name else None, }
                    if stock_quant:
                        vals.update({
                            'warehouse_code': stock_quant.location_id.warehouse_id.code if stock_quant.location_id and stock_quant.location_id.warehouse_id and stock_quant.location_id.warehouse_id.code else None,
                            # Số lượng có thể bán trong kho hàng
                            'available': stock_quant.quantity - stock_quant.reserved_quantity,
                            # Số lượng chuẩn bị gửi cho khách hàng
                            'allocated': stock_quant.reserved_quantity,
                            # Số lượng còn trong kho
                            'onhand': stock_quant.quantity,
                            # Số lượng hàng đã hỏng
                            'damage': stock_quant.quantity if stock_quant.location_id.scrap_location == True else 0.0,
                            # Số lượng chuẩn bị chuyển vào kho
                            'incoming': stock_incoming[0]['product_uom_qty'] if stock_incoming else 0.0,
                            # Số lượng chênh lệnh giữa số lượng còn trong kho và số lượng có thể bán
                            'disparity': stock_quant.reserved_quantity,
                        })
                    res.append(vals)
        return {
            'res': res,
            'total_records': total_stock_quant_records
        }

    @validate_integrate_token
    @http.route(['/stock-data-warehouse'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_stock_data_for_data_warehouse(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            stocks = self._format_stock_data(domain, limit, offset)
            data = {
                'total_records': stocks.get('total_records'),
                'stock': stocks.get('res')
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)

    @staticmethod
    def _format_customer_data(customer_obj):
        res = []
        for customer in customer_obj:
            pos_order_refund_total = 0
            pos_order_refund = request.env['pos.order'].sudo().search([('partner_id', '=', customer.id)])
            if pos_order_refund:
                pos_order_refund_total += sum(pos_order_refund.mapped('refunded_orders_count'))
            sale_order_refund = request.env['sale.order'].sudo().search_count(
                [('partner_id', '=', customer.id), ('is_return_order', '=', True)])
            customer_store = None
            if customer.pos_create_customer == 'POS ecommerce' and not customer.s_pos_order_id:
                customer_store = 'POS ecommerce'
            elif customer.s_pos_order_id:
                if customer.s_pos_order_id.code:
                    customer_store = customer.s_pos_order_id.code
            res.append({
                'id': customer.id or None,
                'phone': customer.phone or None,
                'email': customer.email or None,
                'name': customer.name or None,
                'gender': format_gender(customer),
                'address': str(customer.street) + str(customer.ward_id.name_with_type) if customer.ward_id else None,
                'district': customer.district_id.display_name if customer.district_id else None,
                'city': customer.state_id.name if customer.state_id else None,
                'dob': customer.birthday or None,
                'point': int(customer.loyalty_points),
                'membership': customer.customer_ranked or None,
                'number_of_purchases': customer.sale_order_count + customer.pos_order_count - pos_order_refund_total - sale_order_refund,
                'last_purchase_date': customer.last_order + timedelta(hours=7) if customer.last_order else None,
                'quantity_sales': customer.total_sales_amount,
                'total_product': customer.total_sale_products_qty,
                'store': customer_store
            })
        return res

    @validate_integrate_token
    @http.route(['/customer-data-warehouse'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_customer_data_warehouse(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            customer_rank_domain = [('type', '=', 'contact')]
            domain = AND([domain, customer_rank_domain])
            customer_obj = request.env['res.partner'].sudo().search(domain, limit=limit, offset=offset)
            total_customer_records = request.env['res.partner'].search_count(domain)
            data = {
                'total_records': total_customer_records,
                'customer': self._format_customer_data(customer_obj)
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)

    @staticmethod
    def _format_employee_data(employee_obj):
        res = []
        for employee in employee_obj:
            res.append({
                'id': employee.id or None,
                'code': employee.employee_code or None,
                'name': employee.name or None,
                'dob': employee.birthday or None,
                'gender': format_gender(employee),
                'first_working_day': employee.first_working_day or None,
                'parent_id': employee.parent_id.name if employee.parent_id else None
            })
        return res

    @validate_integrate_token
    @http.route(['/employee-data-warehouse'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_employee_data(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            employee_obj = request.env['hr.employee'].sudo().search(domain, limit=limit, offset=offset)
            employee_data_obj = self._format_employee_data(employee_obj)
            total_employee_records = request.env['hr.employee'].search_count(domain)
            data = {
                'total_records': total_employee_records,
                'employee': employee_data_obj
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)

    @staticmethod
    def _format_sale_order_data(domain, limit, offset):
        res = []
        domain = get_marketplace_order(domain, 'api_sale_order')
        # domain.append(('state', 'in', ['done', 'cancel', 'sale']))
        sale_order_obj = request.env['sale.order'].sudo().search(domain, limit=limit, offset=offset)
        if sale_order_obj:
            sale_order_ids = sale_order_obj.order_line.filtered(lambda line: line.product_uom_qty != 0).mapped(
                'order_id')
            for sale_order in sale_order_ids:
                total_bill = 0
                total_discount = 0
                completed_time = sale_order.completed_date + timedelta(
                    hours=7) if sale_order.completed_date else None
                # if type(completed_time) == tuple and len(completed_time) > 0:
                #     completed_time = completed_time[0]
                # else:
                #     completed_time = None
                if sale_order.order_line:
                    for r in sale_order.order_line:
                        if sale_order.sale_order_status == 'hoan_thanh_1_phan' and sale_order.date_order >= datetime.strptime(
                                '12/05/2023 00:00', '%d/%m/%Y %H:%M'):
                            product_uom_qty = r.qty_delivered
                        else:
                            product_uom_qty = r.product_uom_qty
                        request._cr.execute("""select count(id) from product_product where id=%s""", (r.product_id.id,))
                        product_obj = request._cr.dictfetchall()
                        if len(product_obj) > 0 and product_obj[0].get('count') > 0:
                            if r.product_id.detailed_type == 'product':
                                if 0 < r.price_unit < r.s_lst_price:
                                    total_bill += product_uom_qty * r.s_lst_price
                                else:
                                    total_bill += product_uom_qty * r.price_unit
                                if r.product_uom_qty < 0:
                                    if sale_order.sale_order_status == 'hoan_thanh_1_phan' and sale_order.date_order >= datetime.strptime(
                                            '01/06/2023 00:00', '%d/%m/%Y %H:%M'):
                                        if sale_order.is_magento_order:
                                            total_discount += - ((r.m2_total_line_discount + r.boo_total_discount) * r.qty_delivered / r.product_uom_qty)
                                        else:
                                            total_discount += - ((r.boo_total_discount_percentage + r.boo_total_discount) * r.qty_delivered / r.product_uom_qty)
                                    else:
                                        if sale_order.is_magento_order:
                                            total_discount += - (abs(r.m2_total_line_discount) + r.boo_total_discount)
                                        else:
                                            total_discount += - (abs(r.boo_total_discount_percentage) + r.boo_total_discount)
                                else:
                                    if sale_order.sale_order_status == 'hoan_thanh_1_phan' and sale_order.date_order >= datetime.strptime(
                                            '01/06/2023 00:00', '%d/%m/%Y %H:%M'):
                                        if sale_order.is_magento_order:
                                            total_discount += ((r.m2_total_line_discount + r.boo_total_discount) * r.qty_delivered / r.product_uom_qty)
                                        else:
                                            total_discount += ((r.boo_total_discount_percentage + r.boo_total_discount) * r.qty_delivered / r.product_uom_qty)
                                    else:
                                        if sale_order.is_magento_order:
                                            total_discount += r.m2_total_line_discount + r.boo_total_discount
                                        else:
                                            total_discount += r.boo_total_discount_percentage + r.boo_total_discount
                warehouse_code = ''
                picking_ids = sale_order.picking_ids.filtered(lambda p: p.state in ['assigned', 'done'])
                if picking_ids:
                    for picking in picking_ids:
                        if picking.s_warehouse_id:
                            if picking.s_warehouse_id.code not in warehouse_code:
                                warehouse_code += picking.s_warehouse_id.code + ', '
                    warehouse_code = warehouse_code.rstrip(', ')
                order_type = 'Order'
                if sale_order.state == 'cancel':
                    order_type = 'Cancel'
                elif sale_order.state != 'cancel' and sale_order.is_return_order:
                    order_type = 'Return'
                total_amount = sale_order.amount_total
                if sale_order.sale_order_status == 'hoan_thanh_1_phan' and sale_order.date_order >= datetime.strptime(
                                '01/06/2023 00:00', '%d/%m/%Y %H:%M'):
                    picking_done_ids = sale_order.picking_ids.filtered(lambda p: p.state == 'done' and p.transfer_type == 'out')
                    total_amount = 0
                    if picking_done_ids:
                        for picking_done_id in picking_done_ids:
                            stock_move_ids = picking_done_id.move_lines
                            if stock_move_ids:
                                for stock_move_id in stock_move_ids:
                                    total_amount += stock_move_id.quantity_done * stock_move_id.sale_line_id.s_lst_price
                    picking_return_done_ids = sale_order.picking_ids.filtered(lambda p: p.state == 'done' and p.transfer_type == 'in')
                    if picking_return_done_ids:
                        for picking_return_id in picking_return_done_ids:
                            if picking_return_id.origin:
                                picking_name = picking_return_id.origin.strip('Return of')
                                picking_id = picking_done_ids.filtered(lambda p: p.name == picking_name)
                                if picking_id:
                                    s_stock_move_ids = picking_id.move_lines
                                    if s_stock_move_ids:
                                        for s_stock_move_id in s_stock_move_ids:
                                            total_amount -= s_stock_move_id.quantity_done * s_stock_move_id.sale_line_id.s_lst_price
                    total_amount = total_amount - total_discount
                channel_data = 'Sale'
                if sale_order.is_magento_order or (sale_order.return_order_id and sale_order.return_order_id.is_magento_order):
                    channel_data = 'Online'
                elif sale_order.is_lazada_order or sale_order.is_return_order_lazada:
                    channel_data = 'Lazada'
                elif sale_order.is_tiktok_order or sale_order.is_return_order_tiktok:
                    channel_data = 'Tiktok'
                elif sale_order.s_shopee_is_order or sale_order.is_return_order_shopee:
                    channel_data = 'Shopee'
                res.append({
                    'id': sale_order.id,
                    'order_num': sale_order.name.split("-")[0].strip() if sale_order.name else None,
                    'order_time': sale_order.create_date + timedelta(hours=7) if sale_order.create_date else None,
                    'channel': channel_data,
                    'type': order_type,
                    # Đối với đơn hàng từ module sale.order, store_code cũng là warehouse_code
                    'store_code': warehouse_code if warehouse_code else None,
                    'customer_code': sale_order.partner_id.phone if sale_order.partner_id and sale_order.partner_id.phone else None,
                    'saleman_code': sale_order.user_id.employee_id.employee_code if sale_order.user_id and sale_order.user_id.employee_id and sale_order.user_id.employee_id.employee_code else None,
                    'warehouse_code': warehouse_code if warehouse_code else None,
                    'total_bill': total_bill,
                    'total_discount': total_discount,
                    'total_amount': total_amount,
                    'online_order_id': sale_order.m2_so_id if sale_order.m2_so_id else None,
                    'reference_order_id': sale_order.return_order_id.name if sale_order.return_order_id else None,
                    'completed_time': completed_time,
                })
        total_so_records = request.env['sale.order'].search_count(domain)
        return {
            'res': res,
            'sale_order_total': total_so_records
        }

    @staticmethod
    def _format_pos_order_data(domain, limit, offset):
        res = []
        domain = AND([domain, [('state', '!=', 'draft')]])
        #     domain.append(('is_cancel_order', '=', False))
        pos_order_obj = request.env['pos.order'].sudo().search(domain, limit=limit, offset=offset)
        if pos_order_obj:
            pos_order_ids = pos_order_obj.lines.filtered(lambda line: line.qty != 0).mapped('order_id')
            for pos_order in pos_order_ids:
                warehouse_code = ''
                pos_config = pos_order.config_id
                # if pos_order.picking_type_id and pos_order.picking_type_id.warehouse_id:
                #     warehouse_code = pos_order.picking_type_id.warehouse_id.code
                picking_ids = pos_order.picking_ids.filtered(lambda p: p.state in ['assigned', 'done'])
                if picking_ids:
                    for picking in picking_ids:
                        if picking.s_warehouse_id:
                            if picking.s_warehouse_id.code not in warehouse_code:
                                warehouse_code += picking.s_warehouse_id.code + ', '
                    warehouse_code = warehouse_code.rstrip(', ')
                order_type = 'Order'
                if pos_order.is_cancel_order and pos_order.refunded_orders_count > 0:
                    order_type = 'Cancel'
                elif not pos_order.is_cancel_order and pos_order.refunded_orders_count > 0:
                    order_type = 'Return'
                total_bill = 0
                total_discount = 0
                if pos_order.lines:
                    if order_type == 'Return' and pos_order.write_date > datetime.strptime("2023-04-10 23:59:59",
                                                                                           "%Y-%m-%d %H:%M:%S"):
                        for r in pos_order.lines:
                            if r.product_id.detailed_type == 'product':
                                if 0 < r.price_unit < r.s_lst_price:
                                    total_bill += r.qty * r.s_lst_price
                                else:
                                    total_bill += r.qty * r.price_unit
                                # if not r.refunded_orderline_id:
                                #     total_discount += r.boo_total_discount_percentage
                                total_discount += (r.boo_total_discount_percentage + r.boo_total_discount)
                            elif r.product_id.detailed_type == 'service':
                                if r.qty < 0 and r.price_unit < 0:
                                    total_bill += r.qty * r.price_unit

                    elif order_type != 'Return' or order_type == 'Return' and pos_order.write_date < datetime.strptime(
                            "2023-04-10 23:59:59", "%Y-%m-%d %H:%M:%S"):
                        for r in pos_order.lines:
                            if r.product_id.detailed_type == 'product':
                                if 0 < r.price_unit < r.s_lst_price:
                                    total_bill += r.qty * r.s_lst_price
                                else:
                                    total_bill += r.qty * r.price_unit
                                if r.qty < 0:
                                    total_discount += - (r.boo_total_discount_percentage + r.boo_total_discount)
                                else:
                                    total_discount += r.boo_total_discount_percentage + r.boo_total_discount
                reference_order_id = ''
                if pos_order.refunded_order_ids:
                    for rec in pos_order.refunded_order_ids:
                        if 'Đơn hàng' in rec.pos_reference:
                            reference_order_id += rec.pos_reference.strip('Đơn hàng')
                        elif 'Order' in rec.pos_reference:
                            reference_order_id += rec.pos_reference.strip('Order')
                        reference_order_id += ','
                    reference_order_id = reference_order_id.rstrip(',')

                res.append({
                    'id': pos_order.id,
                    'order_num': pos_order.pos_reference.strip(
                        'Đơn hàng') if 'Đơn hàng' in pos_order.pos_reference else pos_order.pos_reference.strip(
                        'Order'),  # Đơn hoàn tiền vẫn có string 'Đơn hàng'
                    'order_time': pos_order.create_date + timedelta(hours=7) if pos_order.create_date else None,
                    'channel': 'Offline',
                    'type': order_type,
                    'store_code': pos_config.code if pos_config and pos_config.code else None,
                    'customer_code': pos_order.partner_id.phone if pos_order.partner_id and pos_order.partner_id.phone else None,
                    'saleman_code': pos_order.sale_person_id.employee_code if pos_order.sale_person_id else None,
                    'warehouse_code': warehouse_code if warehouse_code else None,
                    'total_bill': total_bill,
                    'total_discount': total_discount,
                    'total_amount': pos_order.amount_total,
                    'online_order_id': None,
                    'reference_order_id': reference_order_id if reference_order_id else None,
                    'completed_time': pos_order.date_order + timedelta(hours=7) if pos_order.date_order else None,
                })
        total_po_records = request.env['pos.order'].search_count(domain)
        return {
            'res': res,
            'pos_order_total': total_po_records
        }

    @validate_integrate_token
    @http.route(['/order-data-warehouse'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_order_data_warehouse(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            if kwargs.get('store', ''):
                domain = AND([domain, [('s_store_code', 'in', [kwargs['store']])]])
            if kwargs.get('order_time_start', ''):
                if len(kwargs['order_time_start'].rstrip()) > 10:
                    if datetime.strptime(kwargs['order_time_start'],
                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        kwargs['order_time_start'], '%d/%m/%Y %H:%M').minute is not None:
                        order_time_start = datetime.strptime(kwargs['order_time_start'], '%d/%m/%Y %H:%M') - timedelta(
                            hours=7)
                        if order_time_start:
                            domain = AND([domain, [('create_date', '>=', order_time_start)]])
                else:
                    domain = AND([domain, [
                        ('create_date', '>=',
                         datetime.strptime(kwargs['order_time_start'] + ' 00:00', '%d/%m/%Y %H:%M') - timedelta(
                             hours=7))]])
            if kwargs.get('order_time_end', ''):
                if len(kwargs['order_time_end'].rstrip()) > 10:
                    if datetime.strptime(kwargs['order_time_end'],
                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        kwargs['order_time_end'], '%d/%m/%Y %H:%M').minute is not None:
                        order_time_end = datetime.strptime(kwargs['order_time_end'], '%d/%m/%Y %H:%M') - timedelta(
                            hours=7)
                        if order_time_end:
                            domain = AND([domain, [('create_date', '<=', order_time_end)]])
                else:
                    domain = AND(
                        [domain,
                         [('create_date', '<=',
                           datetime.strptime(kwargs['order_time_end'] + ' 23:59', '%d/%m/%Y %H:%M') - timedelta(
                               hours=7))]])
            if kwargs.get('completed_time_start', ''):
                if len(kwargs['completed_time_start'].rstrip()) > 10:
                    if datetime.strptime(kwargs['completed_time_start'],
                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        kwargs['completed_time_start'], '%d/%m/%Y %H:%M').minute is not None:
                        completed_time_start = datetime.strptime(kwargs['completed_time_start'],
                                                                 '%d/%m/%Y %H:%M') - timedelta(hours=7)
                        if completed_time_start:
                            domain = AND([domain, [('date_order', '>=', completed_time_start)]])
                else:
                    domain = AND([domain, [
                        ('date_order', '>=',
                         datetime.strptime(kwargs['completed_time_start'] + ' 00:00', '%d/%m/%Y %H:%M') - timedelta(
                             hours=7))]])
            if kwargs.get('completed_time_end', ''):
                if len(kwargs['completed_time_end'].rstrip()) > 10:
                    if datetime.strptime(kwargs['completed_time_end'],
                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        kwargs['completed_time_end'], '%d/%m/%Y %H:%M').minute is not None:
                        completed_time_end = datetime.strptime(kwargs['completed_time_end'],
                                                               '%d/%m/%Y %H:%M') - timedelta(hours=7)
                        if completed_time_end:
                            domain = AND([domain, [('date_order', '<=', completed_time_end)]])
                else:
                    domain = AND(
                        [domain,
                         [('date_order', '<=',
                           datetime.strptime(kwargs['completed_time_end'] + ' 23:59', '%d/%m/%Y %H:%M') - timedelta(
                               hours=7))]])
            sale_order_data = self._format_sale_order_data(domain, limit, offset)
            pos_order_data = self._format_pos_order_data(domain, limit, offset)
            order_obj = sale_order_data.get('res') + pos_order_data.get('res')
            order_total = sale_order_data.get('sale_order_total') + pos_order_data.get('pos_order_total')
            data = {
                'total_records': order_total,
                'order': order_obj
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)

    @staticmethod
    def _format_sale_order_line_data(domain, limit, offset):
        domain = get_marketplace_order(domain, 'api_order_detail')
        res = []
        res_stock_move_ids = []
        sale_order_domain = domain + [('product_uom_qty', '!=', 0)]
        sale_order_line = request.env['sale.order.line'].sudo().search(sale_order_domain, limit=limit, offset=offset)
        if sale_order_line:
            for order_line in sale_order_line:
                if order_line.order_id.date_order >= datetime.strptime('12/05/2023 00:00',
                                                                       '%d/%m/%Y %H:%M') and order_line.order_id.sale_order_status == 'hoan_thanh_1_phan':
                    product_uom_qty = order_line.qty_delivered
                else:
                    product_uom_qty = order_line.product_uom_qty
                completed_time = None
                if order_line.order_id:
                    if order_line.order_id.completed_date:
                        completed_time =  order_line.order_id.completed_date + timedelta(hours=7)
                # if type(completed_time) == tuple and len(completed_time) > 0:
                #     completed_time = completed_time[0]
                # else:
                #     completed_time = None

                amount = 0
                discount_amount = 0
                product_discount = 0
                # product_obj = request.env['product.product'].sudo().search_count(
                #     [('id', '=', order_line.product_id.id)])
                request._cr.execute("""select count(id) from product_product where id=%s""",
                                    (order_line.product_id.id,))
                product_obj = request._cr.dictfetchall()
                if len(product_obj) > 0 and product_obj[0].get('count') > 0 and product_uom_qty != 0:
                    if 0 <= order_line.price_unit < order_line.s_lst_price:
                        amount += product_uom_qty * order_line.s_lst_price
                    else:
                        amount += product_uom_qty * order_line.price_unit
                    if order_line.product_uom_qty < 0:
                        product_discount -= (order_line.boo_total_discount)
                        if order_line.order_id.is_magento_order:
                            discount_amount -= (
                                    order_line.m2_total_line_discount + order_line.boo_total_discount)
                        else:
                            discount_amount -= (-order_line.boo_total_discount_percentage + order_line.boo_total_discount)
                    else:
                        product_discount += order_line.boo_total_discount
                        if order_line.order_id.is_magento_order:
                            discount_amount += order_line.m2_total_line_discount + order_line.boo_total_discount
                        else:
                            discount_amount += order_line.boo_total_discount_percentage + order_line.boo_total_discount
                if len(order_line.move_ids) > 1:
                    stock_move_ids = order_line.move_ids
                    picking_return_done_ids = order_line.order_id.picking_ids.filtered(
                        lambda p: p.state == 'done' and p.transfer_type == 'in')
                    if picking_return_done_ids:
                        for picking_return_id in picking_return_done_ids:
                            if picking_return_id.origin:
                                picking_name = picking_return_id.origin.strip('Return of')
                                picking_id = order_line.order_id.picking_ids.filtered(lambda p: p.name == picking_name)
                                if picking_id:
                                    s_stock_move_ids = picking_id.move_lines
                                    if s_stock_move_ids:
                                        for s_stock_move_id in s_stock_move_ids:
                                            stock_move_ids -= s_stock_move_id
                    for stock_move in stock_move_ids:
                        if (order_line.product_id.la_so_tien_phai_thu_them == False or order_line.product_id.la_phi_ship_hang_m2 == False) and stock_move.picking_id.transfer_type == 'out':
                            if stock_move.picking_id.state not in ['cancel'] and product_uom_qty != 0:
                                warehouse_code = stock_move.picking_id.s_warehouse_id.code if stock_move.picking_id.s_warehouse_id else None
                                # warehouse_code = ''
                                # stock_move_ids = order_line.move_ids
                                # if stock_move_ids:
                                #     for stock_move in stock_move_ids:
                                #         if stock_move.picking_id.state in ['assigned', 'done']:
                                #             if stock_move.picking_id.s_warehouse_id:
                                #                 if stock_move.picking_id.s_warehouse_id.code not in warehouse_code:
                                #                     warehouse_code += stock_move.picking_id.s_warehouse_id.code + ', '
                                #     warehouse_code = warehouse_code.rstrip(', ')
                                if not order_line.order_id.is_return_order:
                                    res.append({
                                        'id': order_line.id,
                                        'order_num': order_line.order_id.name.split("-")[
                                            0].strip() if order_line.order_id.name else None,
                                        'order_time': order_line.create_date + timedelta(
                                            hours=7) if order_line.create_date else None,
                                        'warehouse_code': warehouse_code if warehouse_code else None,
                                        'item_code': order_line.product_id.ma_san_pham if order_line.product_id and order_line.product_id.ma_san_pham else None,
                                        'sku': order_line.product_id.default_code if order_line.product_id and order_line.product_id.default_code else None,
                                        'quantity': stock_move.product_uom_qty,
                                        'amount': (amount / product_uom_qty) * stock_move.product_uom_qty if product_uom_qty else 0,
                                        'discount_amount': (discount_amount / order_line.product_uom_qty) * stock_move.product_uom_qty if product_uom_qty else 0,
                                        'total_amount': amount - (discount_amount / order_line.product_uom_qty) * stock_move.product_uom_qty if product_uom_qty else 0,
                                        'product_discount': product_discount,
                                        'completed_time': completed_time,
                                    })
                                else:
                                    res.append({
                                        'id': order_line.id,
                                        'order_num': order_line.order_id.name.split("-")[
                                            0].strip() if order_line.order_id.name else None,
                                        'order_time': order_line.create_date + timedelta(
                                            hours=7) if order_line.create_date else None,
                                        'warehouse_code': warehouse_code if warehouse_code else None,
                                        'item_code': order_line.product_id.ma_san_pham if order_line.product_id and order_line.product_id.ma_san_pham else None,
                                        'sku': order_line.product_id.default_code if order_line.product_id and order_line.product_id.default_code else None,
                                        'quantity': product_uom_qty,
                                        'amount': amount,
                                        'discount_amount': discount_amount,
                                        'total_amount': amount - discount_amount,
                                        'product_discount': product_discount,
                                        'completed_time': completed_time,
                                    })
                            elif stock_move.picking_id.state in ['cancel'] and product_uom_qty == 0:
                                picking_ids = stock_move_ids.mapped('picking_id.id')
                                picking_ids.sort()
                                picking_id = stock_move_ids.mapped('picking_id').filtered(lambda p: p.id == picking_ids[-1])
                                warehouse_code = picking_id.s_warehouse_id.code if picking_id.s_warehouse_id else None
                                res_stock_move_ids.append({
                                    'id': order_line.id,
                                    'order_num': order_line.order_id.name.split("-")[
                                        0].strip() if order_line.order_id.name else None,
                                    'order_time': order_line.create_date + timedelta(
                                        hours=7) if order_line.create_date else None,
                                    'warehouse_code': warehouse_code if warehouse_code else None,
                                    'item_code': order_line.product_id.ma_san_pham if order_line.product_id and order_line.product_id.ma_san_pham else None,
                                    'sku': order_line.product_id.default_code if order_line.product_id and order_line.product_id.default_code else None,
                                    'quantity': product_uom_qty,
                                    'amount': (
                                                      amount / product_uom_qty) * stock_move.product_uom_qty if product_uom_qty else 0,
                                    'discount_amount': (
                                                               discount_amount / order_line.product_uom_qty) * stock_move.product_uom_qty if product_uom_qty else 0,
                                    'total_amount': amount - (
                                            discount_amount / order_line.product_uom_qty) * stock_move.product_uom_qty if product_uom_qty else 0,
                                    'product_discount': product_discount,
                                    'completed_time': completed_time,
                                })
                                if len(res_stock_move_ids) == 1:
                                    break
                elif len(order_line.move_ids) == 1:
                    warehouse_code = order_line.move_ids.picking_id.s_warehouse_id.code if order_line.move_ids.picking_id.s_warehouse_id else None
                    res.append({
                        'id': order_line.id,
                        'order_num': order_line.order_id.name.split("-")[
                            0].strip() if order_line.order_id.name else None,
                        'order_time': order_line.create_date + timedelta(hours=7) if order_line.create_date else None,
                        'warehouse_code': warehouse_code if warehouse_code else None,
                        'item_code': order_line.product_id.ma_san_pham if order_line.product_id and order_line.product_id.ma_san_pham else None,
                        'sku': order_line.product_id.default_code if order_line.product_id and order_line.product_id.default_code else None,
                        'quantity': product_uom_qty,
                        'amount': amount,
                        'discount_amount': discount_amount,
                        'total_amount': amount - discount_amount,
                        'product_discount': product_discount,
                        'completed_time': completed_time,
                    })
        total_so_line_records = request.env['sale.order.line'].search_count(domain)
        res += res_stock_move_ids
        return {
            'res': res,
            'sale_order_line_total': total_so_line_records
        }

    @staticmethod
    def _format_pos_order_line_data(domain, limit, offset):
        res = []
        pos_order_domain = domain + [('qty', '!=', 0), ('order_id.state', '!=', 'draft')]
        pos_order_line = request.env['pos.order.line'].sudo().search(pos_order_domain, limit=limit, offset=offset)
        if pos_order_line:
            for order_line in pos_order_line:
                warehouse_code = ''
                picking_ids = order_line.order_id.picking_ids.filtered(lambda p: p.state in ['assigned', 'done'])
                if picking_ids:
                    for picking in picking_ids:
                        if picking.s_warehouse_id:
                            if picking.s_warehouse_id.code not in warehouse_code:
                                warehouse_code += picking.s_warehouse_id.code + ', '
                    warehouse_code = warehouse_code.rstrip(', ')
                amount = 0
                discount_amount = 0
                product_discount = 0
                # product_obj = request.env['product.product'].sudo().search_count(
                #     [('id', '=', order_line.product_id.id)])
                request._cr.execute("""select count(id) from product_product where id=%s""", (order_line.product_id.id,))
                product_obj = request._cr.dictfetchall()
                if len(product_obj) > 0 and product_obj[0].get('count') > 0:
                    if 0 <= order_line.price_unit < order_line.s_lst_price:
                        amount += order_line.qty * order_line.s_lst_price
                    else:
                        amount += order_line.qty * order_line.price_unit
                    if order_line.qty < 0:
                        discount_amount += (order_line.boo_total_discount_percentage + order_line.boo_total_discount)
                        product_discount += (order_line.boo_total_discount)
                    else:
                        discount_amount += order_line.boo_total_discount_percentage + order_line.boo_total_discount
                        product_discount += order_line.boo_total_discount
                res.append({
                    'id': order_line.id,
                    'order_num': order_line.order_id.pos_reference.strip(
                        'Đơn hàng') if 'Đơn hàng' in order_line.order_id.pos_reference else order_line.order_id.pos_reference.strip(
                        'Order'),
                    'order_time': order_line.create_date + timedelta(hours=7) if order_line.create_date else None,
                    'warehouse_code': warehouse_code if warehouse_code else None,
                    'item_code': order_line.product_id.ma_san_pham if order_line.product_id and order_line.product_id.ma_san_pham else None,
                    'sku': order_line.product_id.default_code if order_line.product_id and order_line.product_id.default_code else None,
                    'quantity': order_line.qty,
                    'amount': amount,
                    'discount_amount': discount_amount,
                    'total_amount': amount - discount_amount,
                    'product_discount': product_discount,
                    'completed_time': order_line.order_id.date_order + timedelta(
                        hours=7) if order_line.order_id.date_order else None,
                })
        total_po_line_records = request.env['pos.order.line'].search_count(domain)
        return {
            'res': res,
            'pos_order_line_total': total_po_line_records
        }

    @validate_integrate_token
    @http.route(['/order-detail-data-warehouse'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_order_detail_data_warehouse(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            domain += [('product_id.detailed_type', '=', 'product')]
            if kwargs.get('store', ''):
                domain = AND([domain, [('s_store_code', 'in', [kwargs['store']])]])

            if kwargs.get('order_time_start', ''):
                if len(kwargs['order_time_start'].rstrip()) > 10:
                    if datetime.strptime(kwargs['order_time_start'],
                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        kwargs['order_time_start'], '%d/%m/%Y %H:%M').minute is not None:
                        order_time_start = datetime.strptime(kwargs['order_time_start'], '%d/%m/%Y %H:%M') - timedelta(
                            hours=7)
                        if order_time_start:
                            domain = AND([domain, [('create_date', '>=', order_time_start)]])
                else:
                    domain = AND([domain, [
                        ('create_date', '>=',
                         datetime.strptime(kwargs['order_time_start'] + ' 00:00', '%d/%m/%Y %H:%M') - timedelta(
                             hours=7))]])
            if kwargs.get('order_time_end', ''):
                if len(kwargs['order_time_end'].rstrip()) > 10:
                    if datetime.strptime(kwargs['order_time_end'],
                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        kwargs['order_time_end'], '%d/%m/%Y %H:%M').minute is not None:
                        order_time_end = datetime.strptime(kwargs['order_time_end'], '%d/%m/%Y %H:%M') - timedelta(
                            hours=7)
                        if order_time_end:
                            domain = AND([domain, [('create_date', '<=', order_time_end)]])
                else:
                    domain = AND(
                        [domain,
                         [('create_date', '<=',
                           datetime.strptime(kwargs['order_time_end'] + ' 23:59', '%d/%m/%Y %H:%M') - timedelta(
                               hours=7))]])
            if kwargs.get('completed_time_start', ''):
                if len(kwargs['completed_time_start'].rstrip()) > 10:
                    if datetime.strptime(kwargs['completed_time_start'],
                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        kwargs['completed_time_start'], '%d/%m/%Y %H:%M').minute is not None:
                        completed_time_start = datetime.strptime(kwargs['completed_time_start'],
                                                                 '%d/%m/%Y %H:%M') - timedelta(hours=7)
                        if completed_time_start:
                            domain = AND([domain, [('order_id.date_order', '>=', completed_time_start)]])
                else:
                    domain = AND([domain, [
                        ('order_id.date_order', '>=',
                         datetime.strptime(kwargs['completed_time_start'] + ' 00:00', '%d/%m/%Y %H:%M') - timedelta(
                             hours=7))]])
            if kwargs.get('completed_time_end', ''):
                if len(kwargs['completed_time_end'].rstrip()) > 10:
                    if datetime.strptime(kwargs['completed_time_end'],
                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        kwargs['completed_time_end'], '%d/%m/%Y %H:%M').minute is not None:
                        completed_time_end = datetime.strptime(kwargs['completed_time_end'],
                                                               '%d/%m/%Y %H:%M') - timedelta(hours=7)
                        if completed_time_end:
                            domain = AND([domain, [('order_id.date_order', '<=', completed_time_end)]])
                else:
                    domain = AND(
                        [domain,
                         [('order_id.date_order', '<=',
                           datetime.strptime(kwargs['completed_time_end'] + ' 23:59', '%d/%m/%Y %H:%M') - timedelta(
                               hours=7))]])

            sale_order_line_data = self._format_sale_order_line_data(domain, limit, offset)
            pos_order_line_data = self._format_pos_order_line_data(domain, limit, offset)
            order_detail_obj = sale_order_line_data.get('res') + pos_order_line_data.get('res')
            order_detail_total = sale_order_line_data.get('sale_order_line_total') + pos_order_line_data.get(
                'pos_order_line_total')
            data = {
                'total_records': order_detail_total,
                'order': order_detail_obj
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)

    @staticmethod
    def _format_warehouse_info_data(warehouse_obj):
        res = []
        for warehouse in warehouse_obj:
            res.append({
                'id': warehouse.id if warehouse.id else None,
                'code': warehouse.code if warehouse.code else None,
                'name': warehouse.name if warehouse.name else None,
            })
        return res

    @validate_integrate_token
    @http.route(['/warehouse-info-data-warehouse'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_warehouse_info_data_warehouse(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            warehouse_obj = request.env['stock.warehouse'].sudo().search(domain, limit=limit, offset=offset)
            total_stock_wh_records = request.env['stock.warehouse'].search_count(domain)
            data = {
                'total_records': total_stock_wh_records,
                'warehouse': self._format_warehouse_info_data(warehouse_obj)
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)

    @staticmethod
    def _format_store_info_data(store_obj):
        res = []
        for store in store_obj:
            res.append({
                'id': store.id if store.id else None,
                'code': store.code if store.name else None,
                'name': store.name if store.name else None,
            })
        return res

    @validate_integrate_token
    @http.route(['/store-info-data-warehouse'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_store_info_data_warehouse(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            store_obj = request.env['pos.config'].sudo().search(domain, limit=limit, offset=offset)
            total_pos_config_records = request.env['pos.config'].search_count(domain)
            data = {
                'total_records': total_pos_config_records,
                'store': self._format_store_info_data(store_obj)
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)

    @staticmethod
    def _format_order_status_data(order_status_obj):
        res = []
        for order_status in order_status_obj:
            if order_status.field.name == 'sale_order_status':
                so_id = request.env['sale.order'].search([('id', '=', order_status.mail_message_id.res_id)])
                if so_id and (order_status.old_value_char or order_status.new_value_char):
                    res.append({
                        'id': order_status.id or None,
                        'order_num': so_id.name if "-" not in so_id.name else so_id.name.split("-")[
                            0].strip(),
                        'from_status': order_status.old_value_char if order_status.old_value_char != 'Hoàn thành 1 phần' else 'Hoàn thành',
                        'to_status': order_status.new_value_char if order_status.new_value_char != 'Hoàn thành 1 phần' else 'Hoàn thành',
                        'created_time': order_status.create_date + timedelta(hours=7),
                    })
            elif order_status.field.name == 'pos_order_status':
                po_id = request.env['pos.order'].search([('id', '=', order_status.mail_message_id.res_id)])
                if po_id and (order_status.old_value_char or order_status.new_value_char):
                    res.append({
                        'id': order_status.id or None,
                        'order_num': po_id.pos_reference.strip(
                            'Đơn hàng') if 'Đơn hàng' in po_id.pos_reference else po_id.pos_reference.strip(
                            'Order'),
                        'from_status': order_status.old_value_char,
                        'to_status': order_status.new_value_char,
                        'created_time': order_status.create_date + timedelta(hours=7),
                    })
        return res

    @validate_integrate_token
    @http.route(['/order-status-history-log'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_order_status_data_warehouse(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            domain = AND([domain, ['|',
                                   ('field.name', '=', 'sale_order_status'),
                                   ('field.name', '=', 'pos_order_status')]])
            order_status_obj = request.env['mail.tracking.value'].sudo().search(domain, limit=limit, offset=offset)
            total_mail_tracking_value_records = request.env['mail.tracking.value'].search_count(domain)
            data = {
                'total_records': total_mail_tracking_value_records,
                'order_status': self._format_order_status_data(order_status_obj)
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)

    @staticmethod
    def _format_product_data(product_obj):
        res = []
        for product in product_obj:
            # format gender
            product_gender = -1
            if product.gioi_tinh:
                if product.gioi_tinh == 'female':
                    product_gender = 1
                elif product.gioi_tinh == 'male':
                    product_gender = 2
                elif product.gioi_tinh == 'other':
                    product_gender = 3
            # format gender
            # get sub_category
            sub_category = None
            if product.categ_id and product.categ_id.parent_id:
                sub_category = product.categ_id.parent_id.name
            # get sub_category
            sell_price = product.lst_price
            if product.pricelist_id:
                price_id = request.env['product.pricelist.item'].search(
                    [('pricelist_id', '=', product.pricelist_id.id),
                     ('product_id', '=', product.id),
                     ('date_start', '<', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                     ('date_end', '>', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))],
                    order='min_quantity desc', limit=1)
                if price_id:
                    sell_price = price_id.fixed_price

            res.append({
                'id': product.id or None,
                'item_code': product.ma_san_pham or None,
                'sku': product.default_code or None,
                'name': product.name or None,
                'brand': product.thuong_hieu.name if product.thuong_hieu and product.thuong_hieu.name else None,
                'category': product.categ_id.name if product.categ_id and product.categ_id.name else None,
                'sub_category': sub_category,
                'collection': product.bo_suu_tap.name if product.bo_suu_tap and product.bo_suu_tap.name else None,
                'color': product.mau_sac or None,
                'gender': product_gender,
                'line': product.dong_hang.name if product.dong_hang and product.dong_hang.name else None,
                'material': product.chat_lieu.name if product.chat_lieu.name else None,
                'product_type': product.detailed_type,
                'season': product.season.name if product.season and product.season.name else None,
                'original_price': product.lst_price or None,
                'sell_price': sell_price,
                'size': product.kich_thuoc or None,
                'product_green_type': product.is_product_green or None
            })
        return res

    @validate_integrate_token
    @http.route(['/product-data-warehouse'], methods=['GET', 'POST'], auth='public', type='json', csrf=False)
    def get_product_data_warehouse(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            product_domain = [('sale_ok', '=', True), ('la_phi_ship_hang_m2', '!=', True)]
            time_end = None
            if kwargs.get('time_start', ''):
                if len(kwargs['time_start'].rstrip()) > 10:
                    if datetime.strptime(kwargs['time_start'], '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                            kwargs['time_start'], '%d/%m/%Y %H:%M').minute is not None:
                        time_start = datetime.strptime(kwargs['time_start'], '%d/%m/%Y %H:%M') - timedelta(hours=7)
                        if time_start:
                            product_domain = ['|', ('product_tmpl_id.write_date', '>=', time_start),
                                              ('write_date', '>=', time_start), ('sale_ok', '=', True),
                                              ('la_phi_ship_hang_m2', '!=', True)]
                            if kwargs.get('time_end', ''):
                                if len(kwargs['time_end'].rstrip()) > 10:
                                    if datetime.strptime(kwargs['time_end'],
                                                         '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                                        kwargs['time_end'], '%d/%m/%Y %H:%M').minute is not None:
                                        time_end = datetime.strptime(kwargs['time_end'], '%d/%m/%Y %H:%M') - timedelta(
                                            hours=7)
                                else:
                                    time_end = datetime.strptime(kwargs['time_end'] + ' 23:59',
                                                                 '%d/%m/%Y %H:%M') - timedelta(hours=7)
                else:
                    time_start = datetime.strptime(kwargs['time_start'] + ' 00:00', '%d/%m/%Y %H:%M') - timedelta(
                        hours=7)
                    product_domain = ['|', ('product_tmpl_id.write_date', '>=', time_start),
                                      ('write_date', '>=', time_start), ('sale_ok', '=', True),
                                      ('la_phi_ship_hang_m2', '!=', True)]
                    if kwargs.get('time_end', ''):
                        if len(kwargs['time_end'].rstrip()) > 10:
                            if datetime.strptime(kwargs['time_end'],
                                                 '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                                kwargs['time_end'], '%d/%m/%Y %H:%M').minute is not None:
                                time_end = datetime.strptime(kwargs['time_end'], '%d/%m/%Y %H:%M') - timedelta(
                                    hours=7)
                        else:
                            time_end = datetime.strptime(kwargs['time_end'] + ' 23:59', '%d/%m/%Y %H:%M') - timedelta(
                                hours=7)

            if not time_end:
                product_obj = request.env['product.product'].sudo().search(product_domain, limit=limit, offset=offset)
                total_product_records = request.env['product.product'].search(product_domain)
            else:
                product_obj = request.env['product.product'].sudo().search(product_domain, limit=limit,
                                                                           offset=offset).filtered(
                    lambda p: p.product_tmpl_id.write_date <= time_end and
                              p.write_date <= time_end)
                total_product_records = request.env['product.product'].search(product_domain).filtered(
                    lambda p: p.product_tmpl_id.write_date <= time_end and
                              p.write_date <= time_end)
            data = {
                'total_records': len(total_product_records),
                'product': self._format_product_data(product_obj)
            }
            return data
        except Exception as e:
            return invalid_response(head='Data Warehouse - Odoo bridge not found!', message=e.args, status=500)
