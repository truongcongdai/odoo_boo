odoo.define('advanced_loyalty_program.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    var {Gui} = require('point_of_sale.Gui');
    var rpc = require('web.rpc');
    var utils = require('web.utils');
    var round_pr = utils.round_precision;

    const SProductScreen = (ProductScreen) => class extends ProductScreen {
        constructor() {
            super(...arguments);
            // useListener('boo-click-product', this._ClickAddProduct);
        }

        isObjectEmpty(value) {
            return (
                (value == null) ||
                (value.hasOwnProperty('length') && value.length === 0) ||
                (value.constructor === Object && Object.keys(value).length === 0)
            )
        };

        // send_otp_zns(phone_number, zalo_zns_template_id, resend, sum_quantity_order_line) {
        //     return rpc.query({
        //         model: 'sms.sms',
        //         method: 'send_otp_zns',
        //         args: [0, phone_number, zalo_zns_template_id, resend, sum_quantity_order_line],
        //     }).then(function (otp) {
        //         return otp;
        //     });
        // }

        isLoyaltyProgram() {
            var is_loyalty_program = false;
            if (this.env.pos.config.module_pos_loyalty && this.env.pos.loyalty) {
                if (this.env.pos.loyalty.zns_template_id) {
                    if (this.env.pos.loyalty.rewards.length > 0) {
                        var line_reward_id = this.env.pos.get_order().get_orderlines().map(line => line.reward_id);
                        var rewards_ids = this.env.pos.loyalty.rewards.map(reward => reward.id);
                        if (line_reward_id.some(id => rewards_ids.includes(id))) {
                            is_loyalty_program = true;
                        }
                    }
                }
            }
            return is_loyalty_program;
        }

        async _onClickPay() {
            const res = super._onClickPay();
            if (this.isLoyaltyProgram()) {
                if (this.env.pos.config.module_pos_loyalty && this.env.pos.loyalty.zns_template_id) {
                    var customer = this.currentOrder.get_client();
                    const is_customer_empty = this.isObjectEmpty(customer);
                    if (!is_customer_empty) {
                        // const zalo_zns_template_id = this.env.pos.loyalty.zns_template_id[0];
                        // const phone_number = customer['phone'];
                        // const order_line = this.env.pos.get_order().get_orderlines();
                        // if (order_line.length > 0) {
                        //     var sum_quantity_order_line = 0;
                        //     for (var line of order_line) {
                        //         sum_quantity_order_line = sum_quantity_order_line + line.quantity;
                        //     }
                        // }
                        // await this.send_otp_zns(phone_number, zalo_zns_template_id, false, sum_quantity_order_line);
                        if ($(".next").hasClass("highlight")) {
                            $(".next").addClass("disable-btn");
                        }
                    }
                }
            }
            return res;
        }

        async _setValue(val) {
            if (this.env.pos.config.loyalty_id) {
                var set_val = 0
                const select_order_line = this.currentOrder.get_selected_orderline();
                var spendable_points = -1
                if (this.getSpentPoints(val, select_order_line) >= 0) {
                    spendable_points = this.get_loyalty_point() - this.getSpentPoints(val, select_order_line)
                }
                if (select_order_line) {
                    if (typeof (this.env.pos.config.module_pos_loyalty) !== "undefined" && this.env.pos.config.module_pos_loyalty) {
                        if (val !== "") {
                            var reward = select_order_line.get_reward()
                            if (reward !== undefined && reward.reward_type === 'point') {
                                // var loyaltyPoints = this.get_loyalty_point()
                                if (spendable_points >= 0) {
                                    if (select_order_line.product.s_loyalty_product_reward &&
                                        reward.s_exchange_product[0] === select_order_line.product.id
                                        && select_order_line.product.type === 'service') {
                                        var unit_price = -(reward.s_reward_exchange_monetary / reward.s_reward_exchange_point)
                                        ///Quy đổi điểm/đơn hàng
                                        var exchange_maximum = 0
                                        var s_total = this.currentOrder.get_total_with_tax()
                                        if (reward.s_type_exchange === 'number') {
                                            //TH1: val < Quy đổi tối đa
                                            exchange_maximum = reward.s_exchange_maximum
                                            if ((parseInt(val) * reward.s_reward_exchange_point) <= exchange_maximum) {
                                                select_order_line.set_unit_price(unit_price)
                                                set_val = val
                                                // if (parseInt(val) > spendable_points){
                                                //     select_order_line.set_unit_price(unit_price)
                                                //     set_val = spendable_points.toString()
                                                //     this.showPopup('ErrorPopup', {
                                                //         title: this.env._t("Thông báo"),
                                                //         body: this.env._t("Không thể đổi quá số điểm hiện có"),
                                                //     });
                                                // } else {
                                                //     select_order_line.set_unit_price(unit_price)
                                                //     set_val = val
                                                // }
                                            }
                                            //TH2: val > Quy đổi tối đa
                                            else if ((parseInt(val) * reward.s_reward_exchange_point) > exchange_maximum) {
                                                // if (exchange_maximum > spendable_points){
                                                //     select_order_line.set_unit_price(unit_price)
                                                //     set_val = spendable_points.toString()
                                                // }
                                                // else {
                                                //     select_order_line.set_unit_price(unit_price)
                                                //     set_val = exchange_maximum.toString()
                                                // }
                                                select_order_line.set_unit_price(unit_price)
                                                set_val = Math.floor(exchange_maximum / reward.s_reward_exchange_point).toString()
                                                this.showPopup('ErrorPopup', {
                                                    title: this.env._t("Thông báo"),
                                                    body: this.env._t("Không thể đổi quá số điểm quy đổi tối đa"),
                                                });
                                                return;
                                            }
                                            //TH3: val = Quy đổi tối đa
                                            // else {
                                            //     if (parseInt(val) > spendable_points){
                                            //         select_order_line.set_unit_price(unit_price)
                                            //         set_val = spendable_points.toString()
                                            //     } else {
                                            //         select_order_line.set_unit_price(unit_price)
                                            //         set_val = val
                                            //     }
                                            // }
                                        } else {
                                            s_total += Math.abs(select_order_line.quantity * select_order_line.price)
                                            var rate = reward.s_reward_exchange_monetary / reward.s_reward_exchange_point
                                            exchange_maximum = (((s_total * reward.s_exchange_maximum) / 100) / rate)
                                            if ((parseInt(val) * reward.s_reward_exchange_point) <= exchange_maximum) {
                                                select_order_line.set_unit_price(unit_price)
                                                set_val = val
                                            } else if ((parseInt(val) * reward.s_reward_exchange_point) > exchange_maximum) {
                                                select_order_line.set_unit_price(unit_price)
                                                set_val = Math.floor(exchange_maximum.toString() / reward.s_reward_exchange_point)
                                                this.showPopup('ErrorPopup', {
                                                    title: this.env._t("Thông báo"),
                                                    body: this.env._t("Không thể đổi quá số điểm quy đổi tối đa"),
                                                });
                                                return;
                                            }
                                        }
                                    }
                                } else {
                                    // select_order_line.set_unit_price(0)
                                    // select_order_line.set_quantity(0)
                                    this.showPopup('ErrorPopup', {
                                        title: this.env._t("Thông báo"),
                                        body: this.env._t("Điểm quy đổi vượt quá số điểm khách hàng hiện có"),
                                    });
                                    return;
                                }
                            } else if (reward !== undefined && reward.reward_type !== 'point') {
                                set_val = 1
                                if (reward.reward_type === 'gift') {
                                    if (spendable_points < 0) {
                                        this.showPopup('ErrorPopup', {
                                            title: this.env._t("Lỗi người dùng"),
                                            body: this.env._t("Không thể đổi quá số điểm hiện có"),
                                        })
                                    } else {
                                        set_val = parseInt(val)
                                    }
                                }
                            } else if (select_order_line.get_reward() === undefined) {
                                if (this.currentOrder.get_orderlines().filter((line) => line.reward_id).length) {
                                    const {confirmed} = await this.showPopup('ConfirmPopup', {
                                        title: this.env._t('Thông báo'),
                                        body: _.str.sprintf(
                                            this.env._t('Đặt số lượng sản phẩm sẽ xóa dòng phần thưởng trong đơn hàng. Bạn có muốn tiếp tục?'),
                                        ),
                                        cancelText: this.env._t('No'),
                                        confirmText: this.env._t('Yes'),
                                    });
                                    if (confirmed) {
                                        this.currentOrder.remove_orderline(this.currentOrder.get_orderlines().filter((line) => line.reward_id))
                                    } else {
                                        return; // do nothing on the line
                                    }
                                }
                            }
                        } else if (select_order_line.get_reward() === undefined && val === "") {
                            const {confirmed} = await this.showPopup('ConfirmPopup', {
                                title: this.env._t('Thông báo'),
                                body: _.str.sprintf(
                                    this.env._t('Xóa dòng sản phẩm sẽ xóa dòng phần thưởng trong đơn hàng. Bạn có muốn tiếp tục?'),
                                ),
                                cancelText: this.env._t('No'),
                                confirmText: this.env._t('Yes'),
                            });
                            if (confirmed) {
                                this.currentOrder.remove_orderline(this.currentOrder.get_orderlines().filter((line) => line.reward_id))
                            } else {
                                return; // do nothing on the line
                            }
                        }
                    }
                }
            }
            if (set_val > 0) {
                val = parseInt(set_val)
            }
            super._setValue(val)
        }

        getSpentPoints(val, select_order_line) {
            var points = 0;
            if (!this.env.pos.loyalty || !this.env.pos.get_client()) {
                return 0;
            } else {
                var reward_point = 0
                var loyalty_points = this.currentOrder.get_client().loyalty_points
                var lines = this.currentOrder.get_orderlines()
                // var spendable_points = this.currentOrder.get_spendable_points()
                if (lines) {
                    for (var line of lines) {
                        var reward = line.get_reward();
                        if (reward) {
                            if (reward.reward_type === "point") {
                                // if ((this.currentOrder.get_client().loyalty_points - (points + round_pr(parseInt(val) * reward.s_reward_exchange_point, 1))) >= 0){
                                if (line.id === select_order_line.id) {
                                    // reward_point += round_pr(parseInt(val), 1);
                                    points += parseInt(val) * reward.s_reward_exchange_point
                                } else {
                                    // this.set_price_exchange_product(reward)
                                    // reward_point += round_pr(line.get_quantity(), 1);
                                    points += (line.get_quantity() * reward.s_reward_exchange_point)
                                }
                                // }
                                // else {
                                //     this.orderlines.remove(line)
                                // }
                            } else {
                                if (line.id === select_order_line.id) {
                                    points += round_pr(parseInt(val) * reward.point_cost, 1);
                                } else {
                                    points += round_pr(line.get_quantity() * reward.point_cost, 1);
                                }
                            }
                        }
                    }
                }
            }
            points = loyalty_points - points
            return points
        }

        get_loyalty_point() {
            const customer = this.currentOrder.get_client()
            if (!customer) {
                return false
            }
            return customer.loyalty_points
        }

        _ClickAddProduct(event) {
            var reward_line
            var order_lines = this.currentOrder.get_orderlines()
            if (order_lines.length > 0) {
                reward_line = order_lines.filter((line) => line.reward_id)
                this.currentOrder.remove_orderline(reward_line)
            }
        }
    }

    SProductScreen.template = 'ProductScreen';
    Registries.Component.extend(ProductScreen, SProductScreen);
    return ProductScreen;
});
