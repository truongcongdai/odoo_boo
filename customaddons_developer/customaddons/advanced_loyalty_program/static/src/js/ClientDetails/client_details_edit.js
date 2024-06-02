odoo.define('advanced_pos.s_partner_loyalty_pos', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');
    const Registries = require("point_of_sale.Registries");
    models.load_fields('res.partner', ['total_period_revenue', 'total_reality_revenue', 'loyalty_points','s_separate_loyalty_points', 'total_invoiced', 'total_sales_amount']);
    const SPartnerLoyaltyPos = (ClientDetailsEdit) => class extends ClientDetailsEdit {
        constructor() {
            super(...arguments);
            // const partner = this.props.partner;
            // this.changes = {
            //     'country_id': partner.country_id && partner.country_id[0],
            //     'state_id': null,
            // };
        }
        get _fomatTotalInvoiced() {
            var total_sales_amount = this.props.partner.total_sales_amount;
            var currency = this.env.pos.currency.name
            return new Intl.NumberFormat("de-DE").format(total_sales_amount) + ' ' + currency
        }

        get _fomatPeriodRevenue() {
            var total_period_revenue = this.props.partner.total_period_revenue;
            var currency = this.env.pos.currency.name
            return new Intl.NumberFormat("de-DE").format(total_period_revenue) + ' ' + currency
        }

        get _fomatLoyaltyPoints() {
            var total_loyalty_point = this.props.partner.loyalty_points;
            return new Intl.NumberFormat("de-DE").format(total_loyalty_point) + ' Điểm'
        }
    }
    Registries.Component.extend(ClientDetailsEdit, SPartnerLoyaltyPos)
    return SPartnerLoyaltyPos

});

