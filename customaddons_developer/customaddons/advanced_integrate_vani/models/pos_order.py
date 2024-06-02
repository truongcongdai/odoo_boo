from odoo import models, fields, api
from odoo.http import request, _logger
from datetime import datetime
import pytz
import uuid


class SPosOrderInherit(models.Model):
    _inherit = 'pos.order'
    is_vani_scan_barcode = fields.Boolean(string='Là đơn hàng scan barcode Vani', default=False, store=True,
                                          readonly=True)
    vanila_barcode = fields.Char(string='Vanila Barcode')
    vanila_statement = fields.Char(string='Vanila Statement')
    is_vani_post_transaction = fields.Boolean(string='Vanila kiểm tra đơn hàng có được đẩy transaction qua Vani không')

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(SPosOrderInherit, self)._order_fields(ui_order)
        order_fields['vanila_barcode'] = ui_order.get('vanila_barcode')
        if len(ui_order['statement_ids']) == 1:
            order_fields['vanila_statement'] = ui_order['statement_ids'][0][2]['payment_method_id']
        else:
            order_fields['vanila_statement'] = None
        return order_fields

    def create(self, vals_list):
        res = super(SPosOrderInherit, self).create(vals_list)
        if len(res.lines) > 0:
            # if res.loyalty_points < 0:
            #     try:
            #         refunded_orderline = res.lines.filtered(lambda l: l.refunded_orderline_id)
            #         transactionId = refunded_orderline[0].order_id.id if len(refunded_orderline) > 0 else False
            #         customerId = res.partner_id.id
            #         orgTransactionId = refunded_orderline.refunded_orderline_id.order_id.id
            #         user_tz = self.env.user.tz or pytz.utc
            #         tz = pytz.utc.localize(res.date_order).astimezone(pytz.timezone(user_tz))
            #         transactionTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
            #         cancelType = 'P'
            #         cancelPointAmount = abs(res.loyalty_points)
            #         totalPointAmount = res.partner_id.loyalty_points - abs(res.loyalty_points)
            #         self.env['res.partner'].sudo().post_points_cancellation(transactionId, customerId, orgTransactionId,
            #                                                                 transactionTime, cancelType,
            #                                                                 cancelPointAmount,
            #                                                                 totalPointAmount)
            #     except Exception as e:
            #         _logger.error(e.args)
            #         self.env['ir.logging'].sudo().create({
            #             'name': 'Points cancellation',
            #             'type': 'server',
            #             'dbname': 'boo',
            #             'level': 'ERROR',
            #             'message': str(e),
            #             'path': 'url',
            #             'func': 'post_points_cancellation',
            #             'line': '0',
            #         })
            # else:
                try:
                    check_vani_user = self.env['res.partner'].sudo().search(
                        [('is_connected_vani', '=', True), ('id', '=', res.partner_id.id)], limit=1)
                    if check_vani_user:
                        # transactionId = res.id
                        # customerId = res.partner_id.id
                        if res.vanila_barcode is not False:
                            res.is_vani_scan_barcode = True
                            # pointAmount = res.loyalty_points
                            # totalPointAmount = check_vani_user.loyalty_points + res.loyalty_points
                        else:
                            res.is_vani_scan_barcode = False
                            # pointAmount = 0.0
                            # totalPointAmount = check_vani_user.loyalty_points
                        # isVanilaBarcodeUsed = res.is_vani_scan_barcode
                        # transaction_type = self.env['ir.config_parameter'].sudo().search([(
                        #     'key', '=', 'integrate.transactionType'
                        # )])
                        # transactionType = transaction_type.value
                        # user_tz = self.env.user.tz or pytz.utc
                        # tz = pytz.utc.localize(res.date_order).astimezone(pytz.timezone(user_tz))
                        # transactionTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
                        # brand_id = self.env['ir.config_parameter'].sudo().search([(
                        #     'key', '=', 'integrate.brandId'
                        # )])
                        # brandId = brand_id.value
                        # branch_name = self.env['ir.config_parameter'].sudo().search([(
                        #     'key', '=', 'integrate.shopBrandName'
                        # )])
                        # shopBrandName = branch_name.value
                        # branch = res.pos_name
                        #
                        # if len(res.vanila_statement)>0:
                        #     check_payment_method = self.env['pos.payment.method'].search(
                        #         [('id', '=', res.vanila_statement)])
                        #     if check_payment_method.journal_id.name == 'Cash':
                        #         paymentMethod = 'CASH'
                        #         if check_payment_method.is_cod:
                        #             trafficType = 'ONLINE'
                        #         else:
                        #             trafficType = 'OFFLINE'
                        #     elif check_payment_method.journal_id.name == 'Bank':
                        #         if check_payment_method.is_e_wallet:
                        #             paymentMethod = 'E-WALLET'
                        #         elif check_payment_method.is_card or check_payment_method.payment_method_giftcard:
                        #             paymentMethod = 'CARD'
                        #         else:
                        #             paymentMethod = 'ETC'
                        #         trafficType = 'ONLINE'
                        # else:
                        #     paymentMethod = 'ETC'
                        #     trafficType = 'ONLINE'
                        # productTitle = vals_list['lines'][0][2]['full_product_name']
                        # productAmount = res.amount_total
                        # billAmount = res.amount_total
                        # productPurchaseTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
                        # product_currency = self.env['ir.config_parameter'].sudo().search([(
                        #     'key', '=', 'integrate.productCurrency'
                        # )])
                        # productCurrency = product_currency.value
                        #
                        # self.env['res.partner'].post_points_approval(transactionId, customerId, isVanilaBarcodeUsed,
                        #                                              transactionType,
                        #                                              transactionTime, brandId, shopBrandName, branch,
                        #                                              paymentMethod,
                        #                                              productTitle, productAmount, billAmount,
                        #                                              productPurchaseTime, productCurrency, pointAmount,
                        #                                              totalPointAmount, trafficType)

                    if res.refunded_order_ids:
                        if res.refunded_order_ids[0].is_vani_scan_barcode:
                            res.is_vani_scan_barcode = True
                        else:
                            res.is_vani_scan_barcode = False

                    # if res.is_vani_scan_barcode:
                    if res.partner_id.is_connected_vani and not res.partner_id.vani_pos_config_id:
                        # check_first_order = check_vani_user.pos_order_ids.filtered(
                        #     lambda rec: rec.is_vani_scan_barcode is True)
                        # Tự động điền tên POS vào trường vani_connect_from
                        # if len(check_first_order) == 1:
                        # check_vani_user.vani_connect_from = res.pos_name
                        res.sudo().partner_id.write({
                            # 'vani_connect_from': res.pos_name,
                            'vani_pos_config_id': res.session_id.config_id.id
                        })

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
        return res

    # def refund(self):
    #     res = super(SPosOrderInherit, self).refund()
    #     try:
    #         if self.partner_id and self.is_vani_scan_barcode:
    #             cancel_type = self.env['ir.config_parameter'].sudo().search([(
    #                 'key', '=', 'integrate.cancelType'
    #             )])
    #             user_tz = self.env.user.tz or pytz.utc
    #             tz = pytz.utc.localize(self.date_order).astimezone(pytz.timezone(user_tz))
    #
    #             transactionId = res['res_id']
    #             customerId = self.partner_id.id
    #             orgTransactionId = self.id
    #             transactionTime = datetime.strftime(tz, "%Y-%m-%dT%H:%M:%S%Z:00")
    #             cancelType = cancel_type.value
    #             cancelPointAmount = self.loyalty_points
    #             totalPointAmount = self.partner_id.loyalty_points
    #             self.env['res.partner'].sudo().post_points_cancellation(transactionId, customerId, orgTransactionId,
    #                                                                     transactionTime, cancelType, cancelPointAmount,
    #                                                                     totalPointAmount)
    #     except Exception as e:
    #         _logger.error(e.args)
    #         self.env['ir.logging'].sudo().create({
    #             'name': 'Points cancellation',
    #             'type': 'server',
    #             'dbname': 'boo',
    #             'level': 'ERROR',
    #             'message': str(e),
    #             'path': 'url',
    #             'func': 'post_points_cancellation',
    #             'line': '0',
    #         })
    #     return res
