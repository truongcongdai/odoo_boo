odoo.define('advanced_loyalty_program.SLoyaltyOrderLine', function (require) {
    'use strict';
    const Registries = require("point_of_sale.Registries");
    const OrderLine = require("point_of_sale.Orderline");
    var rpc = require('web.rpc');
    const SLoyaltyOrderLine = (OrderLine) => class extends OrderLine {
        constructor() {
            super(...arguments);
            this.checkLineQty();
        }

        //tang so luong san pham
        async incrementValue(e) {
            if (typeof (this.env.pos.loyalty) !== "undefined"){
                var line_reward = this.props.line.get_reward()
                var spendable_points = this.env.pos.get_order().get_spendable_points()
                if (line_reward !== undefined){
                    if (line_reward.reward_type === "discount" || line_reward.reward_type === "gift"){
                        this.env.pos.get_order().trigger('update-rewards');
                        if (line_reward.reward_type === "gift"){
                            if (line_reward.point_cost > spendable_points){
                                this.showPopup('ErrorPopup', {
                                    title: this.env._t("Lỗi người dùng"),
                                    body: this.env._t("Không thể đổi quá số điểm hiện có"),
                                })
                            } else {
                                super.incrementValue(e)
                            }
                        }
                    }
                    else {
                        super.incrementValue(e)
                    }
                } else {
                    if (this.props.line.getLoyaltyRewardLine().length !== undefined && this.props.line.getLoyaltyRewardLine().length > 0) {
                        const {confirmed} = await this.showPopup('ConfirmPopup', {
                            title: this.env._t('Thông báo'),
                            body: _.str.sprintf(
                                this.env._t('Tăng số lượng sản phẩm sẽ xóa dòng phần thưởng trong đơn hàng. Bạn có muốn tiếp tục?'),
                            ),
                            cancelText: this.env._t('No'),
                            confirmText: this.env._t('Yes'),
                        });
                        if (confirmed) {
                            this.env.pos.get_order().remove_orderline(this.props.line.getLoyaltyRewardLine())
                            super.incrementValue(e)
                        } else {
                            return; // do nothing on the line
                        }
                    } else {
                        super.incrementValue(e)
                    }
                }
            } else {
                super.incrementValue(e)
            }
        }

        async decrementValue(e) {
            if (typeof (this.env.pos.loyalty) !== "undefined"){
                var line_reward = this.props.line.get_reward()
                if (line_reward === undefined){
                    if (this.props.line.getLoyaltyRewardLine().length !== undefined && this.props.line.getLoyaltyRewardLine().length > 0) {
                        const {confirmed} = await this.showPopup('ConfirmPopup', {
                            title: this.env._t('Thông báo'),
                            body: _.str.sprintf(
                                this.env._t('Giảm số lượng sản phẩm sẽ xóa dòng phần thưởng trong đơn hàng. Bạn có muốn tiếp tục?'),
                            ),
                            cancelText: this.env._t('No'),
                            confirmText: this.env._t('Yes'),
                        });
                        if (confirmed) {
                            this.env.pos.get_order().remove_orderline(this.props.line.getLoyaltyRewardLine())
                            super.decrementValue(e)
                        } else {
                            return; // do nothing on the line
                        }
                    } else {
                        super.decrementValue(e)
                    }
                } else {
                    super.decrementValue(e)
                }
            } else {
                super.decrementValue(e)
            }
        }

    }
    Registries.Component.extend(OrderLine, SLoyaltyOrderLine)
    return SLoyaltyOrderLine
})