odoo.define('advanced_pos.NumpadWidget', function(require) {
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const Registries = require('point_of_sale.Registries');

    const SNumpadWidget = NumpadWidget => class extends NumpadWidget {
        get hasPriceControlRights() {
            const cashier = this.env.pos.get('cashier') || this.env.pos.get_cashier();
            if (this.env.pos.config.is_create_customer_control) {
                const btnCreateCustomer = $('.new-customer')
                if (btnCreateCustomer.length > 0) {
                    if(cashier.role != 'manager') {
                        btnCreateCustomer.hide();
                    } else {
                        btnCreateCustomer.show();
                    }
                }
            }
            return super.hasPriceControlRights;
        }
    };

    Registries.Component.extend(NumpadWidget, SNumpadWidget);

    return SNumpadWidget;
 });