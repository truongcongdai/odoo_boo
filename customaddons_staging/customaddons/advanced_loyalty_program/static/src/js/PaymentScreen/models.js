odoo.define('advanced_loyalty_program.s_model_loyalty_program', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    const {Gui} = require('point_of_sale.Gui');
    var super_order_model = models.Order.prototype;
    models.Order = models.Order.extend({
        export_for_printing: function () {
            const result = super_order_model.export_for_printing.apply(this, arguments);
            if (this.get_client()) {
                var currency = this.pos.currency.name
                if (this.isReprintBill){
                    result.total_period_revenue = new Intl.NumberFormat("de-DE").format(this.get_client().total_period_revenue).replace(/\./g, ',') + ' ' + currency
                    result.customer_loyalty = new Intl.NumberFormat("de-DE").format(this.get_client().loyalty_points).replace(/\./g, ',')
                    this.isReprintBill = false
                }else {
                    result.total_period_revenue = new Intl.NumberFormat("de-DE").format(this.get_client().total_period_revenue + this.get_total_with_tax()).replace(/\./g, ',') + ' ' + currency
                    result.customer_loyalty = new Intl.NumberFormat("de-DE").format(this.get_client().loyalty_points + (this.get_won_points() - this.get_spent_points())).replace(/\./g, ',')
                }

            } else {
                result.total_period_revenue = ''
                result.customer_loyalty = ''
            }
            return result;
        },
    });
    var super_pos_model = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        _save_to_server: function (orders, options) {
            if (!orders || !orders.length) {
                return Promise.resolve([]);
            }
            for (let i = 0; i < orders.length; i++) {
                if (orders[i].data){
                    if (this.env.pos.loyalty){
                        orders[i].data.apply_loyalty_program = true
                    }
                }
            }
            if ($(".back").hasClass('button back')) {
                $(".back").addClass("disable-btn");
            }
            return super_pos_model._save_to_server.apply(this, arguments);
        },
    });
})