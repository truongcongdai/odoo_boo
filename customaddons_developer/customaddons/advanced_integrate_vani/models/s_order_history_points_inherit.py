from odoo import models, fields, api
from odoo.http import request, _logger
from datetime import datetime
import pytz


class SOrderHistoryPoints(models.Model):
    _inherit = 's.order.history.points'
    _order = "create_date desc"

    def create(self, vals_list):
        res = super(SOrderHistoryPoints, self).create(vals_list)
        order_id = None
        if res.sale_order_id:
            order_id = res.sale_order_id
        elif res.order_id:
            order_id = res.order_id
        if order_id and not res.is_bill:
            if order_id.partner_id.is_connected_vani:
                if res.diem_cong < 0:
                    try:
                        if res.sale_order_id:
                            is_post_transaction = False
                            refunded_orderline = order_id.order_line.filtered(lambda l: l.refunded_orderline_id)
                            if len(refunded_orderline) > 0:
                                if refunded_orderline[0].refunded_orderline_id.order_id.is_vani_post_transaction:
                                    is_post_transaction = True
                            if is_post_transaction:
                                # refund va mua sp
                                refund_order = order_id.order_line.filtered(
                                    lambda l: l.product_uom_qty > 0 and l.product_id.detailed_type == 'product')
                                if len(refund_order) > 0:
                                    cancelType = 'P'
                                else:
                                    cancelType = 'T'
                                transactionId = order_id.id
                                customerId = order_id.partner_id.id
                                if refunded_orderline:
                                    orgTransactionId = refunded_orderline[0].refunded_orderline_id.order_id.id
                                else:
                                    orgTransactionId = order_id.id
                                user_tz = self.env.user.tz or pytz.utc
                                tz = pytz.utc.localize(datetime.now()).astimezone(pytz.timezone(user_tz))
                                transactionTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
                                # cancelType = 'P'
                                cancelPointAmount = abs(res.diem_cong)
                                totalPointAmount = order_id.partner_id.loyalty_points - abs(res.diem_cong)
                                self.env['res.partner'].sudo().post_points_cancellation(transactionId, customerId,
                                                                                        orgTransactionId,
                                                                                        transactionTime, cancelType,
                                                                                        cancelPointAmount,
                                                                                        totalPointAmount)
                        elif res.order_id:
                            is_post_transaction = False
                            refunded_orderline = order_id.lines.filtered(
                                lambda l: l.refunded_orderline_id or l.sale_order_origin_id)
                            if len(refunded_orderline) > 0:
                                if res.order_id.refunded_order_ids:
                                    if res.order_id.refunded_order_ids[0].is_vani_post_transaction:
                                        is_post_transaction = True
                                elif refunded_orderline[0].sale_order_origin_id:
                                    if refunded_orderline[0].sale_order_origin_id.is_vani_post_transaction:
                                        is_post_transaction = True
                                if is_post_transaction:
                                    transactionId = order_id.id
                                    customerId = order_id.partner_id.id
                                    if refunded_orderline[0].sale_order_origin_id:
                                        orgTransactionId = refunded_orderline[0].sale_order_origin_id.id
                                    else:
                                        orgTransactionId = refunded_orderline[0].refunded_orderline_id.order_id.id
                                    user_tz = self.env.user.tz or pytz.utc
                                    tz = pytz.utc.localize(order_id.date_order).astimezone(pytz.timezone(user_tz))
                                    transactionTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
                                    # refund va mua sp
                                    refund_order = sum(order_id.lines.filtered(
                                        lambda l: l.qty < 0 and l.product_id.detailed_type == 'product').mapped('qty'))
                                    if order_id.refunded_order_ids:
                                        refunded_order = sum(order_id.refunded_order_ids[0].lines.filtered(
                                            lambda l: l.qty > 0 and l.product_id.detailed_type == 'product').mapped('qty'))
                                    else:
                                        refunded_order = sum(refunded_orderline[0].sale_order_origin_id.order_line.filtered(
                                            lambda l: l.product_uom_qty > 0 and l.product_id.detailed_type == 'product').mapped('product_uom_qty'))
                                    if abs(refund_order) != abs(refunded_order):
                                        cancelType = 'P'
                                    else:
                                        cancelType = 'T'
                                    cancelPointAmount = abs(res.diem_cong)
                                    totalPointAmount = order_id.partner_id.loyalty_points - abs(res.diem_cong)
                                    self.env['res.partner'].sudo().post_points_cancellation(transactionId, customerId,
                                                                                            orgTransactionId,
                                                                                            transactionTime, cancelType,
                                                                                            cancelPointAmount,
                                                                                            totalPointAmount)

                    except Exception as e:
                        _logger.error(e.args)
                        self.env['ir.logging'].sudo().create({
                            'name': 'Points cancellation',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'message': str(e),
                            'path': 'url',
                            'func': 'post_points_cancellation',
                            'line': '0',
                        })
                else:
                    try:
                        check_vani_user = self.env['res.partner'].sudo().search(
                            [('is_connected_vani', '=', True), ('id', '=', order_id.partner_id.id)], limit=1)
                        if order_id.partner_id:
                            order_id.is_vani_post_transaction = True
                            transactionId = order_id.id
                            customerId = order_id.partner_id.id
                            if res.sale_order_id:
                                pointAmount = res.sale_order_id.loyalty_points
                                totalPointAmount = order_id.partner_id.loyalty_points
                                # if res.invoice_id:
                                #     pointAmount = res.invoice_id.loyalty_points
                            else:
                                pointAmount = order_id.loyalty_points
                                totalPointAmount = order_id.partner_id.loyalty_points + order_id.loyalty_points
                            isVanilaBarcodeUsed = False
                            if res.sale_order_id:
                                order_id.is_vani_scan_barcode = True
                                isVanilaBarcodeUsed = True
                            if res.order_id.vanila_barcode:
                                isVanilaBarcodeUsed = True
                            transaction_type = self.env['ir.config_parameter'].sudo().search([(
                                'key', '=', 'integrate.transactionType'
                            )])
                            transactionType = transaction_type.value
                            user_tz = self.env.user.tz or pytz.utc
                            if res.sale_order_id:
                                productPurchaseTime_tz = pytz.utc.localize(res.sale_order_id.create_date).astimezone(
                                    pytz.timezone(user_tz))
                                productPurchaseTime = datetime.strftime(productPurchaseTime_tz,
                                                                        "%Y-%m-%dT%H:%M:%S%Z:00")
                                if res.sale_order_id.is_magento_order and res.sale_order_id.write_date:
                                    tz = pytz.utc.localize(res.sale_order_id.write_date).astimezone(
                                        pytz.timezone(user_tz))
                                else:
                                    tz = pytz.utc.localize(res.sale_order_id.date_order).astimezone(
                                        pytz.timezone(user_tz))
                            else:
                                tz = pytz.utc.localize(order_id.date_order).astimezone(pytz.timezone(user_tz))
                                productPurchaseTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
                            transactionTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
                            brand_id = self.env['ir.config_parameter'].sudo().search([(
                                'key', '=', 'integrate.brandId'
                            )])
                            brandId = brand_id.value
                            branch_name = self.env['ir.config_parameter'].sudo().search([(
                                'key', '=', 'integrate.shopBrandName'
                            )])
                            shopBrandName = branch_name.value
                            branch = order_id.pos_name
                            paymentMethod = None
                            if res.sale_order_id:
                                if res.sale_order_id.payment_method == 'cod':
                                    paymentMethod = 'CASH'
                                    trafficType = 'ONLINE'
                                else:
                                    paymentMethod = 'E-WALLET'
                                    trafficType = 'ONLINE'
                            else:
                                if order_id.vanila_statement:
                                    check_payment_method = self.env['pos.payment.method'].search(
                                        [('id', '=', int(order_id.vanila_statement))])
                                    if check_payment_method.journal_id.name == 'Cash':
                                        paymentMethod = 'CASH'
                                        # if check_payment_method.is_cod:
                                        # trafficType = 'ONLINE'
                                        # else:
                                        # trafficType = 'OFFLINE'
                                    elif check_payment_method.journal_id.name == 'Bank':
                                        if check_payment_method.is_e_wallet:
                                            paymentMethod = 'E-WALLET'
                                        elif check_payment_method.is_card or check_payment_method.payment_method_giftcard:
                                            paymentMethod = 'CARD'
                                        else:
                                            paymentMethod = 'ETC'
                                        # trafficType = 'ONLINE'
                                else:
                                    paymentMethod = 'ETC'
                                trafficType = 'OFFLINE'
                            if res.sale_order_id:
                                productTitle = res.sale_order_id.order_line[0].product_id.name
                            else:
                                product_title_lines = res.order_id.lines.filtered(lambda l: l.qty > 0)
                                if len(product_title_lines) > 0:
                                    productTitle = product_title_lines[0]['full_product_name']
                                else:
                                    productTitle = res.order_id.lines[0]['full_product_name']
                            if res.sale_order_id:
                                productAmount = 0
                                billAmount = 0
                                if res.sale_order_id.order_line:
                                    # productAmount = sum(order_id.order_line.filtered(lambda l: l.product_id and l.product_id.detailed_type == 'product').mapped('price_total'))
                                    for line in res.sale_order_id.order_line:
                                        if line.qty_delivered > 0:
                                            productAmount += line.qty_delivered * line.price_unit
                                            billAmount += line.price_total

                                # if res.invoice_id:
                                #     if res.invoice_id.invoice_line_ids:
                                #         for invoice_line in res.invoice_id.invoice_line_ids:
                                #             if invoice_line.product_id and invoice_line.product_id.detailed_type=='product':
                                #                 if invoice_line.sale_line_ids:
                                #                     for line in invoice_line.sale_line_ids:
                                #                         productAmount+= invoice_line.quantity*line.s_lst_price
                                # billAmount = res.amount_total
                                # if invoice.id == res.invoice_id.id:
                                # for invoice in res.sale_order_id.invoice_ids:
                                #     if invoice.id ==res.invoice_id.id:
                                #         sale_order_line = res.sale_order_id
                                # if res.invoice_id:
                                #     productAmount = sum(res.invoice_id.invoice_line_ids.filtered(lambda l: l.product_id and l.product_id.detailed_type == 'product').mapped('price_subtotal'))
                                #     if res.invoice_id.invoice_line_ids:
                                #         for
                            else:
                                productAmount = sum(order_id.lines.filtered(
                                    lambda l: l.product_id and l.product_id.detailed_type == 'product').mapped(
                                    'price_subtotal_incl'))
                                billAmount = order_id.amount_total
                            product_currency = self.env['ir.config_parameter'].sudo().search([(
                                'key', '=', 'integrate.productCurrency'
                            )])
                            productCurrency = product_currency.value
                            vaniCouponNumber = None
                            if res.sale_order_id:
                                if res.sale_order_id.coupon_code:
                                    coupon_number = res.sale_order_id.coupon_code 	#'Vani_171,88866666'
                                    if len(coupon_number):
                                        for coupon in coupon_number.split(','):
                                            program = self.env['coupon.coupon'].sudo().search([('boo_code', '=', coupon)])
                                            if len(program) > 0:
                                                if program.program_id.is_vani_coupon_program:
                                                    vaniCouponNumber = coupon
                                                    break
                                else:
                                    if res.sale_order_id.s_promo_code:
                                        coupon_number = res.sale_order_id.s_promo_code
                                        if len(coupon_number) > 0:
                                            for coupon in coupon_number.split(','):
                                                program = self.env['coupon.program'].sudo().search([('ma_ctkm', '=', coupon)])
                                                if len(program) > 0:
                                                    if program.is_vani_coupon_program:
                                                        vaniCouponNumber = coupon
                                                        break

                            else:
                                coupon_number = res.order_id.lines.filtered(lambda l: l.coupon_id)
                                if len(coupon_number) > 0:
                                    for coupon in coupon_number:
                                        program = self.env['coupon.program'].sudo().search([('id', '=', coupon.program_id.id)], limit=1).is_vani_coupon_program
                                        if program:
                                            vaniCouponNumber = coupon.coupon_id.boo_code
                                            break
                                else:
                                    coupon_number = res.order_id.lines.filtered(lambda l: l.program_id)
                                    if len(coupon_number) > 0:
                                        for coupon in coupon_number:
                                            program = self.env['coupon.program'].sudo().search([('id', '=', coupon.program_id.id)], limit=1).is_vani_coupon_program
                                            if program:
                                                vaniCouponNumber = coupon.program_id.promo_code
                                                break

                            self.env['res.partner'].post_points_approval(transactionId, customerId, isVanilaBarcodeUsed,
                                                                         transactionType,
                                                                         transactionTime, brandId, shopBrandName,
                                                                         branch,
                                                                         paymentMethod,
                                                                         productTitle, productAmount, billAmount,
                                                                         productPurchaseTime, productCurrency,
                                                                         pointAmount,
                                                                         totalPointAmount, trafficType, vaniCouponNumber)
                    except Exception as e:
                        _logger.error(e.args)
                        self.env['ir.logging'].sudo().create({
                            'name': 'Points approval',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'ERROR',
                            'message': str(e),
                            'path': 'url',
                            'func': 'post_points_approval',
                            'line': '0',
                        })
            return order_id
