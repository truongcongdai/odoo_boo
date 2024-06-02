odoo.define("advanced_loyalty_program.PaymentScreen", function (require) {
    "use strict";

    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');
    window.intervalIDs = window.intervalIDs || [];

    const SPaymentScreen = PaymentScreen => class extends PaymentScreen {
        constructor() {
            super(...arguments);
            this.clickCount = 0;
        }

        _onChangeInputOtp(event) {
            const is_loyalty_program = this.isLoyaltyProgram();
            const new_value = event.target.value;
            if (is_loyalty_program) {
                if (($(".next").hasClass("disable-btn")) && new_value.length > 0) {
                    $(".next").removeClass("disable-btn");
                } else if (!$(".next").hasClass("disable-btn") && new_value.length === 0) {
                    $(".next").addClass("disable-btn");
                }
            }

        }

        send_otp_zns(phone_number, zalo_zns_template_id, cid_order, type_otp) {
            return rpc.query({
                model: 'sms.sms',
                method: 'send_otp_zns',
                args: [0, phone_number, zalo_zns_template_id, cid_order, type_otp],
            }, {
            shadow: true,
        }).then(function (otp) {
                return otp;
            });
        }

        countdown(customer_phone) {
            var check_customer_phone = document.getElementsByClassName('phone-number');
            var timeleft = 300;
            var downloadTimer = setInterval(function () {
                timeleft--;
                const count_down_timer = document.getElementById("countdowntimer");
                if (count_down_timer) {
                    if (customer_phone === check_customer_phone[0]) {
                        count_down_timer.textContent = timeleft + ' giây';
                    }
                }
                if (timeleft <= 0)
                    clearInterval(downloadTimer);
            }, 1000);
            window.intervalIDs.push(downloadTimer);
        }

        send_back_otp() {
            this.clickCount++;
            var button = document.querySelector('.btn-send-otp'); // Select the button
            var customer_phone = document.getElementsByClassName('phone-number')[0];
            var zalo_template = document.getElementsByClassName('zalo-zns-template-id')[0];
            var count_down_timer = document.getElementById("countdowntimer");
            var array_count_down_timer = count_down_timer.textContent.split(' ');
            var order = this.env.pos.get_order();
            var cid_order = '';
            if (order) {
                cid_order = order.cid;
            }

            if (customer_phone && zalo_template) {
                var phone_number = customer_phone.textContent;
                var zalo_zns_template_id = zalo_template.textContent;

                if ((array_count_down_timer && !parseInt(array_count_down_timer[0])) || (array_count_down_timer && parseInt(array_count_down_timer[0]) === 0)) {
                    this.countdown(customer_phone);
                    this.send_otp_zns(phone_number, zalo_zns_template_id, cid_order, 'pos');
                }
            }
            if (this.clickCount > 0) {
                button.innerHTML = "Gửi lại Mã OTP";
            }
        }

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

        get isInputOTP() {
            return this.isLoyaltyProgram();
        }

        get customer() {
            const is_loyalty_program = this.isLoyaltyProgram();
            if (is_loyalty_program && this.currentOrder.get_client()) {
                return {
                    'phone_number': this.currentOrder.get_client().phone,
                    'zalo_zns_template_id': this.env.pos.loyalty.zns_template_id[0],
                    'countdowntimer': '',
                }
            }
        }

        validate_order(phone_number, zalo_otp) {
            return rpc.query({
                model: 's.res.partner.otp',
                method: 'validate_order',
                args: [0, phone_number, zalo_otp],
            }).then(function (result) {
                return result;
            });
        }

        async validateOrder(isForceValidate) {
            const is_loyalty_program = this.isLoyaltyProgram();
            if (is_loyalty_program) {
                var otp = document.getElementById('input-otp');
                if (otp) {
                    var zalo_otp = otp.value;
                    if (zalo_otp.length > 0) {
                        var phone_number = this.currentOrder.get_client().phone;
                        var result = await this.validate_order(phone_number, zalo_otp);
                        if (!result) {
                            await this.showPopup('ErrorPopup', {
                                title: this.env._t('Lỗi người dùng'),
                                body: this.env._t("Mã xác thực OTP không khớp. Vui lòng nhập lại mã OTP."),
                            });
                            return;
                        }
                    } else {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Lỗi người dùng'),
                            body: this.env._t("Mã xác thực OTP không được bỏ trống."),
                        });
                        return;
                    }

                }
            }
            return super.validateOrder();
        }

    };
    Registries.Component.extend(PaymentScreen, SPaymentScreen);
    return SPaymentScreen;
});
