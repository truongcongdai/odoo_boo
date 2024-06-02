odoo.define('advanced_loyalty_program.s_loyalty', function (require) {
    'use strict';


    // const RewardButton = require('pos_loyalty.RewardButton');
    // const Registries = require('point_of_sale.Registries');
    var utils = require('web.utils');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var {Gui} = require('point_of_sale.Gui');
    var rpc = require('web.rpc');
    var round_pr = utils.round_precision;

    var _t = core._t;
    // models.load_models([{
    //     model: 's.rule.point',
    //     condition: function(self){ return true; },
    //     fields: ['s_customer_ranked_id', 's_proportion_point'],
    //     domain: function(self){ return [['s_customer_ranked_id','!=',false]]; },
    //     loaded: function(self,result){
    //         if(result.length){
    //             self.set('variable',result[0].s_customer_ranked_id);
    //         }
    //     }
    //   }],{'after': 'product.product'});
    models.load_fields("loyalty.reward", ["s_reward_exchange_point", "s_exchange_maximum", "s_type_exchange", "s_exchange_product", "s_reward_exchange_monetary"]);
    models.load_fields("product.product", ["s_loyalty_product_reward"])
    models.load_fields("res.partner", ["related_customer_ranked"])
    models.load_fields("loyalty.rule", ["s_rule_type", "s_rule_point_id", "s_rule_date_to", "s_rule_date_from", "s_multiplication_point", "s_rule_apply_for"])
    models.load_fields("loyalty.program", ["s_point_exchange", "s_monetary_exchange", "is_refund_loyalty_points", "zns_template_id"]);
    models.load_fields("pos.order.line", ["loyalty_points", "s_order_reward_loyalty"]);
    models.load_fields("sale.order.line", ["s_loyalty_point_lines"]);
    // const SRewardButton = (RewardButton) => class extends RewardButton {
    //     constructor() {
    //         super(...arguments);
    //     }


    var _super = models.Order.prototype;
    models.Order = models.Order.extend({
        apply_reward: async function (reward) {
            var crounding;
            var product, product_price, order_total, spendable;
            var spendable_points = this.pos.get_order().get_spendable_points()
            var exchange_maximum = 0
            var s_total
            // Remove Gift Card
            for (let i = 0; i < this.orderlines.models.length; i++) {
                if (this.orderlines.models[i].gift_card_id) {
                    this.remove_orderline(this.orderlines.models[i]);
                }
            }
            // Remove Gift Card
            if (reward.reward_type === 'point') {
                if (this.pos.db.get_product_by_id(reward.s_exchange_product[0]) === undefined) {
                    let product_model = _.find(this.pos.models, (model) => model.model === 'product.product');
                    const products = await this.pos.rpc({
                        model: 'product.product',
                        method: 'search_read',
                        kwargs: {
                            'domain': [['id', '=', reward.s_exchange_product[0]]],
                            'fields': product_model.fields,
                        },
                    });
                    product_model.loaded(this.pos, products);
                }
                var product_reward = this.pos.db.get_product_by_id(reward.s_exchange_product[0]);
                if (!product_reward) {
                    return;
                }
                if (spendable_points > 0 && spendable_points >= reward.s_reward_exchange_point) {
                    if (this.orderlines !== undefined) {
                        // if (this.orderlines.filter(l => l.product.id === reward.s_exchange_product[0]).length === 0){
                        //
                        // }
                        var line_reward_id = this.orderlines.models.filter(l => l.reward_id === reward.id)
                        if (line_reward_id.length) {
                            //Trường hợp add lần thứ 2 reward đổi điểm
                            s_total = this.get_total_point_without_tax(product_reward)
                            if (reward.s_type_exchange === 'number') {
                                exchange_maximum = reward.s_exchange_maximum
                            } else {
                                exchange_maximum = (((s_total * reward.s_exchange_maximum) / 100) / reward.s_reward_exchange_monetary) * reward.s_reward_exchange_point
                            }
                            if (((line_reward_id[0].quantity + 1) * reward.s_reward_exchange_point) >= exchange_maximum) {
                                return Gui.showPopup('ErrorPopup', {
                                    title: _t('Thông báo'),
                                    body: _t('Không thể đổi quá số điểm quy đổi tối đa'),
                                });
                            }
                        }
                        product_reward.lst_price = -reward.s_reward_exchange_monetary
                        this.add_product(product_reward, {
                            price: -reward.s_reward_exchange_monetary,
                            quantity: 1,
                            merge: true,
                            extras: {reward_id: reward.id, s_is_loyalty_reward_line: true},
                        });
                    }
                } else {
                    return Gui.showPopup('ErrorPopup', {
                        title: _t('Thông báo'),
                        body: _t('Khách hàng không đủ điều kiện áp dụng phần thưởng'),
                    });
                }
            } else if (reward.reward_type === 'discount') {
                this.trigger('update-rewards')
                crounding = this.pos.currency.rounding;
                var discount = 0;
                product = this.pos.db.get_product_by_id(reward.discount_product_id[0]);
                if (!product) {
                    return;
                }
                if (reward.discount_type === "percentage") {
                    if (reward.discount_apply_on === "cheapest_product") {
                        var price;
                        for (var line of this.get_orderlines()) {
                            if ((!price || price > line.get_unit_price()) && line.product.id !== product.id && line.product.type !== "service") {
                                discount = round_pr(line.get_price_with_tax() * (reward.discount_percentage / 100), crounding);
                                price = line.get_unit_price();
                            }
                        }
                        if (reward.discount_max_amount !== 0 && discount > reward.discount_max_amount)
                            discount = reward.discount_max_amount;
                        this.add_product(product, {
                            price: -discount,
                            quantity: 1,
                            merge: false,
                            extras: {reward_id: reward.id, s_is_loyalty_reward_line: true},
                        });
                    } else {
                        await _super.apply_reward.apply(this, arguments)
                    }
                } else {
                    await _super.apply_reward.apply(this, arguments)
                }
            } else if (reward.reward_type === 'gift') {
                var gift_product = this.pos.db.get_product_by_id(reward.gift_product_id[0])
                if (!gift_product) {
                    return;
                }
                if (gift_product.type === "product") {
                    var qty_available = await this.pos.rpc({
                        model: 'product.product',
                        method: 'get_product_quantities',
                        args: [reward.gift_product_id[0], this.pos.picking_type.id],
                        kwargs: {context: this.pos.session.user_context},
                    });
                    if (typeof (qty_available) !== undefined) {
                        if (qty_available < 1) {
                            Gui.showPopup('ErrorPopup', {
                                title: _t("Lỗi người dùng"),
                                body: _t("Sản phẩm trong kho không đủ."),
                            });
                            return;
                        }
                    }
                }
                await _super.apply_reward.apply(this, arguments)
            }
        },

        get_available_rewards: function () {
            if (!this.pos.loyalty || !this.get_client()) {
                return [];
            }
            for (var e = 0; e < this.pos.loyalty.rewards.length; e++) {
                var reward = this.pos.loyalty.rewards[e];
                if (reward.reward_type === 'point') {
                    reward.minimum_points = 0
                }
            }
            var spendable_points = this.pos.get_order().get_spendable_points()

            var res = _super.get_available_rewards.apply(this, arguments)
            // var client = this.get_client();
            // if (!client) {
            //     return [];
            // }
            if (res.length > 0) {
                var reward_type_point = res.filter(l => l.reward_type === "point")
                if (reward_type_point) {
                    res = res.filter(l => l.reward_type !== "point")
                    for (let i = 0; i < reward_type_point.length; i++) {
                        if (spendable_points >= reward_type_point[i].s_reward_exchange_point) {
                            if (this.get_spendable_points() >= reward_type_point[i].s_reward_exchange_point)
                                res.push(reward_type_point[i])
                        }
                    }
                }
            }
            return res

        },

        get_spent_points: function () {
            var points = 0;
            if (!this.pos.loyalty || !this.get_client()) {
                return 0;
            } else {
                var reward_point = 0
                var lines = this.get_orderlines()
                if (lines) {
                    for (var line of lines) {
                        var reward = line.get_reward();
                        if (reward) {
                            if (reward.reward_type === "point") {
                                if ((this.get_client().loyalty_points - (points + round_pr(line.get_quantity(), 1))) >= 0) {
                                    this.set_price_exchange_product(reward)
                                    // reward_point += round_pr(line.get_quantity(), 1);
                                    points += round_pr(line.get_quantity() * reward.s_reward_exchange_point, 1);
                                    line.loyalty_points = round_pr(line.get_quantity() * reward.s_reward_exchange_point, 1);

                                } else {
                                    this.orderlines.remove(line)
                                }
                            } else {
                                points += round_pr(line.get_quantity() * reward.point_cost, 1);
                                line.loyalty_points = round_pr(line.get_quantity() * reward.point_cost, 1);
                            }
                        }
                    }
                }
            }
            return points
        },

        set_price_exchange_product: async function (reward) {
            var products = this.pos.db.get_product_by_id(reward.s_exchange_product[0]);
            if (products) {
                products.lst_price = -(reward.s_reward_exchange_monetary / reward.s_reward_exchange_point)
            }
        },

        get_total_point_without_tax: function (product_reward) {
            if (!this.pos.loyalty || !this.get_client()) {
                return 0;
            }
            var sum = 0
            for (var line of this.get_orderlines()) {
                if (!line.get_reward()) {  // Reward products are ignored
                    sum += round_pr(line.get_price_without_tax(), this.pos.currency.rounding)
                } else {
                    if (line.get_reward().reward_type !== 'point' || line.get_reward().s_exchange_product[0] !== product_reward.id) {
                        sum += round_pr(line.get_price_without_tax(), this.pos.currency.rounding)
                    }
                }
            }
            return sum
        },

        get_won_points: function () {
            _super.get_won_points.apply(this, arguments)
            if (!this.pos.loyalty || !this.get_client()) {
                return 0;
            }
            var total_points = 0;
            var s_rule_ranked_point = 0
            var is_only_return_order = false;
            var is_return_order = false
            var total_refunded_points = 0;
            var sol_refund_all = true
            var total_reward_refund_points = 0
            var list_point = this.cal_rule_points_apply_discount(this, this.pos.loyalty.rules);
            for (var line of this.get_orderlines()) {
                if (line.refunded_orderline_id && this.pos.loyalty.is_refund_loyalty_points) {
                    is_only_return_order = true;
                    if (typeof line.loyalty_points !== 'undefined') {
                        total_refunded_points += line.loyalty_points;
                    }
                } else if (line.sale_order_line_id && this.pos.loyalty.is_refund_loyalty_points) {
                    is_only_return_order = true;
                    ///Nếu là đơn trả hàng và trả hết số lượng thì refund tất cả số điểm
                    if (line.product.type === 'product') {
                        if (line.sale_order_line_id.qty_delivered !== Math.abs(line.quantity)) {
                            sol_refund_all = false
                        }
                    }
                    if (line.sale_order_line_id.is_loyalty_reward_line) {
                        total_reward_refund_points -= (line.sale_order_line_id.s_redeem_amount / line.sale_order_line_id.product_uom_qty) * line.quantity
                    } else {
                        if (line.sale_order_line_id.qty_delivered !== 0) {
                            total_refunded_points += (line.sale_order_line_id.sol_loyalty_point / line.sale_order_line_id.qty_delivered) * line.quantity;
                        }
                    }
                } else {
                    if (is_only_return_order) {
                        is_only_return_order = false;
                        is_return_order = true;
                    }
                    if (line.get_reward() || line.get_product().type === 'service') {  // Reward products are ignored
                        continue;
                    }
                    var line_points = 0;
                    var won_point_exchange = 0
                    var totalWithTax = this.get_orderlines().filter(l => !l.refunded_orderline_id && !l.sale_order_line_id).reduce(
                        (total, orderLine) => total + (orderLine.price * orderLine.quantity), 0)
                    var totalWithoutDiscount = this.get_orderlines().filter(
                        l => !l.refunded_orderline_id && !l.sale_order_line_id && !l.program_id && !l.coupon_id && !l.gift_card_id && !l.reward_id
                    ).reduce((total, orderLine) => total + (orderLine.price * orderLine.quantity), 0)
                    // var customer_rank = this.get_client().customer_ranked
                    var customer_rank_id = this.get_client().related_customer_ranked[0]
                    if (this.pos.loyalty.s_point_exchange > 0) {
                        won_point_exchange = ((totalWithTax / this.pos.loyalty.s_monetary_exchange) * this.pos.loyalty.s_point_exchange) * (line.get_price_with_tax() / totalWithoutDiscount)
                    }
                    line_points = won_point_exchange
                    line.loyalty_points = (won_point_exchange + Math.max(...list_point)) * line.get_price_without_tax() / totalWithoutDiscount;
                    total_points += line_points;
                }

            }
            total_points += Math.max(...list_point);
            // Đơn return
            total_refunded_points = Math.floor(total_refunded_points)
            if (is_only_return_order) {
                if (sol_refund_all) {
                    return round_pr(total_refunded_points + total_reward_refund_points, 1);
                }
                return round_pr(total_refunded_points, 1);
            }
            // Đơn return có mua thêm sản phẩm
            if (is_return_order) {
                // if(Math.abs(s_rule_ranked_point) > Math.abs(total_points)){
                //     total_points = 0;
                // } else {
                //     s_rule_ranked_point = 0;
                // }
                if (this.get_total_without_tax() === 0 || this.get_total_without_tax() < 0) {
                    if (sol_refund_all) {
                        return round_pr(total_points + total_reward_refund_points, 1);
                    }
                    return round_pr(0, 1);
                }
            }
            // Không phải đơn return
            // if(Math.abs(s_rule_ranked_point) > Math.abs(total_points)){
            //     total_points = 0;
            // } else {
            //     s_rule_ranked_point = 0;
            // }
            // total_points += ((this.get_total_with_tax() / this.pos.loyalty.s_monetary_exchange) * this.pos.loyalty.s_point_exchange) + s_rule_ranked_point;
            return round_pr(total_points, 1);
        },
        get_total_quantity: function () {
            var total = 0;
            for (var i = 0; i < this.orderlines.models.length; i++) {
                if (this.orderlines.models[i].product.type !== 'service') {
                    total += this.orderlines.models[i].quantity;
                }
            }
            return total;
        },
        cal_rule_points_apply_discount: function (order, rules) {
            var s_rule_ranked_point = 0
            var list_point = []
            var totalWithTax = this.get_orderlines().filter(l => !l.refunded_orderline_id && !l.sale_order_line_id).reduce(
                (total, orderLine) => total + (orderLine.price * orderLine.quantity), 0)
            var totalWithoutDiscount = this.get_orderlines().filter(
                l => !l.refunded_orderline_id && !l.sale_order_line_id && !l.program_id && !l.coupon_id && !l.gift_card_id && !l.reward_id
            ).reduce((total, orderLine) => total + (orderLine.price * orderLine.quantity), 0)
            // var customer_rank = this.get_client().customer_ranked
            var customer_rank_id = this.get_client().related_customer_ranked[0]
            rules.forEach(function (rule) {
                var rule_points = 0
                if (rule.s_rule_type === 'special') {
                    let date = new Date();
                    let currentDate = Date.parse(date.getFullYear() + '-' + ('0' + (date.getMonth() + 1)).slice(-2) + '-' + ('0' + date.getDate()).slice(-2));
                    ///TH1.1: Không có ngày áp dụng và không có hạng áp dụng
                    if (!rule.s_rule_date_from && !rule.s_rule_date_to) {
                        if (!rule.s_rule_apply_for.length) {
                            rule_points += rule.points_quantity * order.get_total_quantity();
                            rule_points += rule.points_currency * order.get_total_with_tax();
                            if (rule.s_multiplication_point > 0) {
                                rule_points = rule_points * rule.s_multiplication_point
                            }
                        } else {
                            if (rule.s_rule_apply_for.includes(customer_rank_id)) {
                                rule_points += rule.points_quantity * order.get_total_quantity();
                                rule_points += rule.points_currency * order.get_total_with_tax();
                                if (rule.s_multiplication_point > 0) {
                                    rule_points = rule_points * rule.s_multiplication_point
                                }
                            }

                        }
                    }
                    //TH2.1: Có ngày bắt đầu và không có ngày kết thúc
                    else if (rule.s_rule_date_from && !rule.s_rule_date_to) {
                        if (Date.parse(rule.s_rule_date_from) <= currentDate) {
                            ///Nếu có hạng áp dụng
                            if (rule.s_rule_apply_for.length) {
                                if (rule.s_rule_apply_for.includes(customer_rank_id)) {
                                    rule_points += rule.points_quantity * order.get_total_quantity();
                                    rule_points += rule.points_currency * order.get_total_with_tax();
                                    if (rule.s_multiplication_point > 0) {
                                        rule_points = rule_points * rule.s_multiplication_point
                                    }
                                }
                            } else {
                                rule_points += rule.points_quantity * order.get_total_quantity();
                                rule_points += rule.points_currency * order.get_total_with_tax();
                                if (rule.s_multiplication_point > 0) {
                                    rule_points = rule_points * rule.s_multiplication_point
                                }
                            }
                        }
                    }
                    //TH2.2: Có ngày kết thúc và không có ngày bắt đầu
                    else if (!rule.s_rule_date_from && rule.s_rule_date_to) {
                        if (Date.parse(rule.s_rule_date_to) >= currentDate) {
                            ///Nếu có hạng áp dụng
                            if (rule.s_rule_apply_for.length) {
                                if (rule.s_rule_apply_for.includes(customer_rank_id)) {
                                    rule_points += rule.points_quantity * order.get_total_quantity();
                                    rule_points += rule.points_currency * order.get_total_with_tax();
                                    if (rule.s_multiplication_point > 0) {
                                        rule_points = rule_points * rule.s_multiplication_point
                                    }
                                }
                            } else {
                                rule_points += rule.points_quantity * order.get_total_quantity();
                                rule_points += rule.points_currency * order.get_total_with_tax();
                                if (rule.s_multiplication_point > 0) {
                                    rule_points = rule_points * rule.s_multiplication_point
                                }
                            }
                        }
                    }
                    //TH3: Có ngày áp dụng (ngày bắt đầu và ngày kết thúc)
                    else if (rule.s_rule_date_from && rule.s_rule_date_to) {
                        if (Date.parse(rule.s_rule_date_from) <= currentDate && currentDate <= Date.parse(rule.s_rule_date_to)) {
                            if (rule.s_rule_apply_for.length) {
                                if (rule.s_rule_apply_for.includes(customer_rank_id)) {
                                    rule_points += rule.points_quantity * order.get_total_quantity();
                                    rule_points += rule.points_currency * order.get_total_with_tax();
                                    if (rule.s_multiplication_point > 0) {
                                        rule_points = rule_points * rule.s_multiplication_point
                                    }
                                }
                            } else {
                                rule_points += rule.points_quantity * order.get_total_quantity();
                                rule_points += rule.points_currency * order.get_total_with_tax();
                                if (rule.s_multiplication_point > 0) {
                                    rule_points = rule_points * rule.s_multiplication_point
                                }
                            }
                        }
                    }

                }
                var won_line_ranked_point = 0;
                if (rule.s_rule_type === 'rule_point') {
                    if (rule.rank_point !== undefined && rule.rank_point.length) {
                        for (let i = 0; rule.rank_point.length > i; i++) {
                            if (rule.rank_point[i].s_customer_ranked_id[0] === customer_rank_id) {
                                if (rule.rank_point[i].s_proportion_point > 0) {
                                    s_rule_ranked_point = (totalWithTax * rule.rank_point[i].s_proportion_point) / 100
                                    won_line_ranked_point = (order.get_total_with_tax() * rule.rank_point[i].s_proportion_point) / 100
                                    list_point.push(won_line_ranked_point)
                                }
                            }
                        }
                    }
                }
                list_point.push(rule_points)
                // if(Math.abs(rule_points) > Math.abs(line_points)) {
                //     line_points = rule_points;
                //     // line.loyalty_points = line_points;
                // }
                // if (loyalty_line > line_points) {
                //     line.loyalty_points = loyalty_line;
                // }
            });
            return list_point
        },
        cal_rule_points_not_apply_discount: function (rules, line) {
            var s_rule_ranked_point = 0
            rules.forEach(function (rule) {
                var rule_points = 0
                if (rule.valid_product_ids.find(function (product_id) {
                    return product_id === line.get_product().id
                })) {
                    if (rule.s_rule_type === 'special') {
                        let date = new Date();
                        let currentDate = Date.parse(date.getFullYear() + '-' + ('0' + (date.getMonth() + 1)).slice(-2) + '-' + ('0' + date.getDate()).slice(-2));
                        ///TH1.1: Không có ngày áp dụng và không có hạng áp dụng
                        if (!rule.s_rule_date_from && !rule.s_rule_date_to) {
                            if (!rule.s_rule_apply_for.length) {
                                rule_points += rule.points_quantity * line.get_quantity();
                                rule_points += rule.points_currency * line.get_price_with_tax();
                                if (rule.s_multiplication_point > 0) {
                                    rule_points = rule_points * rule.s_multiplication_point
                                }
                            } else {
                                if (rule.s_rule_apply_for.includes(customer_rank_id)) {
                                    rule_points += rule.points_quantity * line.get_quantity();
                                    rule_points += rule.points_currency * line.get_price_with_tax();
                                    if (rule.s_multiplication_point > 0) {
                                        rule_points = rule_points * rule.s_multiplication_point
                                    }
                                }

                            }
                        }
                        //TH2.1: Có ngày bắt đầu và không có ngày kết thúc
                        else if (rule.s_rule_date_from && !rule.s_rule_date_to) {
                            if (Date.parse(rule.s_rule_date_from) <= currentDate) {
                                ///Nếu có hạng áp dụng
                                if (rule.s_rule_apply_for.length) {
                                    if (rule.s_rule_apply_for.includes(customer_rank_id)) {
                                        rule_points += rule.points_quantity * line.get_quantity();
                                        rule_points += rule.points_currency * line.get_price_with_tax();
                                        if (rule.s_multiplication_point > 0) {
                                            rule_points = rule_points * rule.s_multiplication_point
                                        }
                                    }
                                } else {
                                    rule_points += rule.points_quantity * line.get_quantity();
                                    rule_points += rule.points_currency * line.get_price_with_tax();
                                    if (rule.s_multiplication_point > 0) {
                                        rule_points = rule_points * rule.s_multiplication_point
                                    }
                                }
                            }
                        }
                        //TH2.2: Có ngày kết thúc và không có ngày bắt đầu
                        else if (!rule.s_rule_date_from && rule.s_rule_date_to) {
                            if (Date.parse(rule.s_rule_date_to) >= currentDate) {
                                ///Nếu có hạng áp dụng
                                if (rule.s_rule_apply_for.length) {
                                    if (rule.s_rule_apply_for.includes(customer_rank_id)) {
                                        rule_points += rule.points_quantity * line.get_quantity();
                                        rule_points += rule.points_currency * line.get_price_with_tax();
                                        if (rule.s_multiplication_point > 0) {
                                            rule_points = rule_points * rule.s_multiplication_point
                                        }
                                    }
                                } else {
                                    rule_points += rule.points_quantity * line.get_quantity();
                                    rule_points += rule.points_currency * line.get_price_with_tax();
                                    if (rule.s_multiplication_point > 0) {
                                        rule_points = rule_points * rule.s_multiplication_point
                                    }
                                }
                            }
                        }
                        //TH3: Có ngày áp dụng (ngày bắt đầu và ngày kết thúc)
                        else if (rule.s_rule_date_from && rule.s_rule_date_to) {
                            if (Date.parse(rule.s_rule_date_from) <= currentDate && currentDate <= Date.parse(rule.s_rule_date_to)) {
                                if (rule.s_rule_apply_for.length) {
                                    if (rule.s_rule_apply_for.includes(customer_rank_id)) {
                                        rule_points += rule.points_quantity * line.get_quantity();
                                        rule_points += rule.points_currency * line.get_price_with_tax();
                                        if (rule.s_multiplication_point > 0) {
                                            rule_points = rule_points * rule.s_multiplication_point
                                        }
                                    }
                                } else {
                                    rule_points += rule.points_quantity * line.get_quantity();
                                    rule_points += rule.points_currency * line.get_price_with_tax();
                                    if (rule.s_multiplication_point > 0) {
                                        rule_points = rule_points * rule.s_multiplication_point
                                    }
                                }
                            }
                        }

                    }
                    var won_line_ranked_point = 0;
                    if (rule.s_rule_type === 'rule_point') {
                        if (rule.rank_point !== undefined && rule.rank_point.length) {
                            for (let i = 0; rule.rank_point.length > i; i++) {
                                if (rule.rank_point[i].s_customer_ranked_id[0] === customer_rank_id) {
                                    if (rule.rank_point[i].s_proportion_point > 0) {
                                        s_rule_ranked_point = (totalWithTax * rule.rank_point[i].s_proportion_point) / 100
                                        won_line_ranked_point = (line.get_price_with_tax() * rule.rank_point[i].s_proportion_point) / 100
                                        list_point.push(won_line_ranked_point)
                                    }
                                }
                            }
                        }
                    }
                    list_point.push(rule_points)
                }
                // if(Math.abs(rule_points) > Math.abs(line_points)) {
                //     line_points = rule_points;
                //     // line.loyalty_points = line_points;
                // }
                // if (loyalty_line > line_points) {
                //     line.loyalty_points = loyalty_line;
                // }
            });
        },
        get_total_amount_used_reward: function () {
            var total_with_tax = round_pr(this.orderlines.reduce((function (sum, orderLine) {
                var orderline_price = 0
                if (orderLine.get_reward() === undefined && !orderLine.product.s_loyalty_product_reward) {
                    orderline_price = orderLine.get_price_without_tax();
                }
                return sum + orderline_price;
            }), 0), this.pos.currency.rounding);
            return (total_with_tax + this.get_total_tax())
        },

        get_rule_point_ids: async function () {
            if (this.pos.loyalty !== undefined) {
                if (this.pos.loyalty.rules !== undefined) {
                    var rules_id = this.pos.loyalty.rules.filter(l => l.s_rule_type === "rule_point" && l.s_rule_point_id)[0]
                    if (rules_id !== undefined) {
                        const rules_point = await this.pos.rpc({
                            model: 's.rule.point',
                            method: 'search_read',
                            kwargs: {
                                'domain': [['s_loyalty_rule_id', '=', rules_id.id]],
                            },
                        });
                        if (rules_point) {
                            this.pos.loyalty.rules.filter(l => l.s_rule_type === "rule_point" && l.s_rule_point_id)[0].rank_point = rules_point
                        }
                    }
                }
            }
        },

        get_new_total_period_revenue: function () {
            if (!this.pos.loyalty || !this.get_client()) {
                return 0;
            } else {
                if (this.state != 'paid') {
                    return round_pr(this.get_client().total_period_revenue + this.get_total_paid(), 1);
                } else {
                    return round_pr(this.get_client().total_period_revenue, 1);
                }
            }
        },
        // _getOnOrderOrderlines: function () {
        //     return _super._getOnOrderOrderlines.apply(this, arguments).filter(line => !line.product.s_loyalty_product_reward)
        // },

        finalize: function () {
            var client = this.get_client();
            if (client) {
                client.total_period_revenue = this.get_new_total_period_revenue();
            }
            _super.finalize.apply(this, arguments);
        },

        export_for_printing: function () {
            var json = _super.export_for_printing.apply(this, arguments);
            if (this.pos.loyalty && this.get_client()) {
                json.loyalty['period_revenue_total'] = json.total_period_revenue + json.total_paid
            }
            return json;
        },

        export_as_JSON: function () {
            this.get_rule_point_ids()
            return _super.export_as_JSON.apply(this, arguments);
        },
    });

    var _super_orderline = models.Orderline.prototype
    models.Orderline = models.Orderline.extend({
        // set_quantity: function (quantity, keep_price) {
        //     if (this.pos.get_order()) {
        //         if (this.pos.get_order().orderlines.length > 0 && quantity !== 'remove'){
        //             var select_order_line = this.pos.get_order().get_selected_orderline()
        //             if (this.pos.loyalty !== undefined && select_order_line !== undefined && select_order_line.get_reward() !== undefined && select_order_line.get_reward().reward_type === 'point'){
        //                 var loyaltyPoints = this.get_loyalty_point()
        //                 if (loyaltyPoints > 0) {
        //                     if (select_order_line.product.s_loyalty_product_reward &&
        //                         select_order_line.get_reward().s_exchange_product[0] === select_order_line.product.id && select_order_line.product.type === 'service') {
        //                         var unit_price = -(select_order_line.get_reward().s_reward_exchange_monetary / select_order_line.get_reward().s_reward_exchange_point)
        //                         //TH1: Quy đổi tối đa <= điểm thân thiết
        //
        //                         if (loyaltyPoints >= quantity && quantity <= select_order_line.get_reward().s_exchange_maximum) {
        //                             select_order_line.set_unit_price(unit_price);
        //                             select_order_line.order.fix_tax_included_price(select_order_line);
        //                         } else {
        //                             if (loyaltyPoints <= quantity){
        //                                 select_order_line.set_unit_price(unit_price)
        //                                 select_order_line.set_quantity(loyaltyPoints)
        //                             } else {
        //                                 select_order_line.set_unit_price(unit_price)
        //                                 select_order_line.set_quantity(select_order_line.get_reward().s_exchange_maximum)
        //                             }
        //                             return Gui.showPopup('ErrorPopup', {
        //                                 title: _t('Thông báo'),
        //                                 body: _t('Không thể đổi quá điểm'),
        //                             });
        //                         }
        //                         //TH2: Quy đổi tối đa >= điểm thân thiết
        //
        //                     }
        //                 } else {
        //                     select_order_line.set_unit_price(0)
        //                     select_order_line.set_quantity(0)
        //                     return Gui.showPopup('ErrorPopup', {
        //                         title: _t('Thông báo'),
        //                         body: _t('Khách hàng không đủ điều kiện áp dụng phần thưởng'),
        //                     });
        //                 }
        //             }
        //             else if (this.pos.loyalty !== undefined && select_order_line !== undefined && select_order_line.get_reward() !== undefined && select_order_line.get_reward().reward_type.includes('gift', 'discount')){
        //                 return _super_orderline.set_quantity.apply(this, [1, true]);
        //             }
        //         }
        //     }
        //     this.trigger('change', this);
        //     return _super_orderline.set_quantity.apply(this, [quantity, keep_price]);
        // },

        // set_quantity: function (quantity, keep_price) {
        //     if (this.pos.get_order()) {
        //         if (this.pos.get_order().orderlines.length){
        //             var select_order_line = this.pos.get_order().get_selected_orderline()
        //             if (this.pos.loyalty !== undefined && select_order_line.get_reward() === undefined) {
        //                 this.pos.get_order().remove_orderline(this.getLoyaltyRewardLine())
        //             }
        //         }
        //     }
        //     return _super_orderline.set_quantity.apply(this, [quantity, keep_price]);
        // },

        getLoyaltyRewardLine: function () {
            const orderlines = this.pos.get_order().get_orderlines()
            return orderlines.filter((line) => line.reward_id);
        },

        set_unit_price: function (price) {
            ///Không cho line reward set lại giá
            if (typeof (this.pos.loyalty) !== "undefined") {
                if (typeof (this.get_reward()) !== 'undefined') {
                    price = this.price
                }
            }

            if (this.s_is_loyalty_reward_line) {
                price = this.price
            }
            _super_orderline.set_unit_price.apply(this, [price])
        },
        export_as_JSON: function () {
            const json = _super_orderline.export_as_JSON.apply(this, arguments);
            json.loyalty_points = this.loyalty_points ? this.loyalty_points : 0;
            json.s_is_loyalty_reward_line = this.s_is_loyalty_reward_line;
            json.refunded_orderline_id = this.refunded_orderline_id;
            return json;
        },
        init_from_JSON: function (json) {
            _super_orderline.init_from_JSON.apply(this, arguments);
            this.loyalty_points = json.loyalty_points || 0;
            this.s_is_loyalty_reward_line = json.s_is_loyalty_reward_line
            this.refunded_orderline_id = json.refunded_orderline_id
        },
    });
    //
    // Registries.Component.extend(RewardButton, SRewardButton);
    // return SRewardButton;
});
