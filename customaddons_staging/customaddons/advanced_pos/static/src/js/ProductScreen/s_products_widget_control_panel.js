odoo.define('advanced_pos.SProductsWidgetControlPanel', function (require) {
    'use strict';
    const {useState, useRef, onPatched, useComponent} = owl.hooks;
    const Registries = require("point_of_sale.Registries");
    const ProductsWidgetControlPanel = require("point_of_sale.ProductsWidgetControlPanel");
    const {useListener} = require("web.custom_hooks");
    const models = require('point_of_sale.models');
    const { Gui } = require('point_of_sale.Gui');
    const SProductsWidgetControlPanel = (ProductsWidgetControlPanel) => class extends ProductsWidgetControlPanel {
        constructor() {
            super(...arguments);
        }

        updateSearch(event) {
            //hien thi product list
            var product_item_dialog = $(".search-bar-portal .s_search_product_item_dialog")
            if (product_item_dialog.length > 0) {
                product_item_dialog[0].style.display = 'block'
            } else {
                var ProductsWidget = $(".s_search_product_item_dialog");
                ProductsWidget.insertAfter($(".search-box"));
            }
            this.trigger('update-search', event.target.value);
            if (event.key === 'Enter') {
                if ($('.s_search_product_item').length == 1) {
                    $('.s_search_product_item').click();
                }
            }
        }

        _showProductListSearchBox() {
            const product_item_dialog = $(".s_search_product_item_dialog");
            const product_item_dialog_bar_portal = $(".search-bar-portal .s_search_product_item_dialog");
            if (product_item_dialog_bar_portal.length > 0) {
                product_item_dialog[0].style.display = 'block'
            } else {
                product_item_dialog.insertAfter($(".search-box"));
            }
        }

        async loadProductFromDB() {
            if(!this.searchWordInput.el.value)
                this.searchWordInput.el.value = '';
            try {
                let ProductIds = await this.rpc({
                    model: 'product.product',
                    method: 'search',
                    args: [['&', ['name', 'ilike', this.searchWordInput.el.value + "%"], ['available_in_pos', '=', true]]],
                    context: this.env.session.user_context,
                });
                if(!ProductIds.length) {
                    this.showPopup('ErrorPopup', {
                        title: '',
                        body: this.env._t("Không tìm thấy sản phẩm mới"),
                    });
                } else {
                    await this.env.pos._addProducts(ProductIds, false);
                    Gui.showNotification('Tải sản phẩm thành công!');
                }
                this.trigger('update-product-list');
            } catch (error) {
                const identifiedError = identifyError(error)
                if (identifiedError instanceof ConnectionLostError || identifiedError instanceof ConnectionAbortedError) {
                    return this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t("Product is not loaded. Tried loading the product from the server but there is a network error."),
                    });
                } else {
                    throw error;
                }
            }
        }
    }
    Registries.Component.extend(ProductsWidgetControlPanel, SProductsWidgetControlPanel)
    return SProductsWidgetControlPanel
})