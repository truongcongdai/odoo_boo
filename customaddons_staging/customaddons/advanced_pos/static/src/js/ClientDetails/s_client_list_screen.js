odoo.define('advanced_pos.SClientListScreen', function (require) {
    "use strict";
    var ClientListScreen = require('point_of_sale.ClientListScreen');
    const Registries = require("point_of_sale.Registries");
    const SClientListScreen = (ClientListScreen) => class extends ClientListScreen {
        constructor() {
            super(...arguments);
        }

        //confirm customer
        confirm(resolve) {
            if (resolve) {
                resolve({confirmed: true, payload: this.state.selectedClient});
                this.currentOrder.set_client(this.state.selectedClient);
                this.currentOrder.updatePricelist(this.state.selectedClient);
                return
            }
            super.confirm()
        }

        _onMouseOverSearchCustomer(){
            $(".searchbox-client input").focus();
        }

        //action set customer
        clickNext() {
            const s_boo_client_list = this.el.parentElement.dataset['isBooClient'];
            // this.env.pos.get_order().trigger('update-rewards');
            if (s_boo_client_list) {
                this.state.selectedClient = this.nextButton.command === 'set' ? this.state.selectedClient : null;
                //func resolve load selected client
                new Promise((resolve) => this.confirm(resolve));
                return
            }
            // this.confirm();
            super.clickNext()
        }

        // activateEditMode(event) {
        //     $("#top-search").hide();
        //     $(".s_button_back").hide();
        //     super.activateEditMode(event)
        // }

        // back(){
        //     $("#top-search").show();
        //     $("#top-search").css("opacity", "1");
        //     if($('.s_icon_customer').length < 1) {
        //         $(".s_customer_list").append("<span class='s_icon_customer'><i class='fa fa-user'></i></span>")
        //     }
        //     $(".s_icon_customer").show();
        //     $(".s_button_back").show();
        //     super.back()
        // }

        // async saveChanges(event){
        //     $("#top-search").show();
        //     $("#top-search").css("opacity", "1");
        //     $(".s_customer_list").append("<span class='s_icon_customer'><i class='fa fa-user'></i></span>")
        //     super.saveChanges(event)
        // }

        async editClient() {
            if(!this.state.selectedClient.country_id){
                this.state.selectedClient.country_id = this.env.pos.company.country_id
            }
            const s_boo_client_list = this.el.parentElement.dataset['isBooClient'];
            if (s_boo_client_list === undefined) {
                var partner_id = this.state.selectedClient;
                let pos_order_id = await this.rpc({
                    model: "pos.order",
                    method: "get_report_info_pos_order",
                    args: [1, partner_id.id],
                });
                if (pos_order_id[0].length > 0){
                    this.getRecentlyBill(pos_order_id)
                    this.getRecentlyPurchasedProducts(pos_order_id)
                    this.getBrandCateg(pos_order_id)
                }
            }
            super.editClient()
        }

        ///Danh sách hóa đơn gần nhất
         getRecentlyBill(pos_order_id) {
            var partner = this.state.selectedClient;

            if (pos_order_id){
                partner.recently_bill = pos_order_id[0]
            }
        }

        ///Danh sách sản phẩm mua gần nhất
        getRecentlyPurchasedProducts(pos_order_id) {
            var partner = this.state.selectedClient;
            var product_ids = [].concat.apply([], pos_order_id[0].map(order => order.details_product));
            if (product_ids){
                partner.recently_purchase_product = product_ids
            }
        }

        ///Danh sách nhóm thương hiệu sản phẩm
        getBrandCateg(pos_order_id) {
            var partner = this.state.selectedClient;
            if (pos_order_id[1]){
                partner.brand_category = pos_order_id[1]
            }
        }

    }
    Registries.Component.extend(ClientListScreen, SClientListScreen)
    return SClientListScreen

});

