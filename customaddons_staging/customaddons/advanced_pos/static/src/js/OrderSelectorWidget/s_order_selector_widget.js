odoo.define('point_of_sale.SOrderSelectorWidget', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const PosComponent = require('point_of_sale.PosComponent');
    const {useListener, useAutofocus} = require('web.custom_hooks');
    const {Gui} = require('point_of_sale.Gui');
    const {posbus} = require('point_of_sale.utils');
    const PosModel = require('point_of_sale.models');

    class SOrderSelectorWidget extends PosComponent {
        constructor() {
            super(...arguments);
        }

        //an search product list
        _onMouseMoveOrderSelect(event) {
            var classCurrent = event.target.className
            var product_item_dialog = $(".search-bar-portal .s_search_product_item_dialog")
            if (product_item_dialog.length > 0) {
                if (classCurrent.length > 0) {
                    if (classCurrent !== 'search-bar-portal' && classCurrent !== 'search-box' && !classCurrent.includes("s_search_product_item")) {
                        product_item_dialog[0].style.display = 'none'
                    }
                }
            }
        }

        get_order_by_uid(uid) {
            var orders = this.env.pos.get_order_list();
            for (var i = 0; i < orders.length; i++) {
                if (orders[i].uid === uid) {
                    return orders[i];
                }
            }
            return undefined;
        };

        async _check_screen_otp(order) {
            const context = this.env.session.user_context;
            const input_otp = document.getElementById('input-otp');
            const countdowntimer = document.getElementById('countdowntimer');
            let check_otp = 0;
            const client = this.env.pos.get_client();
            if (!context['cid_order']) {
                // add key in js
                context['cid_order'] = order.cid;
            }
            if (!context['phone_number']) {
                if (client) {
                    context['phone_number'] = client.phone;
                }

            }
            check_otp = await this.rpc({
                model: 's.res.partner.otp',
                method: 'check_screen_otp',
                args: [],
                context: context,
            });
            let self = this;
            if (check_otp) {
                if (window.intervalIDs.length > 0) {
                    window.intervalIDs.forEach(id => clearInterval(id));
                    window.intervalIDs = [];
                    if (countdowntimer){
                        countdowntimer.textContent = '';
                    }
                }
                if (input_otp) {
                    input_otp.value = '';
                }
                self.intervalId = setInterval(function () {
                    check_otp--;
                    if (countdowntimer) {
                        countdowntimer.textContent = check_otp + ' giây';
                    }
                    if (check_otp <= 0)
                        clearInterval(self.intervalId); // Use self instead of this
                }, 1000);
                window.intervalIDs.push(self.intervalId);
            } else {
                window.intervalIDs.push(self.intervalId);
                // Dừng tất cả các setInterval
                window.intervalIDs.forEach(id => clearInterval(id));
                window.intervalIDs = [];

                if (input_otp) {
                    input_otp.value = '';
                }
                if (countdowntimer) {
                    countdowntimer.textContent = '';
                }
            }
        }

        order_click_handler(order, event) {
            var s_lock_order = false;
            try {
                s_lock_order = window.s_lock_order
                if (typeof s_lock_order !== 'undefined' && !s_lock_order) {
                    this.env.pos.set_order(order);
                    this.render();
                }
            } catch (error) {
                console.log(error)
            }
            if (!s_lock_order) {
                this.env.pos.set_order(order);
                this.render();
            }
            var otp = document.getElementById('input-otp');
            var client = this.env.pos.get_client();
            if (this.env.pos.config.module_pos_loyalty && this.env.pos.loyalty) {
                if (this.env.pos.loyalty.zns_template_id) {
                    if (this.env.pos.loyalty.rewards.length > 0) {
                        var line_reward_id = this.env.pos.get_order().get_orderlines().map(line => line.reward_id);
                        var rewards_ids = this.env.pos.loyalty.rewards.map(reward => reward.id);
                        if (line_reward_id.some(id => rewards_ids.includes(id))) {
                            if (order && client) {
                                this._check_screen_otp(order);
                            }
                        }
                    }
                }
                // document.getElementById('input-otp').value = '';
            }

            // var selected_order = $('.order-selector .orders .selected')
            // var select_order = $(event.target)
            // if (selected_order.length > 0) {
            //     if (selected_order[0].className != select_order[0].className) {
            //         selected_order.removeClass("selected")
            //         if (!select_order.hasClass('select-order')) {
            //             select_order = select_order.parent();
            //         }
            //         select_order.addClass('selected')
            //     }
            //     this.env.pos.set_order(order);
            // }
        };

        neworder_click_handler() {
            this.env.pos.add_new_order()
            this.render();
        };

        async deleteorder_click_handler(event, $el) {
            var self = this;
            var order = this.env.pos.get_order();
            if (!order) {
                return;
            } else if (!order.is_empty()) {
                const {confirmed} = await this.showPopup('ConfirmPopup', {
                    'title': 'Destroy Current Order ?',
                    'body': 'You will lose any data associated with the current order',
                });
                if (confirmed) {
                    self.env.pos.delete_current_order();
                    this.render();
                }
            } else {
                this.env.pos.delete_current_order();
                this.render();
            }
        };

        async _onDeleteOrder() {
            var order = this.env.pos.get_order();
            const screen = order.get_screen_data();
            if (['ProductScreen', 'PaymentScreen'].includes(screen.name) && order.get_orderlines().length > 0) {
                const {confirmed} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Existing orderlines'),
                    body: _.str.sprintf(this.env._t('%s has a total amount of %s, are you sure you want to delete this order ?'), order.name, this.getTotal(order)),
                });
                if (!confirmed) return;
            }
            if (order && (await this._onBeforeDeleteOrder(order))) {
                this.env.pos.delete_current_order();
                this.env.pos.set_order(new PosModel.Order({}, {pos: this.env.pos}));
                this.env.pos.delete_current_order();
                this.env.pos.set_order(this.env.pos.get_order_list()[this.env.pos.get_order_list().length - 1]);
                this.render();
            }
        };

        getTotal(order) {
            return this.env.pos.format_currency(order.get_total_with_tax());
        };

        async _onBeforeDeleteOrder(order) {
            return true;
        };
    }

    SOrderSelectorWidget.template = 'BooOrderSelectorWidget';
    Registries.Component.add(SOrderSelectorWidget);
    return SOrderSelectorWidget;
});
