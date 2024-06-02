odoo.define("advanced_pos.s_payment_screen_payment_lines", function (require) {
    "use strict";

    const PaymentScreenPaymentLines = require("point_of_sale.PaymentScreenPaymentLines");
    const Registries = require("point_of_sale.Registries");

    const s_payment_screen_payment_lines = (PaymentScreenPaymentLines) => class extends PaymentScreenPaymentLines {
        onKeyPaymentNote(line,value){
            line.payment_note = value.target.value;
        }
    }
    Registries.Component.extend(PaymentScreenPaymentLines, s_payment_screen_payment_lines)
    return s_payment_screen_payment_lines
});
