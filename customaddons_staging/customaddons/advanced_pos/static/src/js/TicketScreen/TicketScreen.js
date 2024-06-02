odoo.define('advanced_pos.TicketScreen', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const TicketScreen = require('point_of_sale.TicketScreen');
    const models = require('point_of_sale.models');
    const TicketScreenInherit = (TicketScreen) => class extends TicketScreen {
        constructor() {
            super(...arguments);

        }

        async _fetchSyncedOrders() {
            const domain = this._computeSyncedOrdersDomain();
            const limit = this._state.syncedOrders.nPerPage;
            const offset = (this._state.syncedOrders.currentPage - 1) * this._state.syncedOrders.nPerPage;
            if (this._state.ui.filter == 'SYNCED_ALL') {
                const {ids, totalCount} = await this.rpc({
                    model: 'pos.order',
                    method: 'search_paid_order_ids',
                    kwargs: {config_id: [], domain, limit, offset},
                    context: this.env.session.user_context,
                });
                const idsNotInCache = ids.filter((id) => !(id in this._state.syncedOrders.cache));
                if (idsNotInCache.length > 0) {
                    const fetchedOrders = await this.rpc({
                        model: 'pos.order',
                        method: 'export_for_ui',
                        args: [idsNotInCache],
                        context: this.env.session.user_context,
                    });
                    // Check for missing products and load them in the PoS
                    await this.env.pos._loadMissingProducts(fetchedOrders);
                    // Cache these fetched orders so that next time, no need to fetch
                    // them again, unless invalidated. See `_onInvoiceOrder`.
                    fetchedOrders.forEach((order) => {
                        this._state.syncedOrders.cache[order.id] = new models.Order({}, {
                            pos: this.env.pos,
                            json: order
                        });
                    });
                }
                this._state.syncedOrders.totalCount = totalCount;
                this._state.syncedOrders.toShow = ids.map((id) => this._state.syncedOrders.cache[id]);
            } else {
                const {ids, totalCount} = await this.rpc({
                    model: 'pos.order',
                    method: 'search_paid_order_ids',
                    kwargs: {config_id: this.env.pos.config.id, domain, limit, offset},
                    context: this.env.session.user_context,
                });
                const idsNotInCache = ids.filter((id) => !(id in this._state.syncedOrders.cache));
                if (idsNotInCache.length > 0) {
                    const fetchedOrders = await this.rpc({
                        model: 'pos.order',
                        method: 'export_for_ui',
                        args: [idsNotInCache],
                        context: this.env.session.user_context,
                    });
                    // Check for missing products and load them in the PoS
                    await this.env.pos._loadMissingProducts(fetchedOrders);
                    // Cache these fetched orders so that next time, no need to fetch
                    // them again, unless invalidated. See `_onInvoiceOrder`.
                    fetchedOrders.forEach((order) => {
                        this._state.syncedOrders.cache[order.id] = new models.Order({}, {
                            pos: this.env.pos,
                            json: order
                        });
                    });
                }
                this._state.syncedOrders.totalCount = totalCount;
                this._state.syncedOrders.toShow = ids.map((id) => this._state.syncedOrders.cache[id]);
            }

        }

        getFilteredOrderList() {
            // Show all orders if no filter is selected
            if (this._state.ui.filter == 'SYNCED' || this._state.ui.filter == 'SYNCED_ALL') return this._state.syncedOrders.toShow;
            const filterCheck = (order) => {
                if (this._state.ui.filter && this._state.ui.filter !== 'ACTIVE_ORDERS') {
                    const screen = order.get_screen_data();
                    return this._state.ui.filter === this._getScreenToStatusMap()[screen.name];
                }
                return true;
            };
            const {fieldName, searchTerm} = this._state.ui.searchDetails;
            const searchField = this._getSearchFields()[fieldName];
            const searchCheck = (order) => {
                if (!searchField) return true;
                const repr = searchField.repr(order);
                if (repr === null) return true;
                if (!searchTerm) return true;
                return repr && repr.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (order) => {
                return filterCheck(order) && searchCheck(order);
            };
            return this._getOrderList().filter(predicate);
        }

        async _onFilterSelected(event) {
            // Add event selected filter SYNCED_ALL
            this._state.ui.filter = event.detail.filter;
            if (this._state.ui.filter == 'SYNCED') {
                await this._fetchSyncedOrders();
            } else if (this._state.ui.filter == 'SYNCED_ALL') {
                await this._fetchSyncedOrders();
            }
            this.render();
        }

        _getRefundableDetails(customer) {
            return Object.values(this.env.pos.toRefundLines).filter(
                ({qty, orderline, destinationOrderUid}) =>
                    !this.env.pos.isProductQtyZero(qty) &&
                    (customer ? orderline.orderPartnerId == customer.id : true) &&
                    !destinationOrderUid
            );
        }

        _doesOrderHaveSoleItem(order) {
            const orderlines = order.get_orderlines();
            if (orderlines.length !== 1) return false;
            const theOrderline = orderlines[0];
            const refundableQty = theOrderline.get_quantity() - theOrderline.refunded_qty;
            return this.env.pos.isProductQtyZero(refundableQty - 1);
        }

        _prepareAutoRefundOnOrder(order) {
            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.models.find((line) => line.id == selectedOrderlineId);
            if (!orderline) return;

            const toRefundDetail = this._getToRefundDetail(orderline);
            const refundableQty = orderline.get_quantity() - orderline.refunded_qty;
            if (this.env.pos.isProductQtyZero(refundableQty - 1)) {
                toRefundDetail.qty = 1;
            }
        }

        _prepareRefundOrderlineOptions(toRefundDetail) {
            const {qty, orderline} = toRefundDetail;
            return {
                quantity: -qty,
                price: orderline.price,
                extras: {price_manually_set: true},
                merge: false,
                refunded_orderline_id: orderline.id,
                tax_ids: orderline.tax_ids,
                discount: orderline.discount,
            }
        }

        _onCloseScreen() {
            this.close();
        }

        async _onDoRefund() {
            const order = this.getSelectedSyncedOrder();
            if (!order) {
                this._state.ui.highlightHeaderNote = !this._state.ui.highlightHeaderNote;
                return this.render();
            }

            if (this._doesOrderHaveSoleItem(order)) {
                this._prepareAutoRefundOnOrder(order);
            }

            const customer = order.get_client();

            var allToRefundDetails = this._getRefundableDetails(customer)
            // Refund gift card có chọn qty sẽ xóa line gift card để đưa về giống auto
            var giftProduct = this.env.pos.db.product_by_id[this.env.pos.config.gift_card_product_id[0]];
            if (typeof (giftProduct) !== "undefined") {
                allToRefundDetails = allToRefundDetails.filter(product => product.orderline.productId != this.env.pos.config.gift_card_product_id[0])
            }
            // remove global coupon product of allToRefundDetails
            var newAllToRefundDetails = [];
            for (let i = 0; i < allToRefundDetails.length; i++) {
                var is_global_discount_product = false;
                for (let c = 0; c < this.env.pos.promo_programs.length; c++) {
                    if (allToRefundDetails[i].orderline.productId === this.env.pos.promo_programs[c].discount_line_product_id[0]) {
                        is_global_discount_product = true
                    }
                }
                if (is_global_discount_product === false) {
                    newAllToRefundDetails.push(allToRefundDetails[i])
                }
                if(newAllToRefundDetails.length > 0){
                    for (let l = 0; l < this.env.pos.promo_programs.length; l++) {
                        if (allToRefundDetails[i].orderline.productId === this.env.pos.promo_programs[l].discount_line_product_id[0]
                            && (this.env.pos.promo_programs[l].reward_type !== 'discount' ||
                            this.env.pos.promo_programs[l].discount_type === 'fixed_amount')) {
                            newAllToRefundDetails.push(allToRefundDetails[i])
                        }
                    }
                }
            }
            allToRefundDetails = newAllToRefundDetails;

            var total_price_order = 0
            var total_price_free_product = 0
            for (let i = 0; i < allToRefundDetails.length; i++) {
                if (allToRefundDetails[i].orderline.price > 0) {
                    total_price_order += allToRefundDetails[i].orderline.price * allToRefundDetails[i].qty
                }
                ///Nếu line là sản phẩm được tặng
                else if (allToRefundDetails[i].orderline.price < 0) {
                    var get_product = this.env.pos.db.get_product_by_id(allToRefundDetails[i].orderline.productId)
                    ///TH1: CTKM tặng nhiều sản phẩm
                    if (get_product.s_free_product_id){
                        total_price_free_product += allToRefundDetails[i].orderline.price * allToRefundDetails[i].qty
                    }
                    ///TH2: CTKM tặng 1 sản phẩm
                    else {
                        for (let l = 0; l < this.env.pos.promo_programs.length; l++) {
                            if (allToRefundDetails[i].orderline.productId === this.env.pos.promo_programs[l].discount_line_product_id[0] &&
                            this.env.pos.promo_programs[l].reward_type === 'product') {
                                total_price_free_product += allToRefundDetails[i].orderline.price * allToRefundDetails[i].qty
                            }
                        }
                    }
                }
            }
            if (total_price_free_product !== 0){
                total_price_order += total_price_free_product
            }
            // Tìm tổng tiền đơn hàng gốc (không tính khuyến mại, quà tặng)
            var total_price_src_order = 0
            try {
                for (let k = 0; k < order.orderlines.models.length; k++){
                    if (order.orderlines.models[k].price > 0){
                        total_price_src_order += order.orderlines.models[k].price * order.orderlines.models[k].quantity
                    }
                }
            } catch (error){
            }
            var program_cheapest_ids = []
            for (let i = 0; i < order.orderlines.models.length; i++) {
                if (order.orderlines.models[i].price < 0) {
                    var coupon_price = 0
                    // Chương trình khuyến mãi
                    for (let c = 0; c < this.env.pos.promo_programs.length; c++) {
                        if (order.orderlines.models[i].product.id === this.env.pos.promo_programs[c].discount_line_product_id[0]) {
                            if (this.env.pos.promo_programs[c].reward_type === 'discount' && this.env.pos.promo_programs[c].discount_type === 'percentage') {
                                var check_product_discount = false
                                var total_product_discount = 0
                                var discount_product_ids = this.env.pos.promo_programs[c].discount_specific_product_ids
                                for (let z = 0; z < allToRefundDetails.length; z++) {
                                    if([...discount_product_ids].includes(allToRefundDetails[z].orderline.productId)){
                                        check_product_discount = true
                                        total_product_discount += allToRefundDetails[z].orderline.price * allToRefundDetails[z].qty
                                    }
                                }

                                if(this.env.pos.promo_programs[c].free_discount_cheapest_products){
                                    coupon_price = -(this.env.pos.promo_programs[c].discount_percentage * (order.orderlines.models[i].price * order.orderlines.models[i].quantity) / 100)
                                }else if(this.env.pos.promo_programs[c].discount_apply_on === 'cheapest_product'){
                                    var product_orderline_refund = allToRefundDetails.filter(line=>line.orderline.price > 0)
                                    var cheapestLine = product_orderline_refund.reduce((min_line, line) => {
                                        if (line.orderline.price < min_line.orderline.price && line.orderline.price >= 0) {
                                            return line;
                                        } else {
                                            return min_line;
                                        }
                                    }, product_orderline_refund[0]);
                                    if(cheapestLine.orderline.price === -order.orderlines.models[i].price && order.orderlines.models[i].product.id === this.env.pos.promo_programs[c].discount_line_product_id[0]){
                                        coupon_price = this.env.pos.promo_programs[c].discount_percentage * cheapestLine.orderline.price / 100
                                    }
                                }else if(check_product_discount === true && this.env.pos.promo_programs[c].discount_apply_on === 'specific_products'){
                                    coupon_price = this.env.pos.promo_programs[c].discount_percentage * total_product_discount / 100
                                }else if(this.env.pos.promo_programs[c].discount_apply_on !== 'specific_products'){
                                    coupon_price = this.env.pos.promo_programs[c].discount_percentage * total_price_order / 100
                                }
                            }

                            // if (this.env.pos.promo_programs[c].reward_type === 'discount' && this.env.pos.promo_programs[c].discount_type === 'percentage') {
                            //     if(this.env.pos.promo_programs[c].free_discount_cheapest_products){
                            //         coupon_price = -(this.env.pos.promo_programs[c].discount_percentage * (order.orderlines.models[i].price * order.orderlines.models[i].quantity) / 100)
                            //     }else{
                            //         coupon_price = this.env.pos.promo_programs[c].discount_percentage * total_price_order / 100
                            //     }
                            // }else if (this.env.pos.promo_programs[c].reward_type === 'discount' && this.env.pos.promo_programs[c].discount_type === 'percentage' && this.env.pos.promo_programs[c].discount_apply_on === 'cheapest_product') {
                            //     var product_orderline_refund = allToRefundDetails.filter(line=>line.orderline.price > 0)
                            //     var cheapestLine = product_orderline_refund.reduce((min_line, line) => {
                            //         if (line.price < min_line.price && line.price >= 0) {
                            //             return line;
                            //         } else {
                            //             return min_line;
                            //         }
                            //     }, product_orderline_refund[0]);
                            //     coupon_price = this.env.pos.promo_programs[c].discount_percentage * cheapestLine.orderline.price / 100
                            // }
                        }
                    }
                    // Chương trình phiếu giảm giá
                    for (let d = 0; d < this.env.pos.coupon_programs.length; d++) {
                        if (order.orderlines.models[i].product.id === this.env.pos.coupon_programs[d].discount_line_product_id[0]) {
                            if (this.env.pos.coupon_programs[d].reward_type === 'discount' && this.env.pos.coupon_programs[d].discount_type === 'percentage'){
                                coupon_price = this.env.pos.coupon_programs[d].discount_percentage * total_price_order / 100
                            }
                        }
                    }
                    // DungNH: auto add gift card
                    try {
                        let giftProduct = this.env.pos.db.product_by_id[this.env.pos.config.gift_card_product_id[0]];
                        if (typeof (giftProduct) !== "undefined") {
                            if (order.orderlines.models[i].product.id === giftProduct.id) {
                                // check da ton tai chua
                                var product_list_rf = []
                                for (let d = 0; d < allToRefundDetails.length; d++) {
                                    product_list_rf.push(allToRefundDetails[d].orderline.productId)
                                }
                                if (product_list_rf.includes(giftProduct.id) === false) {
                                    if (total_price_src_order > 0) {
                                        coupon_price = Math.round(order.orderlines.models[i].price * order.orderlines.models[i].quantity * -1 * ((total_price_order-total_price_free_product)/total_price_src_order))
                                    }
                                }
                            }
                        }
                    } catch (error){
                    }
                    if (coupon_price > 0) {
                        var autoRefund = allToRefundDetails.filter(l => l.orderline.id === order.orderlines.models[i].id)
                        if (!autoRefund.length && order.orderlines.models[i].quantity > 0) {
                            allToRefundDetails.push({
                                "qty": order.orderlines.models[i].quantity,
                                "orderline": {
                                    "id": order.orderlines.models[i].id,
                                    "productId": order.orderlines.models[i].product.id,
                                    "price": -coupon_price,
                                    "qty": -(order.orderlines.models[i].quantity),
                                    "refundedQty": 0,
                                    "orderUid": order.orderlines.models[i].order.uid,
                                    "orderBackendId": order.orderlines.models[i].order.backendId,
                                    "orderPartnerId": order.orderlines.models[i].order.user_id,
                                    "tax_ids": [],
                                    "discount": 0
                                },
                                "destinationOrderUid": false
                            })
                        }
                    }
                    // Xóa CTKM khói POS, return order tự động thêm line CTKM
                    var line_coupon_program_id = await this.rpc({
                        model: "pos.order.line",
                        method: 'search_read',
                        args: [[["id", "=", order.orderlines.models[i].id]]],
                    })
                    if(line_coupon_program_id.length > 0){
                        if(line_coupon_program_id[0].program_id.length > 0){
                            if(line_coupon_program_id[0].coupon_id.length > 0){
                                if(this.env.pos.coupon_programs.filter(item => item.id === line_coupon_program_id[0].program_id[0]).length === 0 && order.orderlines.models[i].product.type === 'service'){
                                    var autoRefund_coupon = allToRefundDetails.filter(l => l.orderline.id === order.orderlines.models[i].id)
                                    if(!autoRefund_coupon.length && order.orderlines.models[i].quantity > 0){
                                        allToRefundDetails.push({
                                            "qty": order.orderlines.models[i].quantity,
                                            "orderline": {
                                                "id": order.orderlines.models[i].id,
                                                "productId": order.orderlines.models[i].product.id,
                                                "price": order.orderlines.models[i].price,
                                                "qty": -(order.orderlines.models[i].quantity),
                                                "refundedQty": 0,
                                                "orderUid": order.orderlines.models[i].order.uid,
                                                "orderBackendId": order.orderlines.models[i].order.backendId,
                                                "orderPartnerId": order.orderlines.models[i].order.user_id,
                                                "tax_ids": [],
                                                "discount": 0
                                            },
                                            "destinationOrderUid": false
                                        })
                                    }
                                }
                            }else{
                                if(this.env.pos.promo_programs.filter(item => item.id === line_coupon_program_id[0].program_id[0]).length === 0 && order.orderlines.models[i].product.type === 'service'){
                                    var autoRefund_coupon = allToRefundDetails.filter(l => l.orderline.id === order.orderlines.models[i].id)
                                    if(!autoRefund_coupon.length && order.orderlines.models[i].quantity > 0){
                                        allToRefundDetails.push({
                                            "qty": order.orderlines.models[i].quantity,
                                            "orderline": {
                                                "id": order.orderlines.models[i].id,
                                                "productId": order.orderlines.models[i].product.id,
                                                "price": order.orderlines.models[i].price,
                                                "qty": -(order.orderlines.models[i].quantity),
                                                "refundedQty": 0,
                                                "orderUid": order.orderlines.models[i].order.uid,
                                                "orderBackendId": order.orderlines.models[i].order.backendId,
                                                "orderPartnerId": order.orderlines.models[i].order.user_id,
                                                "tax_ids": [],
                                                "discount": 0
                                            },
                                            "destinationOrderUid": false
                                        })
                                    }
                                }
                            }
                            var program_cheapest_id = this.env.pos.promo_programs.filter(item => item.id === line_coupon_program_id[0].program_id[0])
                            if(program_cheapest_id.length > 0){
                                if(program_cheapest_id[0].free_discount_cheapest_products && !program_cheapest_ids.includes(program_cheapest_id[0])){
                                    program_cheapest_ids.push(program_cheapest_id[0])
                                }
                            }
                        }
                    }
                }
            }
            if (allToRefundDetails.length == 0) {
                this._state.ui.highlightHeaderNote = !this._state.ui.highlightHeaderNote;
                return this.render();
            }

            // The order that will contain the refund orderlines.
            // Use the destinationOrder from props if the order to refund has the same
            // customer as the destinationOrder.
            const destinationOrder =
                this.props.destinationOrder && customer === this.props.destinationOrder.get_client()
                    ? this.props.destinationOrder
                    : this.env.pos.add_new_order({silent: true});

            // Add orderline for each toRefundDetail to the destinationOrder.
            for (const refundDetail of allToRefundDetails) {
                const product = this.env.pos.db.get_product_by_id(refundDetail.orderline.productId);
                const options = this._prepareRefundOrderlineOptions(refundDetail);
                await destinationOrder.add_product(product, options);
                refundDetail.destinationOrderUid = destinationOrder.uid;
            }

            // Set the customer to the destinationOrder.
            if (customer && !destinationOrder.get_client()) {
                destinationOrder.set_client(customer);
                destinationOrder.updatePricelist(customer);
            }

            // Danh sách line sản phẩm Order refund
            var refund_order_lines = []
            for (let c = 0; c < allToRefundDetails.length; c++) {
                var productId = allToRefundDetails[c].orderline.productId
                var refund_line_productId = destinationOrder.orderlines.models.filter(l => l.product.id === productId && l.product.type === 'product')
                if(refund_line_productId[0] && !refund_order_lines.includes(refund_line_productId[0])){
                    refund_order_lines.push(refund_line_productId[0])
                }
            }

            var cheapest_lines_refund_ids = []

            for (let c = 0; c < program_cheapest_ids.length; c++) {
                var line_ctkm_cheapest_ids = await this.rpc({
                    model: "pos.order.line",
                    method: 'search_read',
                    args: [[["program_id", "=", program_cheapest_ids[c].id], ['order_id', '=', order.backendId]]],
                })
                var total_value_line_ctkm_cheapest_ids = 0
                if(line_ctkm_cheapest_ids.length > 0){
                    for (let j = 0; j < line_ctkm_cheapest_ids.length; j++) {
                        total_value_line_ctkm_cheapest_ids = total_value_line_ctkm_cheapest_ids + line_ctkm_cheapest_ids[j].price_subtotal
                    }
                }

                if(refund_order_lines){
                    cheapest_lines_refund_ids = refund_order_lines
                    for (let i = 0; i < refund_order_lines.length; i++) {
                        var line_product_id = await this.rpc({
                            model: "pos.order.line",
                            method: 'search_read',
                            args: [[["id", "=", refund_order_lines[i].refunded_orderline_id]]],
                        })
                        if(line_product_id.length > 0){
                            var line_price = (Math. abs(total_value_line_ctkm_cheapest_ids) / total_price_src_order) * line_product_id[0].price_unit * refund_order_lines[i].quantity
                            let new_line = new models.Orderline({}, {
                                pos: this.env.pos,
                                order: this.env.pos.get_order(),
                                product: this.env.pos.db.get_product_by_id(program_cheapest_ids[c].discount_line_product_id[0]),
                                price: line_price,
                            })
                            new_line.quantity = -1
                            new_line.is_line_cheapest_refund = true
                            var new_line_options = {
                                is_program_reward: true,
                                program_id: this.env.pos.promo_programs[c].id,
                                refunded_orderline_id: false,
                            };
                            this.env.pos.get_order().set_orderline_options(new_line, new_line_options);
                            if (!cheapest_lines_refund_ids.includes(new_line)) {
                                cheapest_lines_refund_ids.push(new_line)
                            }
                        }
                    }
                }
            }

            // Thêm Danh sách line sản phẩm Order refund và Danh sách line giảm giá của SP rẻ nhất của Order refund
            if(line_ctkm_cheapest_ids !== undefined){
                var destinationOrder_models = destinationOrder.orderlines.models.filter(item => !line_ctkm_cheapest_ids.map(r => r.id).includes(item.refunded_orderline_id) && !cheapest_lines_refund_ids.filter(item => item.product.type === 'product').includes(item))
                if(cheapest_lines_refund_ids.length > 0){
                    destinationOrder.orderlines.models = cheapest_lines_refund_ids.concat(destinationOrder_models)
                }else{
                    destinationOrder.orderlines.models = destinationOrder_models
                }
            }

            this._onCloseScreen();
        }

        _getFilterOptions() {
            // Add SYNCED_ALL option
            const orderStates = this._getOrderStates();

            orderStates.set('SYNCED_ALL', {text: this.env._t('All Order POS')});
            orderStates.set('SYNCED', {text: this.env._t('Paid')});
            return orderStates;
        }

        //#region PUBLIC METHODS
        getSelectedSyncedOrder() {
            if (this._state.ui.filter == 'SYNCED' || this._state.ui.filter == 'SYNCED_ALL') {
                return this._state.syncedOrders.cache[this._state.ui.selectedSyncedOrderId];
            } else {
                return null;
            }
        }

        async _onSearch(event) {
            Object.assign(this._state.ui.searchDetails, event.detail);
            if (this._state.ui.filter == 'SYNCED' || this._state.ui.filter == 'SYNCED_ALL') {
                this._state.syncedOrders.currentPage = 1;
                await this._fetchSyncedOrders();
            }
            this.render();
        }

        _getSearchFields() {
            return Object.assign({}, super._getSearchFields(), {
                PHONE: {
                    displayName: this.env._t('Phone'),
                    modelField: 'partner_id.phone',
                },
            });
        }

    };

    Registries.Component.extend(TicketScreen, TicketScreenInherit);
    return TicketScreenInherit;
});
