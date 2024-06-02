odoo.define("advanced_pos.FreeProductPopup", function (require) {
    "use strict";

    const {useState, useRef, onPatched, useComponent} = owl.hooks;
    const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
    const Registries = require("point_of_sale.Registries");
    const {useListener} = require("web.custom_hooks");
    var rpc = require('web.rpc');
    const {Gui} = require('point_of_sale.Gui');

    class FreeProductPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.props.cancelFreeProduct = false;
            this.props.unavailableQty = false;
        }

        async get_free_products() {
            return await this.rpc({
                model: "product.product",
                method: "search_read",
                args: [[["id", "=", this.props.free_products]]],
            })
        }

        confirm_free_product(event) {
            try {
                var self = this
                var free_products = this.props.free_products
                var products = this.props.products
                let selectedLine = this.env.pos.get_order().get_selected_orderline();
                // Danh dau san pham duoc ap dung CTKM tang nhieu san pham
                if (selectedLine) {
                    selectedLine.is_multi_free_product = true;
                }
                if (free_products) {
                    for (let i = 0; free_products.length > i; i++) {
                        var e = document.getElementById("s_free_product");
                        var value = e.value;
                        if (free_products[i].id === parseInt(value) && value) {
                            // this.pos.db.get_product_by_id(value)
                            let currentOrder = this.env.pos.get_order()
                            if (currentOrder) {
                                let newRewardLines = this.props.newRewardLines
                                // change price reward
                                // insert sku free product
                                // newRewardLines[0].product.display_name = newRewardLines[0].product.display_name + ' - ' + free_products[i].default_code
                                const qty_available = rpc.query({
                                    model: 'product.product',
                                    method: 'get_product_quantities',
                                    args: [free_products[i].id, this.env.pos.picking_type.id],
                                    kwargs: {context: this.env.session.user_context},
                                }).then(function (qty_available) {
                                    const productQty = currentOrder.orderlines.models.filter((line)=> line.product.id==free_products[i].id).map(l => l.quantity).reduce((a, b) => a + b, 0)
                                    if (free_products[i].type !== 'product' || productQty+1 <= qty_available) {
                                        if (newRewardLines.length > 0) {
                                            newRewardLines[0].price = -free_products[i].get_price(self.env.pos.pricelists[0], 1)
                                            for (var j = 0; products.length > j; j++) {
                                                if (parseInt(products[j].s_free_product_id) === free_products[i].id && products[j].s_free_product_id) {
                                                    newRewardLines[0].product = products[j]
                                                    var oldRewardLines = currentOrder.orderlines.filter((line) => line.product.id == products[j].id && line.is_program_reward && line.product.s_free_product_id)
                                                    if (oldRewardLines.length > 0) {
                                                        // oldRewardLines[0].set_quantity(oldRewardLines[0].quantity + 1);
                                                        oldRewardLines[0].set_quantity(oldRewardLines[0].quantity + 1,-free_products[i].get_price(self.env.pos.pricelists[0], oldRewardLines[0].quantity + 1));

                                                        // newRewardLines[0].quantity = oldRewardLines[0].quantity
                                                        // currentOrder.orderlines.add(newRewardLines, {
                                                        //     merge: true,
                                                        // });
                                                        // currentOrder.orderlines.remove(oldRewardLines);
                                                    } else {
                                                        newRewardLines[0].quantity = 1
                                                        var newRewardLine = currentOrder.orderlines.add(newRewardLines[0]);
                                                        if (newRewardLine) {
                                                            // price_manually_set = true de khong thay doi gia san pham duoc tang trong func updatePricelist
                                                            newRewardLine.price_manually_set=true;
                                                            newRewardLine.set_quantity(1,-free_products[i].get_price(self.env.pos.pricelists[0], 1));
                                                        }
                                                        // currentOrder.orderlines.remove(oldRewardLines);
                                                    }
                                                }
                                            }
                                        }
                                        var freeProducts = currentOrder.orderlines.models.filter((line) => line.product.id == free_products[i].id);
                                        // free_products[i].s_is_free_product = true
                                        currentOrder.add_product(free_products[i], {
                                            merge: true,
                                            s_is_free_product: true,
                                            is_multi_free_product: true,
                                        })
                                        // if (freeProducts.length === 0){
                                        //     currentOrder.add_product(free_products[i], {
                                        //         merge: true,
                                        //         s_is_free_product: true,
                                        //     })
                                        // }
                                        // We need this for the rendering of ActivePrograms component.
                                        currentOrder.activeMultiFreeProducts = false;
                                        currentOrder.rewardsContainer = self.props.rewardsContainer;
                                        // Send a signal that the rewardsContainer are updated.
                                        currentOrder.trigger('update-rewards');
                                        currentOrder.trigger('rewards-updated');
                                        self.confirm();
                                    } else {
                                        self.props.unavailableQty = true;
                                        self.render()
                                        // Gui.showPopup('ErrorPopup', {
                                        //     title: "Lỗi người dùng",
                                        //     body: "Sản phẩm trong kho không đủ.",
                                        // });
                                    }
                                });
                            }
                        }
                    }
                }
            } catch (e) {
                console.log(e)
            }
        }

        cancel_free_product() {
            this.props.cancelFreeProduct = true;
            this.render()
            // let currentOrder = this.env.pos.get_order()
            // currentOrder.trigger('rewards-updated');
        }

        confirm_free_product_popup() {
            // if (this.props.newRewardLines) {
            //     for (var r = 0; r < this.props.newRewardLines.length; r++) {
            //         var order_line_free = this.env.pos.get_order().orderlines.models.filter(item => item.product.id === this.props.newRewardLines[r].product.id
            //             && this.props.newRewardLines[r].product.s_free_product_id)
            //         if (order_line_free) {
            //             this.env.pos.get_order().remove_orderline(order_line_free[0])
            //         }
            //     }
            // }
            this.cancel();
        }

        cancel_free_product_popup() {
            this.props.cancelFreeProduct = false;
            this.render()
        }
        confirm_unavailable_qty(){
            this.props.unavailableQty = false;
            this.render()
        }
    }


    FreeProductPopup.template = "FreeProductPopup";

    Registries.Component.add(FreeProductPopup);

    return FreeProductPopup;
});
