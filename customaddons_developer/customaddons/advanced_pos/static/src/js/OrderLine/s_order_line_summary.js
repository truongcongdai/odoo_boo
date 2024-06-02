odoo.define('advanced_pos.SOrderLineSummary', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const OrderSummary = require('point_of_sale.OrderSummary');

    const AdvancedOrderSummary = OrderSummary =>
    class extends OrderSummary {
        get productQuantity() {
            var order = this.env.pos.get_order();
            var sum = 0;
            var product_quantity_positive = 0
            var product_quantity_minus = 0
            if (order.orderlines.models.length > 0){
                for (let i = 0; i < order.orderlines.models.length; i++) {
                    if(order.orderlines.models[i].product.type === 'product'){
                        if(order.orderlines.models[i].quantity < 0) {
                            product_quantity_minus += order.orderlines.models[i].quantity
                        }
                        else {
                            product_quantity_positive += order.orderlines.models[i].quantity
                        }
                    }
                }
            }
            sum = product_quantity_positive + Math.abs(product_quantity_minus);
            return sum;
        }

        get giftcardCash() {
            var currentOrder = this.env.pos.get_order();
            var giftcard_array_ids = currentOrder.giftcard_array
            var gift_card_name_ids = []
            if (giftcard_array_ids) {
                for(let i = 0; i < giftcard_array_ids.length; i++){
                    gift_card_name_ids.push(giftcard_array_ids[i].name)
                }
            }
            return gift_card_name_ids
        }
    }
    Registries.Component.extend(OrderSummary, AdvancedOrderSummary);

    return OrderSummary;
});
