from odoo import fields,models,_


class SSmsComposer(models.TransientModel):
    _inherit = 'sms.composer'

    # Check duplicates in marketing automation
    def _get_done_record_ids(self, records, recipients_info):
        """ Get a list of already-done records. Order of record set is used to
        spot duplicates so pay attention to it if necessary. """
        done_ids, done = [], []
        for record in records:
            sanitized = recipients_info[record.id]['sanitized']
            if sanitized in done:
                if self.mailing_id or self.marketing_activity_id:
                    if self.mailing_id.s_type_send_sms != 'completed_buy' or self.marketing_activity_id.campaign_id.s_is_completed_buy == False:
                        done_ids.append(record.id)
            else:
                done.append(sanitized)
        return done_ids