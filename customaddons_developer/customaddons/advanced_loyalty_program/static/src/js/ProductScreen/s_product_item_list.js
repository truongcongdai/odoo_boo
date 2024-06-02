odoo.define('point_of_sale.SProductItemList', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    class SProductItemList extends PosComponent {
        constructor() {
            super(...arguments);
            // useListener('s-click-pay', this._onClickPayAdvanced);
            useListener('boo-click-product', this._booClickProduct);
        }

        //an product list khi tro chuot ra ngoai product list
        async _onMouseLeaveProductItem(ev) {
            var product_item_dialog = $(".search-bar-portal .s_search_product_item_dialog")
            if (product_item_dialog.length > 0) {
                product_item_dialog[0].style.display = 'none'
            }
        }

        get pricelist() {
            const current_order = this.env.pos.get_order();
            if (current_order) {
                return current_order.pricelist;
            }
            return this.env.pos.default_pricelist;
        }

        get price() {
            const formattedUnitPrice = this.env.pos.format_currency(this.product.get_price(this.pricelist, 1), 'Product Price');
            if (this.product.to_weight) {
                return `${formattedUnitPrice}/${this.env.pos.units_by_id[this.product.uom_id[0]].name}`;
            } else {
                return formattedUnitPrice;
            }
        }

        async _booClickProduct(event) {
            var reward_line
            var order_lines = this.env.pos.get_order().get_orderlines()
            if (order_lines.length > 0){
                reward_line = order_lines.filter((line) => line.reward_id)
                if (reward_line.length > 0) {
                    const {confirmed} = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Thông báo'),
                        body: _.str.sprintf(
                            this.env._t('Thêm sản phẩm mới sẽ xóa dòng phần thưởng trong đơn hàng. Bạn có muốn tiếp tục?'),
                        ),
                        cancelText: this.env._t('No'),
                        confirmText: this.env._t('Yes'),
                    });
                    if (confirmed) {
                        this.env.pos.get_order().remove_orderline(reward_line)
                    } else {
                        return; // do nothing on the line
                    }
                }
            }
            var self = this
            var qty_available = await this.rpc({
                model: 'product.product',
                method: 'get_product_quantities',
                args: [event.detail.id,this.env.pos.picking_type.id],
                kwargs: {context: this.env.session.user_context},
            });
            // var currentQuant = parseInt($(".product-name:contains('" + event.detail.display_name + "')").closest('li').find(':input[type="number"]').val()) + 1;
            // if (isNaN(currentQuant)) {
            //     currentQuant = 0;
            // }
            var current_order = this.env.pos.get_order()
            var currentQuant = 0;
            var order_line_id = current_order.orderlines.models.filter(l => l.product.default_code === event.detail.default_code)
            if(order_line_id.length > 0){
                currentQuant = order_line_id[0].quantity
            }
            if (event.detail.type !='product') {
                if (!current_order) {
                    this.env.pos.add_new_order();
                }
                const product = event.detail;
                const options = this._getAddProductOptions(product);
                if (!options) return;
                current_order.add_product(product, options);
                NumberBuffer.reset();
            } else if (qty_available > 0 && qty_available > currentQuant && event.detail.type =='product') {
                if (!current_order) {
                    this.env.pos.add_new_order();
                }
                const product = event.detail;
                const options = this._getAddProductOptions(product);
                if (!options) return;
                current_order.add_product(product, options);
                NumberBuffer.reset();
            } else {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Lỗi người dùng"),
                    body: this.env._t("Sản phẩm trong kho không đủ."),
                });
                return;
            }
        }

        async _getAddProductOptions(product, base_code) {
            let price_extra = 0.0;
            let draftPackLotLines, weight, description, packLotLinesToEdit;

            if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                                  .filter((attr) => attr !== undefined);
                let { confirmed, payload } = await this.showPopup('ProductConfiguratorPopup', {
                    product: product,
                    attributes: attributes,
                });

                if (confirmed) {
                    description = payload.selected_attributes.join(', ');
                    price_extra += payload.price_extra;
                } else {
                    return;
                }
            }

            // Gather lot information if required.
            if (['serial', 'lot'].includes(product.tracking) && (this.env.pos.picking_type.use_create_lots || this.env.pos.picking_type.use_existing_lots)) {
                const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                if (isAllowOnlyOneLot) {
                    packLotLinesToEdit = [];
                } else {
                    const orderline = this.currentOrder
                        .get_orderlines()
                        .filter(line => !line.get_discount())
                        .find(line => line.product.id === product.id);
                    if (orderline) {
                        packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                    } else {
                        packLotLinesToEdit = [];
                    }
                }
                const { confirmed, payload } = await this.showPopup('EditListPopup', {
                    title: this.env._t('Lot/Serial Number(s) Required'),
                    isSingleItem: isAllowOnlyOneLot,
                    array: packLotLinesToEdit,
                });
                if (confirmed) {
                    // Segregate the old and new packlot lines
                    const modifiedPackLotLines = Object.fromEntries(
                        payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                    );
                    const newPackLotLines = payload.newArray
                        .filter(item => !item.id)
                        .map(item => ({ lot_name: item.text }));

                    draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                } else {
                    // We don't proceed on adding product.
                    return;
                }
            }

            // Take the weight if necessary.
            if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
                // Show the ScaleScreen to weigh the product.
                if (this.isScaleAvailable) {
                    const { confirmed, payload } = await this.showTempScreen('ScaleScreen', {
                        product,
                    });
                    if (confirmed) {
                        weight = payload.weight;
                    } else {
                        // do not add the product;
                        return;
                    }
                } else {
                    await this._onScaleNotAvailable();
                }
            }

            if (base_code && this.env.pos.db.product_packaging_by_barcode[base_code.code]) {
                weight = this.env.pos.db.product_packaging_by_barcode[base_code.code].qty;
            }

            return { draftPackLotLines, quantity: weight, description, price_extra };
        }

    }

    SProductItemList.template = 'advanced_pos.SProductItemList';
    Registries.Component.add(SProductItemList);
    return SProductItemList;
});
