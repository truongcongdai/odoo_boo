odoo.define('advanced_pos.SOrderLine', function (require) {
    'use strict';
    const Registries = require("point_of_sale.Registries");
    const OrderLine = require("point_of_sale.Orderline");
    var rpc = require('web.rpc');
    const SOrderLine = (OrderLine) => class extends OrderLine {
        constructor() {
            super(...arguments);
            this.checkLineQty();
        }

        // Check available quantity order line
        async checkLineQty() {
            var self = this
            var qty_available = await this.rpc({
                model: 'product.product',
                method: 'get_product_quantities',
                args: [this.props.line.product.id, this.env.pos.picking_type.id],
                kwargs: {context: this.env.session.user_context},
            });
            if (this.props.line.product.type == 'service') { // is copon
                qty_available = 1;
            }
            if (qty_available <= this.props.line.quantity && this.props.line.product.type == 'product') {
                this.props.line.set_quantity(qty_available);
            }
        }

        //tang so luong san pham
        async incrementValue(e) {
            e.preventDefault();
            var fieldName = this.props.line.id;
            var parent = $(e.target).closest('div');
            var currentVal = parseInt(parent.find('input[name=' + fieldName + ']').val(), 10);
            var self = this
            // DungNH: check trường hợp trả đơn online
            if (typeof (this.props.line.sale_order_line_id) !== "undefined") {
                let new_qty = this.props.line.quantity + 1
                if (new_qty >= 0){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t("Lỗi người dùng"),
                        body: this.env._t("Số lượng bị sai."),
                    });
                    return;
                }
            }
            var qty_available = await this.rpc({
                model: 'product.product',
                method: 'get_product_quantities',
                args: [this.props.line.product.id,this.env.pos.picking_type.id],
                kwargs: {context: this.env.session.user_context},
            });
            var product_type = this.props.line.product.type;
            if (product_type != 'service' && product_type != 'product') {
                if (!isNaN(currentVal)) {
                    parent.find('input[name=' + fieldName + ']').val(currentVal + 1);
                    this.props.line.set_quantity(this.props.line.quantity + 1);
                } else {
                    parent.find('input[name=' + fieldName + ']').val(0);
                }
            }
            if (product_type == 'service') { // is copon
                qty_available = 1;
            }
            if (qty_available >= this.props.line.quantity + 1) {
                this.props.line.isUnavailableQty = false
                if (!isNaN(currentVal)) {
                    //Khong cho tang so luong don hoan
                    if ((!isNaN(currentVal) && currentVal < 0) && this.props.line.refunded_orderline_id){
                        this.props.line.set_quantity(this.props.line.quantity)
                    }
                    // else if ((!isNaN(currentVal) && currentVal === 0) && this.props.line.refunded_orderline_id && product_type == 'product'){
                    //     this.props.line.set_quantity(0)
                    // }
                    // //Neu la coupon/CTKM/giftcard don hoan khong cho tang so luong
                    // else if ((!isNaN(currentVal) && currentVal < 0) && this.props.line.refunded_orderline_id && product_type != 'product' && this.props.line.price < 0){
                    //     this.props.line.set_quantity(this.props.line.quantity)
                    // }
                    else {
                        parent.find('input[name=' + fieldName + ']').val(currentVal + 1);
                        this.props.line.set_quantity(this.props.line.quantity + 1);
                    }
                } else {
                    parent.find('input[name=' + fieldName + ']').val(0);
                }
            } else if (product_type == 'product') {
                this.props.line.isUnavailableQty = true
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Lỗi người dùng"),
                    body: this.env._t("Sản phẩm trong kho không đủ."),
                });
            }
            this.env.pos.get_order().trigger('update-rewards');
        }

        //giam so luong san pham
        decrementValue(e) {
            e.preventDefault();
            var fieldName = this.props.line.id;
            var parent = $(e.target).closest('div');
            var product_type = this.props.line.product.type;
            var currentVal = parseInt(parent.find('input[name=' + fieldName + ']').val(), 10);
            // var product_type = this.props.line.product.type;
            // DungNH: check trường hợp trả đơn online
            if (typeof (this.props.line.sale_order_line_id) !== "undefined") {
                let new_qty = Math.abs(this.props.line.quantity - 1)
                let qty_delivered = this.props.line.sale_order_line_id.qty_delivered
                if (new_qty > qty_delivered && product_type === 'product'){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t("Lỗi người dùng"),
                        body: this.env._t("Số lượng không thể vượt quá số lượng đã giao."),
                    });
                    return;
                }
            }
            if (!isNaN(currentVal) && currentVal > 0) {
                //set lai quantity cua order line
                const set_quantity = this.props.line.set_quantity(this.props.line.quantity - 1);
                if (set_quantity) {
                    if (this.props.line.quantity == 0) {
                        this.props.line.set_quantity('remove');
                        // this.props.line.order.remove_orderline(this.props.line);
                    } else {
                        parent.find('input[name=' + fieldName + ']').val(currentVal - 1);
                    }
                }
            }
            //Khong cho giam so luong don hoan
            else if ((!isNaN(currentVal) && currentVal <= 0) && this.props.line.refunded_orderline_id) {
                this.props.line.set_quantity(this.props.line.quantity)
            }
            // //Neu la coupon/CTKM/giftcard don hoan khong cho giam so luong
            // else if ((!isNaN(currentVal) && currentVal < 0) && this.props.line.refunded_orderline_id && product_type != 'product' && this.props.line.price < 0){
            //     this.props.line.set_quantity(this.props.line.quantity)
            // }
            else {
                if (this.props.line.quantity == 1) {
                    this.props.line.set_quantity('remove');
                } else {
                    parent.find('input[name=' + fieldName + ']').val(0);
                }
            }
            this.env.pos.get_order().trigger('update-rewards');
        }

    }
    Registries.Component.extend(OrderLine, SOrderLine)
    return SOrderLine
})