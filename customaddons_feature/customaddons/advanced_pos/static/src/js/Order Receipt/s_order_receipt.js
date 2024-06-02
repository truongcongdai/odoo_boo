odoo.define('advanced_pos.SOrderReceipt', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const OrderReceipt = require('point_of_sale.OrderReceipt');
    var rpc = require('web.rpc');

    const OrderReceiptInherit = (OrderReceipt) => class extends OrderReceipt {
        constructor() {
            super(...arguments);
        }
        get s_receipt_qty() {
            const product_qty = this._receiptEnv.orderlines
            var sum = 0;
            var total_product_positive = 0
            var total_product_minus = 0
            for (let i = 0; i < product_qty.length; i++) {
                if(product_qty[i].product.type === 'product') {
                    if (product_qty[i].quantity < 0) {
                        total_product_minus += product_qty[i].quantity
                    }
                    else {
                        total_product_positive += product_qty[i].quantity
                    }
                }
            }
            sum = total_product_positive + Math.abs(total_product_minus);
            return sum
        }

        get s_receipt_discount_amount() {
            const product_discount = this._receiptEnv.receipt.orderlines
            var amount_name = 0;
            for (let i = 0; i < product_discount.length; i++) {
                if (product_discount[i].price < 0 && !product_discount[i].product_name_wrapped[0].includes('%') ) {
                    amount_name += product_discount[i].price;
                }
            }
            return amount_name;
        }

        get s_receipt_discount_percent() {
            const product_percent = this._receiptEnv.receipt.orderlines
            var percent_name = 0
            for (let i = 0; i < product_percent.length; i++) {
                if (product_percent[i].price < 0 && product_percent[i].product_name_wrapped[0].includes('%') ) {
                    percent_name += product_percent[i].price;
                }
            }
            return percent_name;
        }

        get s_receipt_discount() {
            console.log('test23123')
            const orderlines = this._receiptEnv.receipt.orderlines
            var percent_name = 0
            for (let i = 0; i < orderlines.length; i++) {
                if (orderlines[i].price < 0 && orderlines[i].product_type == 'service' ) {
                    percent_name += orderlines[i].price*orderlines[i].quantity;
                }
            }
            return percent_name;
        }

        get s_subtotal() {
            const product_total = this._receiptEnv.receipt.orderlines
            var subtotal = 0
            for (let i = 0; i < product_total.length; i++) {
                if (product_total[i].product_type == 'product') {
                    subtotal += product_total[i].price_display;
                }
            }
            return subtotal;
        }

        get s_receipt_tax_details(){
            const tax_details = this._receiptEnv.receipt.tax_details
                for (const element of tax_details) {
                    if(element.amount){
                        return tax_details[0].amount
                    }
                }
        }

        s_product_name(line) {
            if (line.product_name === "Gift Card") {
                var gift_card_line = this.receiptEnv.orderlines.filter(l => l.id === line.id)
                if (gift_card_line && gift_card_line.length){
                    var currency = this.env.pos.currency.name
                    if (gift_card_line[0].s_product_name !== undefined){
                        return gift_card_line[0].s_product_name
                    } else if (gift_card_line[0].gift_card_id) {
                        return line.product_name + " - " + "số dư: " + new Intl.NumberFormat("de-DE").format(gift_card_line[0].s_balance_left) + ' ' + currency
                    } else {
                        return line.product_name
                    }
                } else {
                    return line.product_name
                }
            } else {
                return line.product_name
            }
        }

        get s_sale_person(){
            const sale_person_id = this.env.pos.sale_person_id
            if (sale_person_id){
                return this.env.pos.employee_by_id[sale_person_id].name
            } else if (this.receipt.name && this._receiptEnv.order.state) {
                rpc.query({
                    model: 'pos.order',
                    method: 'search_order',
                    args: [1,this.receipt.name],
                }).then(function (context) {
                    document.getElementById('sale-person').innerText = ''
                    if (context['sale_person']) {
                        document.getElementById('sale-person').innerText = context['sale_person']
                    }
                });
            } else {
                return ""
            }
        }

        get s_date_order() {
            rpc.query({
                model: 'pos.order',
                method: 'search_order',
                args: [1,this.receipt.name],
            }).then(function (context) {
                if (context['date_order']) {
                    var dateOrder = document.getElementById('date-order')
                    if (dateOrder){
                        document.getElementById('date-order').innerText = context['date_order']
                    }
                }
            });
        }

        get s_is_free_product(){
            var is_free_product =[]
            const orderlines = this._receiptEnv.orderlines
            const orderlines_receipt = this._receiptEnv.receipt.orderlines
            for (let i = 0; i < orderlines.length; i++) {
                // orderlines[i].is_program_reward === true
                if (typeof(orderlines[i].program_id) !== 'undefined') {
                    var programs = this.env.pos.coupon_programs_by_id[orderlines[i].program_id]
                    if (programs){
                        if (programs.reward_type === "product"){
                            for (let j = 0; j < orderlines_receipt.length; j++) {
                                if (orderlines[i].id === orderlines_receipt[j].id){
                                    is_free_product.push(orderlines_receipt[j])
                                }
                            }
                        }
                    }
                }
            }
            if (!is_free_product.length){
                ///Trường hợp in lại bill
                for (let j = 0; j < orderlines_receipt.length; j++) {
                    if (orderlines_receipt[j].is_gift_free_product === true || orderlines_receipt[j].s_free_product_id){
                        is_free_product.push(orderlines_receipt[j])
                    }
                }
            }
            return is_free_product
        }

    };
    Registries.Component.extend(OrderReceipt, OrderReceiptInherit);
    return OrderReceipt;
});
