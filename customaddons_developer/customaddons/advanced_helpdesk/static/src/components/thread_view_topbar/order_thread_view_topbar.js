/** @odoo-module **/

import {registerMessagingComponent} from '@mail/utils/messaging_component';
import {useRefToModel} from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import {useUpdateToModel} from '@mail/component_hooks/use_update_to_model/use_update_to_model';

const {Component} = owl;

class OrderThreadViewTopbar extends Component {
    setup() {
        super.setup();
    }

    get thread() {
        return this.messaging && this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }
    async _onClickOrder(ev) {
        ev.stopPropagation();
        return this.env.bus.trigger('do-action', {
            action: {
                name: this.env._t("Orders"),
                type: 'ir.actions.act_window',
                res_model: 'sale.order',
                views: [[false, 'list'], [false, 'form']],
                domain: [['s_thread_id', '=', this.thread.id]],
                context: {
                    'default_s_thread_id': this.thread.id,
                    'default_s_facebook_sender_id': this.thread.s_facebook_sender_id ? this.thread.s_facebook_sender_id : null,
                    'default_s_zalo_sender_id': this.thread.s_zalo_sender_id ? this.thread.s_zalo_sender_id : null,
                    'default_partner_id': this.thread.s_partner_id ? this.thread.s_partner_id : false,
                    'default_source_id': this.thread.s_source_id ? this.thread.s_source_id: false,
                    'default_is_magento_order': true,
                }
            },
        });
    }
}

Object.assign(OrderThreadViewTopbar, {
    props: {
        threadLocalId: String,
    },
    template: 'advanced_helpdesk.OrderThreadViewTopbar',
});

registerMessagingComponent(OrderThreadViewTopbar);

export default OrderThreadViewTopbar;
