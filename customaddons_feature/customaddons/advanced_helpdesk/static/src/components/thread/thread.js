/** @odoo-module **/
import {attr, many2many, many2one, one2many, one2one} from '@mail/model/model_field';
import {
    registerFieldPatchModel,
    registerIdentifyingFieldsPatch,
    registerInstancePatchModel,
    registerClassPatchModel
} from '@mail/model/model_core';

registerFieldPatchModel('mail.thread', 'advanced_helpdesk/static/src/components/thread/thread.js', {
    s_facebook_sender_id: attr(),
    s_zalo_sender_id: attr(),
    s_partner_id: attr(),
    s_source_id: attr(),
});
registerClassPatchModel('mail.thread', 'advanced_helpdesk/static/src/components/thread/thread.js', {
    /**
     * @override
     */
    convertData(data) {
        const res = this._super(data);
        if ('s_facebook_sender_id' in data) {
            res.s_facebook_sender_id = data.s_facebook_sender_id;
        }
        if ('s_zalo_sender_id' in data) {
            res.s_zalo_sender_id = data.s_zalo_sender_id;
        }
        if ('s_partner_id' in data) {
            res.s_partner_id = data.s_partner_id;
        }
        if ('s_source_id' in data){
            res.s_source_id = data.s_source_id;
        }
        return res;
    },
});

