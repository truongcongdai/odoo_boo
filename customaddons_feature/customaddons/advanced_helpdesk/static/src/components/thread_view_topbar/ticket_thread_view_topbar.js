/** @odoo-module **/

import {registerMessagingComponent} from '@mail/utils/messaging_component';
import {useRefToModel} from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import {useUpdateToModel} from '@mail/component_hooks/use_update_to_model/use_update_to_model';

const {Component} = owl;

class TicketThreadViewTopbar extends Component {
    setup() {
        super.setup();
    }

    get thread() {
        return this.messaging && this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    async _onClickDoneTicket() {
        let done_ticket = await this.rpc({
            model: 'mail.channel',
            method: 'btn_done_ticket',
            args: [this.thread.id],
        });
        if (done_ticket) {
            this.env.services['notification'].notify({
                message: this.env._t("Done Ticket Thành Công!"),
                type: 'info',
            });
            return;
        } else {
            this.env.services['notification'].notify({
                message: this.env._t("Không Có Ticket"),
                type: 'warning',
            });
            return;
        }
    }
}

Object.assign(TicketThreadViewTopbar, {
    props: {
        threadLocalId: String,
    },
    template: 'advanced_helpdesk.DoneTicketThreadViewTopbar',
});

registerMessagingComponent(TicketThreadViewTopbar);

export default TicketThreadViewTopbar;
