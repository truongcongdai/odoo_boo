odoo.define('advanced_pos.pos_create_invoice', function (require) {
"use strict";

var models = require('point_of_sale.models');
var posmodel_super = models.PosModel.prototype;

models.PosModel = models.PosModel.extend({
    push_single_order: async function(order, opts) {
        order.to_invoice = true
        return posmodel_super.push_single_order.apply(this, arguments)
        },
    });

});