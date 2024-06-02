odoo.define('advanced_pos.BooTicketButton', function (require) {
    'use strict';
    const {useListener} = require("web.custom_hooks");
    const Registries = require('point_of_sale.Registries');
    const TicketButton = require('point_of_sale.TicketButton');
    const { posbus } = require('point_of_sale.utils');
    const BooTicketButton = (TicketButton) => class extends TicketButton {
        constructor() {
            super(...arguments);
        }
        boo_onclick() {
            if (this.props.isTicketScreenShown) {
                posbus.trigger('ticket-button-clicked');
            } else {
                var product_item_dialog = $(".search-bar-portal .s_search_product_item_dialog")
                if (product_item_dialog.length > 0) {
                    product_item_dialog.remove();
                }
                this.showScreen('TicketScreen');
            }
        }
    }
    Registries.Component.extend(TicketButton, BooTicketButton)
    return BooTicketButton
})
