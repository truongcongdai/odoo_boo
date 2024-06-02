odoo.define('advanced_pos.SCoupon', function (require) {
    "use strict";

    const { Gui } = require('point_of_sale.Gui');
    var models = require('point_of_sale.models');
    var _order_super = models.Order.prototype;
    models.Order = models.Order.extend({

        resetPrograms: function () {
            this.activeMultiFreeProducts=true
            this.resetProgramsContext=true
            let deactivatedCount = 0;
            if (this.bookedCouponCodes) {
                const couponIds = Object.values(this.bookedCouponCodes).map((couponCode) => couponCode.coupon_id);
                if (couponIds.length > 0) {
                    this.trigger('reset-coupons', couponIds);
                }
                this.bookedCouponCodes = {};
                deactivatedCount += couponIds.length;
            }
            if (this.activePromoProgramIds) {
                const codeNeededPromoProgramIds = this.activePromoProgramIds.filter((program_id) => {
                    // return this.pos.coupon_programs_by_id[program_id].promo_code_usage === 'code_needed';
                    if(this.pos.coupon_programs_by_id[program_id]){ // Nếu trong cache ko có CTKM ở Pos Config thì sẽ bị lỗi. Vì thế thêm điều kiện này
                        return this.pos.coupon_programs_by_id[program_id].promo_code_usage === 'code_needed';
                    }
                });
                this.activePromoProgramIds = this._getAutomaticPromoProgramIds();
                deactivatedCount += codeNeededPromoProgramIds.length;
            }
            if (deactivatedCount > 0) Gui.showNotification('Phiếu giảm giá đang hoạt động và mã khuyến mãi đã bị vô hiệu hóa.');
            this.trigger('update-rewards');
            ///start block reset program free products
            // var order_lines = this.orderlines.models
            // var promo_lines = []
            // if (order_lines){
            //     for (var i = 0; i < order_lines.length; i++){
            //         if (order_lines[i].program_id){
            //             promo_lines.push(order_lines[i].program_id)
            //         }
            //     }
            // }
            // if (promo_lines.length){
            //     for (var j = 0; j < order_lines.length; j++){
            //         var s_program = this.pos.coupon_programs_by_id[order_lines[j].program_id]
            //         if (typeof s_program !== "undefined" ){
            //             var check = this.activePromoProgramIds.filter(l => l === s_program.id)
            //             if (!check.length){
            //                 if (s_program.s_free_products.length > 0 && s_program.s_is_free_products === true){
            //                     this.activePromoProgramIds.push(s_program.id)
            //                 }
            //             }
            //         }
            //     }
            // }
            ///end block reset program free products
        },

        activateCode: async function (code) {
            const promoProgram = this.pos.promo_programs.find(
                (program) => program.promo_barcode == code || program.promo_code == code
            );
            // if (this.pos.promo_programs){
            //         this.activePromoProgramIds = this._getAutomaticPromoProgramIds();
            //
            //     }
            if (promoProgram){
                if(this.activePromoProgramIds.includes(promoProgram.id)){
                    return Gui.showNotification('Chương trình mã khuyến mãi này đã được kích hoạt.');
                }
            }
            if (code in this.bookedCouponCodes) {
                return Gui.showNotification('Mã phiếu giảm giá này đã được quét và kích hoạt.');
            }
            for (let i = 0; this.orderlines.models.length > i; i++){
                if (this.orderlines.models[i].is_gift_card_discard){
                    return Gui.showNotification('Không thể áp dụng CTKM vì đơn hàng đang sử dụng Gift Card Discard');
                }
            }
            await _order_super.activateCode.apply(this, arguments);
        },

        _getOnCheapestProductDiscount: function (program, coupon_id) {
            const amountsToDiscount = {};
            const orderlines = this._getRegularOrderlines();
            if (program.program_type === "promotion_program" && program.discount_apply_on === "cheapest_product"
                && program.discount_type === "percentage" && program.discount_percentage === 100
                && program.rule_min_quantity >= 1 && program.free_discount_cheapest_products === true) {
                if (orderlines.length > 0) {
                    var multiCheapestLines = [];
                    var free_cheapest_line = []
                    var _productQuantity = this._productQuantity()
                    const math_trunc = Math.trunc(_productQuantity / program.rule_min_quantity)
                    if (math_trunc > 0){
                        for (let i = 0; math_trunc > i; i++){
                            const cheapestLine = this._searchCheapestLine(orderlines, free_cheapest_line);
                            if (cheapestLine) {
                                if (!free_cheapest_line.map(l => l.id).includes(cheapestLine.id) || cheapestLine.quantity > 1 ){
                                    free_cheapest_line.push(cheapestLine)
                                }
                            }
                        }
                        if (free_cheapest_line.length) {
                            for (let x = 0; free_cheapest_line.length > x; x++) {
                                const key = this._getGroupKey(free_cheapest_line[x]);
                                const multiAmountsToDiscount = {};
                                multiAmountsToDiscount[key] = free_cheapest_line[x].price;
                                multiCheapestLines.push(multiAmountsToDiscount)
                            }
                            return this._multiFreeDiscountRewards(program, coupon_id, multiCheapestLines);
                        }
                    }
                }
            }
            else {
                if (orderlines.length > 0) {
                    const cheapestLine = orderlines.reduce((min_line, line) => {
                        if (line.price < min_line.price && line.price >= 0) {
                            return line;
                        } else {
                            return min_line;
                        }
                    }, orderlines[0]);
                    const key = this._getGroupKey(cheapestLine);
                    amountsToDiscount[key] = cheapestLine.price;
                }
            }
            return this._createDiscountRewards(program, coupon_id, amountsToDiscount);
        },

        // _getOnCheapestProductDiscount: function (program, coupon_id) {
        //     const amountsToDiscount = {};
        //     const orderlines = this._getRegularOrderlines();
        //     if (orderlines.length > 0) {
        //         const cheapestLine = orderlines.reduce((min_line, line) => {
        //             if (line.price < min_line.price && line.price >= 0) {
        //                 return line;
        //             } else {
        //                 return min_line;
        //             }
        //         }, orderlines[0]);
        //         const key = this._getGroupKey(cheapestLine);
        //         amountsToDiscount[key] = cheapestLine.price;
        //     }
        //     return this._createDiscountRewards(program, coupon_id, amountsToDiscount);
        // },

        _searchCheapestLine: function (orderlines, free_cheapest_line) {
            var line_discount = orderlines
            if (free_cheapest_line.length) {
                // orderlines = orderlines.filter(l => !free_cheapest_line.map(r => r.id).includes(l.id))
                for (let x = 0; orderlines.length > x; x++) {
                    var compare_qty = free_cheapest_line.filter(l =>l.id === orderlines[x].id)
                    if (compare_qty.length > 0) {
                        if (compare_qty.length === orderlines[x].quantity) {
                            var removeLine = orderlines.filter(l => compare_qty.map(r => r.id).includes(l.id))
                            line_discount = line_discount.filter(l => !removeLine.map(r => r.id).includes(l.id))
                        }
                    }
                }
            }
            const freeQuantityPerProduct = {};
            const remainingQtyOfLine = new Map();
            if (line_discount.length) {
                for (const line of [...line_discount].sort((a, b) => b.price - a.price)) {
                    const productId = line.product.id;
                    let freeQuantity = freeQuantityPerProduct[productId] || 0;
                    remainingQtyOfLine.set(line, line.get_quantity());
                    const lineQty = remainingQtyOfLine.get(line);
                    if (lineQty < freeQuantity) {
                        remainingQtyOfLine.set(line, 0);
                        freeQuantity -= lineQty;
                    } else {
                        remainingQtyOfLine.set(line, lineQty - freeQuantity);
                        freeQuantity = 0;
                    }
                    freeQuantityPerProduct[productId] = freeQuantity;
                }
                const linesWithoutRewards = [...remainingQtyOfLine.entries()]
                    .map(([line, _]) => line)
                    .sort((a, b) => a.price - b.price);
                return linesWithoutRewards[0];
            }
            return false
        },

        _productQuantity: function (){
            var order = this.pos.get_order();
            var sum = 0;
            var product_quantity_positive = 0
            var product_quantity_minus = 0
            if (order.orderlines.length > 0){
                for (let i = 0; i < order.orderlines.length; i++) {
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
        },
    });
});
