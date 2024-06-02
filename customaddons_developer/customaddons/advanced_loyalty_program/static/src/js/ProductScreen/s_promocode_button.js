odoo.define('advanced_loyalty_program.SPromoCodeButton', function (require) {
    'use strict';

    const { useListener } = require('web.custom_hooks');
    const PromoCodeButton = require('pos_coupon.PromoCodeButton');
    const Registries = require('point_of_sale.Registries');

    const SPromoCodeButton = (PromoCodeButton) => class extends PromoCodeButton {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);

        }
        async onClick() {
            const currentOrder = this.env.pos.get_order()
            var percent_max = []
            if (currentOrder.get_orderlines().filter((line) => line.reward_id).length) {
                var line_reward_id = currentOrder.get_orderlines().filter((line) => line.reward_id)
                if (line_reward_id.length) {
                    for (var i = 0; line_reward_id.length > i; i++) {
                        if (line_reward_id[i].get_reward()) {
                            if (line_reward_id[i].get_reward().reward_type === 'point'){
                                if (line_reward_id[i].get_reward().s_type_exchange === 'percent'){
                                    percent_max.push(line_reward_id[i])
                                }
                            }
                        }
                    }
                }
                if (percent_max.length) {
                    const {confirmed} = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Thông báo'),
                        body: _.str.sprintf(
                            this.env._t('Áp dụng khuyến mãi sẽ xóa dòng quy đổi điểm tối đa theo phần trăm đơn hàng. Bạn có muốn tiếp tục?'),
                        ),
                        cancelText: this.env._t('No'),
                        confirmText: this.env._t('Yes'),
                    });
                    if (confirmed) {
                        currentOrder.remove_orderline(percent_max)
                    } else {
                        return; // do nothing on the line
                    }
                }
            }
            super.onClick()
        }

    }
    Registries.Component.extend(PromoCodeButton, SPromoCodeButton);
    return SPromoCodeButton;
});
