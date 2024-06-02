odoo.define('advanced_pos.RewardButton', function (require) {
    'use strict';

    const RewardButton = require('pos_loyalty.RewardButton');
    const Registries = require('point_of_sale.Registries');

    const SRewardButton = (RewardButton) => class extends RewardButton {
        constructor() {
            super(...arguments);
        }

        async onClick() {
            let order = this.env.pos.get_order();
            let rewards = order.get_available_rewards();
            if (rewards.length === 0) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Không có phần thưởng'),
                    body: this.env._t('Khách hàng không có phần thường nào trong chương trình khách hàng thân thiết'),
                });
                return;
            } else {
                await super.onClick(this, arguments);
            }
        }

    };
    Registries.Component.extend(RewardButton, SRewardButton);
    return SRewardButton;
});
