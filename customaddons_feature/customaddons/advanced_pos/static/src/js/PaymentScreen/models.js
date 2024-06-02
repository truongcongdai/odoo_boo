odoo.define('advanced_pos.s_pos_order', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    const {Gui} = require('point_of_sale.Gui');
    var super_order_model = models.Order.prototype;
    var _super_orderline = models.Orderline.prototype;
    var super_payment_line = models.Paymentline.prototype;
    var rpc = require('web.rpc');
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            this.payment_note = ''; //frk editor
            super_order_model.initialize.apply(this, arguments);
        }, init_from_JSON: function (json) {
            super_order_model.init_from_JSON.apply(this, arguments);
        }, export_as_JSON: function () {
            const json = super_order_model.export_as_JSON.apply(this, arguments);
            json.is_bag = this.pos.is_bag;
            json.is_bill = this.pos.is_bill;
            if (typeof this.pos.sale_person_id != 'undefined') {
                json.sale_person_id = this.pos.sale_person_id
            }
            return json;
        }, export_for_printing: function () {
            const result = super_order_model.export_for_printing.apply(this, arguments);
            result.pos_name = this.pos.config.name
            if (this.pos.config.s_pos_adress) {
                result.s_pos_adress = this.pos.config.s_pos_adress
            } else {
                result.s_pos_adress = ''
            }
            if (this.pos.config.s_pos_phone_number) {
                result.s_pos_phone_number = this.pos.config.s_pos_phone_number
            } else {
                result.s_pos_phone_number = ''
            }
            if (this.get_client()) {
                result.customer_name = this.get_client().name
                result.customer_phone = this.get_client().phone
                result.customer_ranked = this.get_client().customer_ranked
                result.customer_loyalty = this.get_client().loyalty_points
                result.is_connected_vani = this.get_client().is_connected_vani
                result.vani_connect_from = this.get_client().vani_connect_from

            } else if (this.name && this.state) {
                rpc.query({
                    model: 'pos.order',
                    method: 'search_order',
                    args: [1,this.name],
                }).then(function (context) {
                    document.getElementById('customer-name').innerText = context['customer_name']
                    document.getElementById('customer-phone').innerText = context['customer_phone']
                });
            } else {
                result.customer_name = ''
                result.customer_phone = ''
                result.customer_ranked = ''
                result.customer_loyalty = ''
                result.is_connected_vani = ''
                result.vani_connect_from = ''
            }

            return result;

        },
        async activateCode(code) {
            let today = new Date();
            const promoProgram = this.pos.promo_programs.find(
                (program) => program.promo_barcode == code || program.promo_code == code
            );
            if (promoProgram) {
                if(Date.parse(promoProgram.rule_date_to) < today){
                    return Gui.showNotification(`Mã giảm giá này đã hết hạn (${code})!`);
                }
            }
            await super_order_model.activateCode.apply(this, arguments);
        },
    });
    models.Orderline = models.Orderline.extend({
        initialize: function (attr, options) {
            _super_orderline.initialize.apply(this, arguments);
            this.attribute = options.attribute;
        },
        get_color_variant: function () {
            var color = this.product.mau_sac;
            if (color) {
                return color;
            }
        },
        get_size_variant: function () {
            var size = this.product.kich_thuoc;
            if (size) {
                return size;
            }
        },
        get_sku_variant: function () {
            var sku = this.product.default_code;
            if (sku) {
                return sku;
            }
        },
        export_as_JSON: function () {
            const attributes_variant = _super_orderline.export_as_JSON.apply(this, arguments);
            attributes_variant.mau_sac = this.get_color_variant()
            attributes_variant.kich_thuoc = this.get_size_variant()
            attributes_variant.default_code = this.get_sku_variant()
            return attributes_variant;
        },
    });
    models.Paymentline = models.Paymentline.extend({
        export_as_JSON: function () {
            const json = super_payment_line.export_as_JSON.call(this);
            json.payment_note = this.get_payment_note() //frk editor
            return json;
        },
        //frk start
        get_payment_note: function () {
            return this.payment_note;
        },
        //frk end
    });
})