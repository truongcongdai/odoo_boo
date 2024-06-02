odoo.define('point_of_sale.SInputCustomerList', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ClientListScreen = require('point_of_sale.ClientListScreen');

    class SInputCustomerList extends ClientListScreen {
        constructor() {
            super(...arguments);
        }
        _onChangeSearch(){
        }
    }

    SInputCustomerList.template = 'advanced_pos.SInputCustomerList';
    Registries.Component.add(SInputCustomerList);
    return SInputCustomerList;
});
