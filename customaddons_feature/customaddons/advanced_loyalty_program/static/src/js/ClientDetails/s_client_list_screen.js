odoo.define('advanced_loyalty_program.SClientListScreenEx', function (require) {
    "use strict";
    var ClientListScreen = require('point_of_sale.ClientListScreen');
    const Registries = require("point_of_sale.Registries");
    const SClientListScreenEx = (ClientListScreen) => class extends ClientListScreen {
        constructor() {
            super(...arguments);
        }

        //action set customer
        async clickNext() {
            ///Xóa hết line loyalty reward đi tránh trường hợp user không đủ điểm quy đổi reward -> loyalty points bị âm
            var current_order = this.currentOrder
            var reward_line_id = []
            if (typeof (this.env.pos.loyalty) !== "undefined"){
                for (let i = 0; i < current_order.orderlines.models.length; i++) {
                    var line = this.currentOrder.orderlines.models[i];
                    if (typeof (line.get_reward()) !== "undefined"){
                        reward_line_id.push(line.id)
                    }
                }
                if (reward_line_id.length){
                    const {confirmed} = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Thông báo'),
                        body: _.str.sprintf(
                            this.env._t('Đặt khách hàng sẽ xóa dòng phần thưởng trong đơn hàng. Bạn có muốn tiếp tục?'),
                        ),
                        cancelText: this.env._t('No'),
                        confirmText: this.env._t('Yes'),
                    });
                    if (confirmed) {
                        current_order.orderlines.remove(current_order.orderlines.filter((line) => reward_line_id.includes(line.id)));
                    } else {
                        return; // do nothing on the line
                    }
                }
            }
            if (this.state.selectedClient){
                var loadSetCustomer = await this.searchSetClient(this.state.selectedClient.id)
            }
            super.clickNext()
        }

        async searchSetClient(id){
            if (id) {
                let result = await this.getSetNewClient(id);
                if (!result.length) {
                    await this.showPopup('ErrorPopup', {
                        title: '',
                        body: this.env._t('No customer found'),
                    });
                }
                // this.env.pos.db.add_seclected_partners(result);
                // this.render();
                //load dữ liệu KH khi đặt KH
                this.state.selectedClient.total_period_revenue = result[0].total_period_revenue
                this.state.selectedClient.total_reality_revenue = result[0].total_reality_revenue
                this.state.selectedClient.total_sales_amount = result[0].total_sales_amount
                this.state.selectedClient.loyalty_points = result[0].loyalty_points
                this.state.selectedClient.customer_ranked = result[0].customer_ranked
                this.state.selectedClient.related_customer_ranked = result[0].related_customer_ranked

            }
        }

        async getSetNewClient(id) {
            var domain = [];
            if (id){
                domain = [["id", "=", id]]
            }
            var fields = _.find(this.env.pos.models, function(model){ return model.label === 'load_partners'; }).fields;
            var result = await this.rpc({
                model: 'res.partner',
                method: 'search_read',
                args: [domain, fields],
                kwargs: {
                    limit: 10,
                },
            },{
                timeout: 3000,
                shadow: true,
            });
            return result;
        }


    }
    Registries.Component.extend(ClientListScreen, SClientListScreenEx)
    return SClientListScreenEx

});

