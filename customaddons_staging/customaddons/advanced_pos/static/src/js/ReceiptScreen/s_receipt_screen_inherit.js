odoo.define('advanced_pos.ReceiptScreen', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ReceiptScreen = require('point_of_sale.ReceiptScreen');

    const ReceiptScreenInherit = (ReceiptScreen) => class extends ReceiptScreen {
        constructor() {
            super(...arguments);
        }

        async handleAutoPrint() {
            const is_bill = this.env.pos.is_bill ? this.env.pos.is_bill : false
            if (this._shouldAutoPrint() && !is_bill && this.env.pos.attributes.selectedClient) {
                await this.printReceipt();
                if (this.currentOrder._printed && this._shouldCloseImmediately()) {
                    this.whenClosing();
                }
            }
        }
    };
    Registries.Component.extend(ReceiptScreen, ReceiptScreenInherit);
    return ReceiptScreen;
});
