odoo.define('advanced_pos.OrderReceipt', function (require) {
    'use strict';
    const {useState, useRef, onPatched, useComponent} = owl.hooks;
    const Registries = require("point_of_sale.Registries");
    const GiftCardPopup = require("pos_gift_card.GiftCardPopup");
    const SGiftCardPopup = (GiftCardPopup) => class extends GiftCardPopup {
        constructor() {
            super(...arguments);
            this.state = useState({
                checkDiscountGiftCard: false,
                checkAmountGiftCard: false,
                is_not_calculate_amount: false,
            });
        }

        async UseWithGiftCard(){
            let giftCard = await this.getGiftCard();
            if (!giftCard) return;
            if (giftCard.discount_percentage !== false && giftCard.discount_type === "percentage"){
                this.state.valueGiftCard = giftCard.discount_percentage;
                this.state.checkDiscountGiftCard = true
                this.state.checkAmountGiftCard = false
            }
            if (giftCard.discount_amount !== false && giftCard.discount_type === "discount_amount"){
                this.state.valueGiftCard = giftCard.discount_amount;
                this.state.checkDiscountGiftCard = false
                this.state.checkAmountGiftCard = true
            }
            if(giftCard.is_not_calculate_amount === true){
                this.state.is_not_calculate_amount = true
            }else{
                this.state.is_not_calculate_amount = false
            }
        }

        //Customize discount theo %
        // async DiscountWithGiftCard() {
        //     let giftCard = await this.getGiftCard();
        //     if (!giftCard) return;
        //     this.state.valueGiftCard = giftCard.discount_percentage;
        //     this.state.checkDiscountGiftCard = true
        //     this.state.checkAmountGiftCard = false
        // }

        get totalCurrentOrderValue() {
            var currentOrder = this.env.pos.get_order();
            var sum = 0.0;
            for (var i=0; i<currentOrder.orderlines.models.length; i++) {
                var line = currentOrder.orderlines.models[i];
                sum += (line.quantity * line.price) - (line.quantity * line.price) * line.discount / 100;
            }
            return sum;
        }

        //Customize discount theo amount
        // async AmountWithGiftCard() {
        //     let giftCard = await this.getGiftCard();
        //     if (!giftCard) return;
        //     this.state.valueGiftCard = giftCard.discount_amount
        //     this.state.checkAmountGiftCard = true
        //     this.state.checkDiscountGiftCard = false
        // }

        //override customize get gift card lay theo discount va amount
        async getGiftCard() {
            let currentOrder = this.env.pos.get_order();
            if (this.state.giftCardBarcode == "") return;
            let giftCard = await this.rpc({
                model: "gift.card",
                method: "search_read",
                args: [[["code", "=", this.state.giftCardBarcode]]],
            });
            if (giftCard.length) {
                giftCard = giftCard[0];
            } else {
                return false;
            }
            if (this.state.checkAmountGiftCard) {
                if (giftCard.is_not_calculate_amount !== true) {
                    if (giftCard.discount_amount > giftCard.balance) {
                        giftCard.discount_amount = giftCard.balance;
                    }
                    giftCard.s_balance_left = giftCard.balance - giftCard.discount_amount
                    giftCard.balance = giftCard.discount_amount
                }
            } else if (this.state.checkDiscountGiftCard) {
                // var sum = 0;
                // for (var i=0; i<currentOrder.orderlines.models.length; i++) {
                //     var line = currentOrder.orderlines.models[i];
                //     if(line.product.type === 'product'){
                //         sum += line.quantity * line.price;
                //     }
                // }
                // let discountRightAmount = (giftCard.discount_percentage * sum)/100;
                let totalCurrentOrderValue = this.totalCurrentOrderValue;
                let discountRightAmount = (giftCard.discount_percentage * totalCurrentOrderValue)/100;
                if (giftCard.is_not_calculate_amount !== true) {
                    if (discountRightAmount > giftCard.balance) {
                        discountRightAmount = giftCard.balance;
                    }
                    giftCard.s_balance_left = giftCard.balance - discountRightAmount
                    giftCard.balance = discountRightAmount
                }
                // if (discountRightAmount > giftCard.balance) {
                //     discountRightAmount = giftCard.balance;
                // }
                // giftCard.balance = discountRightAmount
            }
            return giftCard;
        }

        async payWithGiftCard() {
            let giftCard = await this.getGiftCard();
            if (!giftCard) return;
            let currentOrder = this.env.pos.get_order();
            if(giftCard.partner_id){
                if(currentOrder.changed && currentOrder.changed.client){
                    if(giftCard.partner_id[0] !== currentOrder.changed.client['id']){
                        var partner_name = currentOrder.changed.client['name']
                        return await this.showPopup('ErrorPopup', {
                            title: this.env._t('Lỗi áp dụng Gift Card'),
                            body: this.env._t('Gift Card này không được áp dụng cho khách hàng ')+partner_name,
                        });
                    }
                }else{
                    return await this.showPopup('ErrorPopup', {
                        title: this.env._t('Chưa chọn khách hàng'),
                        body: this.env._t('Chọn khách hàng trước khi áp dụng Gift Card'),
                    });
                }
            }
            if (giftCard.is_not_calculate_amount === true) {
                if (giftCard.balance && giftCard.balance > 0 && giftCard.is_used_gift_card === false) {
                    if (currentOrder.giftcard_array === undefined || currentOrder.giftcard_array.length === 0) {
                        currentOrder.giftcard_array = [giftCard]
                    }
                    else {
                        var giftcard_array_codes = []
                        for(let i = 0; i < currentOrder.giftcard_array.length; i++){
                            giftcard_array_codes.push(currentOrder.giftcard_array[i].code)
                        }
                        if(giftcard_array_codes.includes(giftCard.code) === true){
                            await this.showPopup('ErrorPopup', {
                                title: this.env._t('Thẻ quà tặng đã tồn tại'),
                                body: this.env._t('Thẻ quà tặng đã được thêm vào đơn hàng'),
                            });
                        }else{
                            currentOrder.giftcard_array.push(giftCard)
                        }
                    }
                    this.cancel();
                }
                else if (giftCard.is_used_gift_card === true) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Thẻ quà tặng đã sử dụng'),
                        body: this.env._t('Thẻ quà tặng đã được sử dụng'),
                    });
                }
                else {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Số dư không đủ'),
                        body: this.env._t('Số dư của gift card cash bằng 0'),
                    });
                }
            }
            if(giftCard.is_gift_card_discard){
                for (let i = 0; currentOrder.orderlines.models.length > i; i++){
                    if(currentOrder.orderlines.models[i].price < currentOrder.orderlines.models[i].product.lst_price){
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Không áp dụng được Gift Card Discard'),
                            body: this.env._t('Không thể áp dụng Gift Card Discard cho đơn hàng vì giá thông tin sản phẩm > giá sản phẩm trong SO line'),
                        });
                    }
                    if (currentOrder.orderlines.models[i].program_id || currentOrder.orderlines.models[i].gift_card_id){
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Không áp dụng được Gift Card Discard'),
                            body: this.env._t('Không thể áp dụng Gift Card Discard cho đơn hàng '),
                        });
                    }
                }
            }else if(!giftCard.is_not_calculate_amount){
                var program_line_id = currentOrder.orderlines.models.filter(l => l.program_id)
                for (let i = 0; currentOrder.orderlines.models.length > i; i++){
                    if (currentOrder.orderlines.models[i].is_gift_card_discard){
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Không áp dụng được Gift Card'),
                            body: this.env._t('Không thể áp dụng Gift Card vì đơn hàng đang sử dụng Gift Card Discard'),
                        });
                    }
                    if (program_line_id.length) {
                        for (let i=0; i < program_line_id.length; i++){
                            var program = this.env.pos.coupon_programs_by_id[program_line_id[i].program_id]
                            if (program && program.s_is_program_discard === true){
                                await this.showPopup('ErrorPopup', {
                                    title: this.env._t('Không áp dụng được Gift Card'),
                                    body: this.env._t('Chỉ có thể kết hợp CTKM discard với Gift Card không trừ doanh thu'),
                                });
                            }
                        }
                    }
                }
            }
            // localStorage.setItem("giftcardCode", giftCard.code);
            // // localStorage.getItem("giftcardCode");
            // localStorage.removeItem("giftcardCode")

            super.payWithGiftCard(...arguments);
        }

        switchSelectTypeView() {
            this.state.checkDiscountGiftCard = false
            this.state.checkAmountGiftCard = false
            this.state.giftCardBarcode = ''
        }
    }
    Registries.Component.extend(GiftCardPopup, SGiftCardPopup)
    return SGiftCardPopup
});
