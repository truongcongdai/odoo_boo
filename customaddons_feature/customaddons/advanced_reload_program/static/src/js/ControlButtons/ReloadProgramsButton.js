odoo.define('advanced_reload_program.ReloadProgramsButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');

    class ReloadProgramsButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }

        async onClick() {
            let self_update = this
            try {
                if (this.env.pos.config.s_promo_domain !== false) {
                    const promo_domain = JSON.parse(this.env.pos.config.s_promo_domain.replaceAll("'", '"'))['domain']
                    const programs = await rpc.query({
                        model: 'coupon.program',
                        method: "search_read",
                        domain: promo_domain,
                    })
                    if (programs.length) {
                        for (var i = 0, len = programs.length; i < len; i++) {
                            if (self_update.env.pos.coupon_programs_by_id.hasOwnProperty(programs[i].id) === false) {
                                programs[i].valid_product_ids = new Set(programs[i].valid_product_ids);
                                programs[i].valid_partner_ids = new Set(programs[i].valid_partner_ids);
                                programs[i].discount_specific_product_ids = new Set(programs[i].discount_specific_product_ids);
                                self_update.env.pos.programs.push(programs[i])
                                self_update.env.pos.promo_programs.push(programs[i])
                                self_update.env.pos.coupon_programs_by_id[programs[i].id] = programs[i]
                                self_update.env.pos.config.promo_program_ids.push(programs[i].id)
                                self_update.env.pos.config.program_ids.push(programs[i].id)
                            }
                        }
                    }
                    this.showPopup('ConfirmPopup',{
                        title: this.env._t('Thành công'),
                        body: this.env._t("Tải thành công chương trình phiếu khuyến mãi."),
                    });
                }
            } catch (error) {
                console.log(error);
                // window.confirm("Not Ok");
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi'),
                    body: this.env._t("Chưa tích chọn chương trình khuyến mãi. Vui lòng chọn điểm bán hàng liên quan và nhấn nút Đặt chương trình khuyến mãi."),
                });
            }
        }
    }
    ReloadProgramsButton.template = 'ReloadProgramsButton';
    // ProductScreen.addControlButton({
    //     component: ReloadProgramsButton,
    //     condition: function () {
    //         return this.env.pos.config.use_coupon_programs;
    //     },
    // });
    Registries.Component.add(ReloadProgramsButton);
    return ReloadProgramsButton;
});
