/** @odoo-module **/
import {
    registerInstancePatchModel,
} from '@mail/model/model_core';

registerInstancePatchModel('mail.messaging_notification_handler', 'advanced_helpdesk/static/src/components/discuss/s_messaging_notification_handler.js', {
    async _handleNotificationChannelMessage({id: channelId, message: messageData}) {
        const res = this._super(...arguments);
        let channel = this.messaging.models['mail.thread'].findFromIdentifyingData({
            id: channelId,
            model: 'mail.channel',
        });
        // Hiển thị window chat đối với channel
        if (channel) {
            if (typeof channel.channel_type !== 'undefined') {
                if (channel.channel_type === 'channel' && !this.messaging.device.isMobile && !channel.chatWindow) {
                    this.messaging.chatWindowManager.openThread(channel);
                }
            }
        } else if (!channel) {
            channel = (await this.async(() =>
                this.messaging.models['mail.thread'].performRpcChannelInfo({ids: [channelId]})
            ))[0];
            if (typeof channel.channel_type !== 'undefined') {
                if (channel.channel_type === 'channel' && !this.messaging.device.isMobile && !channel.chatWindow) {
                    this.messaging.chatWindowManager.openThread(channel);
                }
            }
        }
        return res;
    }
});

