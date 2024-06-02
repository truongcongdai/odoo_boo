odoo.define('advanced_pos.SActionpadWidget', function (require) {
    'use strict';
    const {useListener} = require("web.custom_hooks");
    const Registries = require('point_of_sale.Registries');
    const ActionpadWidget = require('point_of_sale.ActionpadWidget');
    const SActionpadWidget = (ActionpadWidget) => class extends ActionpadWidget {
        constructor() {
            super(...arguments);
        }

        // remove product list when click button pay
        async _onClickPayRemoveProductList() {
            var product_item_dialog = $(".search-bar-portal .s_search_product_item_dialog")
            if (product_item_dialog.length > 0) {
                product_item_dialog.remove();
            }
        }

        get client() {
            let client = super.client;
            if (client) {
                if (client.total_period_revenue) {
                    client.s_separate_total_period_revenue = client.total_period_revenue.toLocaleString('vi-VN');
                }
                if (client.loyalty_points) {
                    let loyalty_points = Number(client.loyalty_points);
                    if (!isNaN(loyalty_points)) {
                        client.s_separate_loyalty_points = parseFloat(loyalty_points.toFixed(1)).toLocaleString('vi-VN');
                    }
                }
            }
            return client;
        }
    }
    Registries.Component.extend(ActionpadWidget, SActionpadWidget)
    return SActionpadWidget
})