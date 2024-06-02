odoo.define('advanced_pos.SChrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const ClientListScreen = require('point_of_sale.ClientListScreen');

    const SChrome = (Chrome) => class extends Chrome {
        constructor() {
            super(...arguments);
            // ClientListScreen.updateClientList()
        }

        // async _updateClientList(event) {
        //     var newClientList = await this.getNewClient();
        //     this.state.query = event.target.value;
        //     const clients = this.clients;
        //     if (event.code === 'Enter' && clients.length === 1) {
        //         this.state.selectedClient = clients[0];
        //         this.clickNext();
        //     } else {
        //         this.render();
        //     }
        // }
        //
        // async getNewClient() {
        //     var domain = [];
        //     if (this.state.query) {
        //         domain = [["name", "ilike", this.state.query + "%"]];
        //     }
        //     var fields = _.find(this.env.pos.models, function (model) {
        //         return model.label === 'load_partners';
        //     }).fields;
        //     var result = await this.rpc({
        //         model: 'res.partner', method: 'search_read', args: [domain, fields], kwargs: {
        //             limit: 10,
        //         },
        //     }, {
        //         timeout: 3000, shadow: true,
        //     });
        //
        //     return result;
        // }

        get clients() {
            let res;
            if (this.state.query && this.state.query.trim() !== '') {
                res = this.env.pos.db.search_partner(this.state.query.trim());
            } else {
                res = this.env.pos.db.get_partners_sorted(1000);
            }
            return res.sort(function (a, b) {
                return (a.name || '').localeCompare(b.name || '')
            });
        }

        clickNext() {
            this.state.selectedClient = this.nextButton.command === 'set' ? this.state.selectedClient : null;
            this.confirm();
        }

        _searchCustomer(event){
            // var search_box = $('.s_clientlist_screen .searchbox-client')
            // search_box.insertAfter($("#top-search"));
            // $("#top-search").css("opacity", "0");
            // var icon_search_box = $('.s_icon_customer');
            // icon_search_box.insertAfter($(".searchbox-client input"));
            // $(".searchbox-client input:first").focus();
            // // remove if exists old searchbox
            // if($(".searchbox-client").length > 1) {
            //     $(".searchbox-client:last").remove();
            // }
        }

        //an search product list
        _onMouseMoveHiddenProductList(event) {
            var classCurrent = event.target.className
            var product_item_dialog_bar_portal = $(".search-bar-portal .s_search_product_item_dialog")
            var product_item_dialog = $(".s_search_product_item_dialog")
            if (product_item_dialog.length > 0) {
                if (classCurrent.length > 0) {
                    if (classCurrent !== 'search-bar-portal' && classCurrent !== 'search-box' && !classCurrent.includes("s_search_product_item")) {
                        if (product_item_dialog.length > 1) {
                            product_item_dialog_bar_portal.remove()
                        } else {
                            product_item_dialog[0].style.display = 'none'
                        }
                    }
                }
            }
        }
    };
    Registries.Component.extend(Chrome, SChrome);
    return SChrome;
});
