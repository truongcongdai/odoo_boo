odoo.define('advanced_pos.SalePersonButton', function (require) {
    'use strict';
    const {useState, useRef, onPatched, useComponent} = owl.hooks;
    const Registries = require("point_of_sale.Registries");
    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const {useListener} = require("web.custom_hooks");
    const models = require('point_of_sale.models');
    models.load_fields('pos.order', ['sale_person_id', 'is_bag']);
    const SalePersonButton = (PaymentScreen) => class extends PaymentScreen {
        constructor() {
            super(...arguments);
            useListener('sale-person-button', this.onClickSalePerson);
            useListener('is_bag', this.onChangeCheckBoxIsBag);
            useListener('is_bill', this.onChangeCheckBoxIsBill);
        }

        async onChangeCheckBoxIsBill() {
            const is_bill = document.getElementById('is_bill');
            if (is_bill.checked) {
                this.env.pos.is_bill = true;
            } else {
                this.env.pos.is_bill = false;
            }
        }

        async onChangeCheckBoxIsBag(event) {
            const is_bag = document.getElementById('is_bag');
            if (is_bag.checked) {
                this.env.pos.is_bag = true;
            } else {
                this.env.pos.is_bag = false;
            }
        }

        async validateOrder(isForceValidate) {
            for (var i = 0; i < this.currentOrder.orderlines.models.length; i++) {
                var line = this.currentOrder.orderlines.models[i];
                var qty_available = await this.rpc({
                    model: 'product.product',
                    method: 'get_product_quantities',
                    args: [this.currentOrder.orderlines.models[i].product.id, this.env.pos.picking_type.id],
                    kwargs: {context: this.env.session.user_context},
                });
                if (line.product.type === 'product' && line.quantity > qty_available) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t("Lỗi người dùng"), body: this.env._t("Sản phẩm trong kho không đủ."),
                    });
                    return;
                }
                if (typeof (line.coupon_id) !== "undefined") {
                    var coupon_is_used = await this.rpc({
                        model: 'coupon.coupon',
                        method: 'check_coupon_is_used',
                        args: [line.coupon_id],
                        kwargs: {context: this.env.session.user_context},
                    });
                    if (!coupon_is_used[0]) {
                        var popup_text = "Coupon " + coupon_is_used[1] + " đã được sử dụng"
                        this.showPopup('ErrorPopup', {
                            title: this.env._t("Lỗi người dùng"), body: this.env._t(popup_text),
                        });
                        return;
                    }
                }
                if (line.sale_order_line_id && line.sale_order_line_id.id) {
                    const saleOrder = await this.rpc({
                        model: 'sale.order.line',
                        method: 'check_return_sale_order_line',
                        args: [line.sale_order_line_id.id],
                        kwargs: {context: this.env.session.user_context},
                    });
                    if (saleOrder) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t("Lỗi người dùng"),
                            body: this.env._t("Đơn hàng đã được hoàn trả tại đơn hàng Ecommerce."),
                        });
                        return;
                    }
                }

            }

            if (!this.env.pos.get_client()) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'), body: this.env._t("Đơn hàng chưa có khách hàng."),
                });
                return;
            } else if ($('.selected_sale_person').text() == '') {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'), body: this.env._t("Đơn hàng chưa có nhân viên bán hàng."),
                });
                return;
            } else {
                if ($(".next").hasClass("highlight")) {
                    $(".next").addClass("disable-btn");
                }
            }
            super.validateOrder()
        }

        //show popup select sale person
        async onClickSalePerson() {
            this.showPopup("SalePersonPopup", {});
        }

        async _finalizeValidation() {
            //insert nhan vien ban hang vao order
            this.currentOrder.sale_person_id = this.env.pos.sale_person_id
            this.currentOrder.is_bag = this.env.pos.is_bag ? this.env.pos.is_bag : document.getElementById('is_bag').checked;
            if (document.getElementById('is_bill')) {
                this.currentOrder.is_bill = this.env.pos.is_bill ? this.env.pos.is_bill : document.getElementById('is_bill').checked;
            }
            super._finalizeValidation()
        }

    }
    SalePersonButton.template = 'SalePersonButton';
    Registries.Component.extend(PaymentScreen, SalePersonButton)
    return SalePersonButton
})