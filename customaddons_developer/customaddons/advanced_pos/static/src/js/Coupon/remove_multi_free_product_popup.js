odoo.define("advanced_pos.RemoveMultiFreeProduct", function (require) {
    "use strict";

    const {useState, useRef, onPatched, useComponent} = owl.hooks;
    const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
    const Registries = require("point_of_sale.Registries");
    const {useListener} = require("web.custom_hooks");
    var rpc = require('web.rpc');
    const {Gui} = require('point_of_sale.Gui');

    class RemoveMultiFreeProduct extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }

        // return the quantity of product
        confirmMultiFreeProductRewardLines() {
            const orderlines = this.props.order.orderlines;
            for (var i = 0; orderlines.models.length > i; i++) {
                if (orderlines.models[i].product.s_free_product_id) {
                    if (orderlines.models[i].coupon_id) {
                        const coupon_code = Object.values(orderlines.models[i].order.bookedCouponCodes).find(
                            (couponCode) => couponCode.coupon_id === orderlines.models[i].coupon_id
                        ).code;
                        delete orderlines.models[i].order.bookedCouponCodes[coupon_code];
                        orderlines.models[i].order.trigger('reset-coupons', [orderlines.models[i].coupon_id]);
                        this.showNotification(`Coupon (${coupon_code}) has been deactivated.`);
                    } else if (typeof orderlines.models[i].program_id != 'undefined') {
                        // remove program from active programs
                        const index = orderlines.models[i].order.activePromoProgramIds.indexOf(orderlines.models[i].program_id);
                        orderlines.models[i].order.activePromoProgramIds.splice(index, 1);
                        this.showNotification(
                            `'${
                                this.env.pos.coupon_programs_by_id[orderlines.models[i].program_id].name
                            }' program has been deactivated.`
                        );
                    }
                    let multiFreeProduct = orderlines.filter((line) => line.product.s_free_product_id);
                    if (multiFreeProduct) {
                        orderlines.remove(multiFreeProduct)
                        this.props.order.trigger('update-rewards');
                    }


                    // this.props.order.activeMultiFreeProducts=true
                }
            }
            this.props.line.set_quantity(this.props.quantity)
            this.confirm();
            return true;
        }

        cancelMultiFreeProductRewardLines() {
            this.cancel();
            return false;
        }
    }

    RemoveMultiFreeProduct.template = "RemoveMultiFreeProduct";

    Registries.Component.add(RemoveMultiFreeProduct);

    return RemoveMultiFreeProduct;
});
