odoo.define('advanced_pos.CustomerPos', function (require) {
    "use strict";
    var models = require('point_of_sale.models');
    var ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');
    const Registries = require("point_of_sale.Registries");
//    override replace fields in pos model
//     models.load_fields('res.partner', ['district', 'birthday', 'format_birthday', 'gender','s_pos_order_id', 'pos_create_customer', 'is_new_customer', 'last_order', 'customer_ranked','customer_rank']);
    models.load_fields('res.partner', ['district', 'birthday', 'gender', 'partner_note', 's_pos_order_id', 'pos_create_customer', 'is_new_customer', 'last_order', 'customer_ranked', 'customer_rank', 'type', 'is_connected_vani', 'vani_connect_from']);
    models.load_fields('pos.order', ['sale_person_id']);
    models.load_fields('product.product', ['ma_san_pham', 'mau_sac', 'kich_thuoc', 's_free_product_id', 'is_gift_free_product']);
    models.load_fields('coupon.program', ['free_discount_cheapest_products', 's_rule_maximum_amount_tax_inclusion', 's_rule_maximum_amount', 's_apply_rule_maximum', 's_is_program_discard']);
    models.load_fields('pos.payment.method', ['payment_method_giftcard']);
    //override change info customer
    const SCustomerPos = (ClientDetailsEdit) => class extends ClientDetailsEdit {
        constructor() {
            super(...arguments);
            // const partner = this.props.partner;
            // this.changes = {
            //     'country_id': partner.country_id && partner.country_id[0],
            //     'state_id': null,
            // };
        }


        is_phonenumber(phonenumber) {
            var phoneno = /^\+?([0-9]{2})\)?[-. ]?([0-9]{4})[-. ]?([0-9]{4})$/;
            if (phonenumber.match(phoneno)) {
                return true;
            } else {
                return false;
            }
        }

        // onChangeDate(event) {
        //     this.changes[event.target.name] = event.target.value;
        //     var format_date = new Date(event.target.value)
        //     var set_date = ('0' + format_date.getDate()).slice(-2).toString()
        //                     + '/' + ('0' + (format_date.getMonth() + 1)).slice(-2).toString()
        //                     + '/' + format_date.getFullYear().toString()
        //     event.target.setAttribute("data-date", set_date)
        //     $('.format_birthday').val(set_date);
        // }

        _formatDateBirthDay(value) {
            if (value.target.dataset.date === 'day') {
                this.s_day = value.target.value
            } else if (value.target.dataset.date === 'month') {
                this.s_month = value.target.value
            } else {
                this.s_year = value.target.value
            }
            if (this.s_day && this.s_month && this.s_year) {
                if (this.s_day.length === 2 && this.s_month.length === 2 && this.s_year.length === 4) {
                    if ((parseInt(this.s_day) > 31)) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Lỗi người dùng'),
                            body: this.env._t("Nhập sai định dạng ngày sinh."),
                        })
                    } else if (parseInt(this.s_month) > 12) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Lỗi người dùng'),
                            body: this.env._t("Nhập sai định dạng tháng sinh."),
                        })
                    } else {
                        this.changes.birthday = this.s_day.toString() + '/' + this.s_month.toString() + '/' + this.s_year.toString()
                    }
                }
            }
        }

        ///Hóa đơn gần nhất

        _buttonMoreRecentlyBill() {
            var show_element = document.getElementById("show-info-recently-bill");
            show_element.classList.remove("block-client-bills-hide")
            show_element.classList.add("block-client-bills-show")
            var more_element = document.getElementById("more-recently-bill");
            more_element.classList.add("block-more-button")
        }

        _buttonShowinfoDownRecentlyBill() {
            var show_element = document.getElementById("show-info-recently-bill");
            show_element.classList.remove("block-client-none")
            var show_button_show_up = document.getElementById("show-info-up-recently-bill");
            show_button_show_up.classList.remove("button-show-info-up")
            var hide_button_show_down = document.getElementById("show-info-down-recently-bill");
            hide_button_show_down.classList.add("info-caret-none")
        }

        _buttonShowinfoUpRecentlyBill() {
            var hide_element = document.getElementById("show-info-recently-bill");
            hide_element.classList.add("block-client-none")
            hide_element.classList.add("block-client-bills-hide")
            hide_element.classList.remove("block-client-bills-show")
            var show_button_show_down = document.getElementById("show-info-down-recently-bill");
            show_button_show_down.classList.remove("info-caret-none")
            var hide_button_show_up = document.getElementById("show-info-up-recently-bill");
            hide_button_show_up.classList.add("button-show-info-up")
            var more_element = document.getElementById("more-recently-bill");
            more_element.classList.remove("block-more-button")
        }

        //Sản phẩm gần nhất

        _buttonMoreRecentlyProduct() {
            var show_element = document.getElementById("show-info-recently-product");
            show_element.classList.remove("block-client-bills-hide")
            show_element.classList.add("block-client-bills-show")
            var more_element = document.getElementById("more-recently-product");
            more_element.classList.add("block-more-button")
        }

        _buttonShowinfoDownRecentlyProduct() {
            var show_element = document.getElementById("show-info-recently-product");
            show_element.classList.remove("block-client-none")
            var show_button_show_up = document.getElementById("show-info-up-recently-Product");
            show_button_show_up.classList.remove("button-show-info-up")
            var hide_button_show_down = document.getElementById("show-info-down-recently-Product");
            hide_button_show_down.classList.add("info-caret-none")
        }

        _buttonShowinfoUpRecentlyProduct() {
            var hide_element = document.getElementById("show-info-recently-product");
            hide_element.classList.add("block-client-none")
            hide_element.classList.add("block-client-bills-hide")
            hide_element.classList.remove("block-client-bills-show")
            var show_button_show_down = document.getElementById("show-info-down-recently-Product");
            show_button_show_down.classList.remove("info-caret-none")
            var hide_button_show_up = document.getElementById("show-info-up-recently-Product");
            hide_button_show_up.classList.add("button-show-info-up")
            var more_element = document.getElementById("more-recently-product");
            more_element.classList.remove("block-more-button")
        }

        //Sản phẩm đã mua
        _buttonShowinfoDownBrandCategory() {
            var show_element = document.getElementById("show-info-recently-brand-category");
            show_element.classList.remove("block-client-none")
            var show_button_show_up = document.getElementById("show-info-up-brand-category");
            show_button_show_up.classList.remove("button-show-info-up")
            var hide_button_show_down = document.getElementById("show-info-down-brand-category");
            hide_button_show_down.classList.add("info-caret-none")
        }

        _buttonShowinfoUpRecentlyBrandCategory() {
            var hide_element = document.getElementById("show-info-recently-brand-category");
            hide_element.classList.add("block-client-none")
            var show_button_show_down = document.getElementById("show-info-down-brand-category");
            show_button_show_down.classList.remove("info-caret-none")
            var hide_button_show_up = document.getElementById("show-info-up-brand-category");
            hide_button_show_up.classList.add("button-show-info-up")
        }

        isEditPhone(phone) {
            const cashier = this.env.pos.get('cashier') || this.env.pos.get_cashier();
            if (cashier.role === 'manager' || !this.props.partner.id || phone === this.props.partner.phone) {
                return phone;
            } else {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'),
                    body: this.env._t("Chỉ quản lý được sửa số điện thoại khách hàng."),
                });
                return false;
            }
        }


        saveChanges() {
            // if (!this.props.partner.id) {
            //KH duoc tao tai POS
            const phone = document.getElementsByClassName('detail client-phone')[0].value;
            const email = document.getElementsByClassName('detail client-email')[0].value;
            const district = document.getElementsByClassName('client-address-district')[0].value;
            const city = document.getElementsByClassName('s-client-address-city')[0].value;
            const client_birthday_day = document.getElementsByClassName('client-birthday-day')[0].value;
            const client_birthday_month = document.getElementsByClassName('client-birthday-month')[0].value;
            const client_birthday_year = document.getElementsByClassName('client-birthday-year')[0].value;
            const is_edit_phone = this.isEditPhone(phone);
            if (!is_edit_phone) {
                return;
            }
            if (!phone) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'),
                    body: this.env._t("Chưa có thông tin số điện thoại khách hàng."),
                });
                return;
            } else if (!this.is_phonenumber(phone)) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'),
                    body: this.env._t("Số điện thoại không hợp lệ."),
                });
                return;
            } else if (!email) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'),
                    body: this.env._t("Chưa có thông tin email khách hàng."),
                });
                return;
            } else if (!district) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'),
                    body: this.env._t("Chưa có thông tin quận huyện."),
                });
                return;
            } else if (!city) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'),
                    body: this.env._t("Chưa có thông tin thành phố."),
                });
                return;
            } else if (!client_birthday_day || !client_birthday_month || !client_birthday_year) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Lỗi người dùng'),
                    body: this.env._t("Chưa có thông tin ngày tháng năm sinh khách hàng."),
                });
                return;
            } else {
                this.changes.pos_create_customer = this.env.pos.config.name;
                this.changes.s_pos_order_id = this.env.pos.config.id;
            }
            ;
            // KH co don hang dau tien la KH moi
            // this.changes.is_new_customer = true;
            // }
            super.saveChanges();
        }
    }
    Registries.Component.extend(ClientDetailsEdit, SCustomerPos)
    return SCustomerPos

});

