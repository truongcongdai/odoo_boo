odoo.define("pos_gift_card.SalePersonPopup", function (require) {
    "use strict";

    const {useState, useRef, onPatched, useComponent} = owl.hooks;
    const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
    const Registries = require("point_of_sale.Registries");
    const {useListener} = require("web.custom_hooks");

    class SalePersonPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            useListener('selection-sale-person', this.selectSalePerson);
        }

        async selectSalePerson(salePerson) {
            this.env.pos.sale_person_id = salePerson.id
            $('.selected_sale_person').text(salePerson.name);
            $('.sale-person-button').find('.button').addClass('highlight');
            this.confirm();
        }
    }

    SalePersonPopup.template = "SalePersonPopup";

    Registries.Component.add(SalePersonPopup);

    return SalePersonPopup;
});
