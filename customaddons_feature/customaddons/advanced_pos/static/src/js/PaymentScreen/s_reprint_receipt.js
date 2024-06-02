odoo.define('advanced_pos.s_reprint_receipt', function (require) {
    'use strict';

    const { useListener } = require('web.custom_hooks');
    const ReprintReceipt = require('point_of_sale.ReprintReceiptButton');
    const Registries = require('point_of_sale.Registries');

    const SReprintBill = (ReprintReceipt) => class extends ReprintReceipt {
        constructor() {
            super(...arguments);

        }
        async _onClick() {
            if (!this.props.order) return;
            //TH in lại bill sẽ truy cập BE để lấy thông tin gift card và số dư
            var gift_card_line = this.props.order.get_orderlines().filter(l => l.product.id === this.env.pos.config.gift_card_product_id[0])
            if (gift_card_line) {
                for (let i = 0; i < gift_card_line.length; i++) {
                    const gift_card = await this.rpc({
                        model: "pos.order.line",
                        method: "get_gift_card_balance_by_order_line_id",
                        args: [0, gift_card_line[i].id],
                    })
                    if (gift_card) {
                        var currency = this.env.pos.currency.name
                        gift_card_line[i].s_product_name = "Gift Card" + " - " + "số dư: " + new Intl.NumberFormat("de-DE").format(gift_card['gift_card_balance']) + ' ' + currency
                    }
                }
            }
            super._onClick()

        }

    }
    Registries.Component.extend(ReprintReceipt, SReprintBill);
    return SReprintBill;
});
