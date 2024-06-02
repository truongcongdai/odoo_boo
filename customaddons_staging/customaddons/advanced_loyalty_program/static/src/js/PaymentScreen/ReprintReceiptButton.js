odoo.define('point_of_sale.SReprintReceiptButton', function (require) {
    'use strict';

    const { useListener } = require('web.custom_hooks');
    const ReprintReceipt = require('point_of_sale.ReprintReceiptButton');
    const Registries = require('point_of_sale.Registries');

    const SReprintReceiptButton = (ReprintReceipt) => class extends ReprintReceipt {
        constructor() {
            super(...arguments);

        }
        async _onClick() {
            if (!this.props.order) return;
            this.props.order.isReprintBill = true
            super._onClick()

        }

    }
    Registries.Component.extend(ReprintReceipt, SReprintReceiptButton);
    return SReprintReceiptButton;
});
