odoo.define("advanced_pos.SSaleOrderRow", function (require) {
    "use strict";

    const SaleOrderRow = require('pos_sale.SaleOrderRow');
    const Registries = require('point_of_sale.Registries');

    const SSaleOrderRow = (SaleOrderRow) => class extends SaleOrderRow {
        get date_custom() {
            return moment(this.order.date_order).add(7, "h").format('YYYY-MM-DD hh:mm A');
        }
    }

    Registries.Component.extend(SaleOrderRow, SSaleOrderRow)
    return SSaleOrderRow
});
