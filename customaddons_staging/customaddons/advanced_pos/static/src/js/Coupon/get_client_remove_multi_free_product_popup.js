odoo.define("advanced_pos.SClientRemoveMultiFreeProduct", function (require) {
    "use strict";

    const {useState, useRef, onPatched, useComponent} = owl.hooks;
    const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
    const Registries = require("point_of_sale.Registries");
    const {useListener} = require("web.custom_hooks");
    var rpc = require('web.rpc');
    const {Gui} = require('point_of_sale.Gui');

    class SClientRemoveMultiFreeProduct extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }

        // return the quantity of product
        confirmRemoveMultiFreeProduct() {
            const orderlines = this.props.order.orderlines;
            if (orderlines) {
                orderlines.remove(orderlines.filter((line) => line.product.s_free_product_id));
            }
            this.props.order.assert_editable();
            this.props.order.resetProgramsContext=true
            this.props.order.set('client', this.props.client);
            this.confirm();
        }

        cancelRemoveMultiFreeProduct() {
            this.cancel();
            return false;
        }
    }

    SClientRemoveMultiFreeProduct.template = "SClientRemoveMultiFreeProduct";

    Registries.Component.add(SClientRemoveMultiFreeProduct);

    return SClientRemoveMultiFreeProduct;
});
