import logging
import threading
from odoo import api, fields, models, tools, _
from odoo.addons.phone_validation.tools import phone_validation
from datetime import timedelta

_logger = logging.getLogger(__name__)


class SmsSmsInherit(models.Model):
    _inherit = 'sms.sms'

    def _zalo_send(self):
        success_results = []
        error_results = []
        for rec in self:
            try:
                if rec.mailing_id and rec.mailing_id.s_is_zalo_sms_marketing:
                    zalo_mode = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_zalo.zalo_mode')
                    # numbers = [number.strip() for number in self.numbers.splitlines()]
                    # sanitize_res = phone_validation.phone_sanitize_numbers_w_record([rec.partner_id.phone],
                    #                                                                 rec.partner_id,
                    #                                                                 rec.partner_id.country_id)
                    # sanitized_numbers = [info['sanitized'] for info in sanitize_res.values() if info['sanitized']]
                    # invalid_numbers = [number for number, info in sanitize_res.items() if info['code']]
                    phone = rec.partner_id.phone.replace('0', '84', 1) if rec.partner_id.phone else ""
                    mailing_trace_id = rec.mailing_trace_ids.filtered(lambda l: l.sms_sms_id.id == rec.id)
                    data = {
                        "phone": phone,
                        "template_id": rec.mailing_id.s_zalo_zns_template_id.s_template_id,
                        "template_data": {
                            "customer_name": rec.partner_id.name,
                            "company_name": self.env.company.name if self.env.company.name else '',
                        },
                        "tracking_id": mailing_trace_id[0].id
                    }
                    if zalo_mode == 'sandbox':
                        data['mode'] = 'development'
                    if rec.mailing_id.mailing_model_id.model in ['sale.order', 'pos.order']:
                        if len(rec.mailing_trace_ids) > 0:
                            for trace in rec.mailing_trace_ids:
                                if trace.marketing_trace_id and trace.marketing_trace_id.participant_id:
                                    participant = trace.marketing_trace_id.participant_id
                                    if participant.resource_ref:
                                        if participant.resource_ref._name == 'pos.order':
                                            pos_reference_name = participant.resource_ref.pos_reference
                                            if 'Đơn hàng' in participant.resource_ref.pos_reference:
                                                pos_reference_name = participant.resource_ref.pos_reference.strip(
                                                    'Đơn hàng')
                                            elif 'Order' in participant.resource_ref.pos_reference:
                                                pos_reference_name = participant.resource_ref.pos_reference.strip('Order')
                                            data['template_data'].update({
                                                'cost': participant.resource_ref.amount_total,
                                                'total_point': participant.resource_ref.partner_id.loyalty_points if participant.resource_ref.partner_id else 0,
                                                'order_date': str(
                                                    (participant.resource_ref.date_order + timedelta(hours=7)).strftime(
                                                        "%H:%M %d/%m/%Y")),
                                                'order_code': pos_reference_name
                                            })
                                        elif participant.resource_ref._name == 'sale.order':
                                            amount_total = 0
                                            total_points = 0
                                            order_line_ids = participant.resource_ref.order_line.filtered(
                                                lambda l: l.qty_delivered or l.product_id.la_phi_ship_hang_m2)
                                            for order_line_id in order_line_ids:
                                                if order_line_id.product_id.detailed_type == 'product':
                                                    amount_total += (order_line_id.qty_delivered * order_line_id.price_unit
                                                                     - ((order_line_id.boo_total_discount_percentage /
                                                                         order_line_id.product_uom_qty) *
                                                                        order_line_id.qty_delivered))
                                                else:
                                                    amount_total += order_line_id.price_total
                                            sale_order_name = participant.resource_ref.name
                                            if 'Đổi trả' in participant.resource_ref.name:
                                                sale_order_name = participant.resource_ref.name.split()[0]
                                            # s_history_loyalty_points = self.env[
                                            #     's.order.history.points'].sudo().search(
                                            #     [('sale_order_id', '=', participant.resource_ref.id)], limit=1)
                                            # if s_history_loyalty_points:
                                            #     total_points = s_history_loyalty_points.diem_cong
                                            data['template_data'].update({
                                                'cost': amount_total,
                                                'total_point': participant.resource_ref.partner_id.loyalty_points if participant.resource_ref.partner_id else 0,
                                                'order_date': str(
                                                    (participant.resource_ref.completed_date + timedelta(hours=7)).strftime(
                                                        "%H:%M %d/%m/%Y")),
                                                'order_code': sale_order_name
                                            })
                                        if data.get("template_data").get("company_name"):
                                            data.get("template_data").pop("company_name")
                    if data:
                        ir_config_param_obj = self.env['ir.config_parameter'].sudo()
                        if (ir_config_param_obj.get_param('advanced_marketing_automation.zalo_remaining_quota')
                                and ir_config_param_obj.get_param('advanced_integrate_zalo.zalo_mode')):
                            if (int(ir_config_param_obj.get_param('advanced_marketing_automation.zalo_remaining_quota')) == 0
                                    and ir_config_param_obj.get_param('advanced_integrate_zalo.zalo_mode') == 'product'):
                                self.env['ir.logging'].sudo().create({
                                    'name': 'zalo-send',
                                    'type': 'server',
                                    'dbname': 'boo',
                                    'level': 'ERROR',
                                    'path': 'url',
                                    'message': 'Gửi quá giới hạn SMS Zalo!',
                                    'func': '_zalo_send',
                                    'line': '0',
                                })
                                return
                        zalo_result = rec.s_send_data_zns(data)
                        if zalo_result['state'] == 'success':
                            rec.mailing_trace_ids.write({
                                's_zalo_msg_id': zalo_result.get('msg_id')
                            })
                            success_results.append(zalo_result)
                            ir_config_param_obj.set_param('advanced_marketing_automation.zalo_remaining_quota', zalo_result['quota'])
                        else:
                            rec.mailing_trace_ids.write({
                                's_zalo_state_msg': zalo_result.get('message')
                            })
                            if rec.mailing_trace_ids.marketing_trace_id:
                                if rec.mailing_trace_ids.marketing_trace_id.participant_id:
                                    if rec.mailing_trace_ids.marketing_trace_id.participant_id.resource_ref:
                                        rec.mailing_trace_ids.marketing_trace_id.participant_id.resource_ref.sudo().write({
                                            'send_message_error': True
                                        })
                            error_results.append({
                                'res_id': zalo_result.get('res_id'),
                                'state': zalo_result.get('state'),
                            })
            except Exception as e:
                rec.mailing_trace_ids.write({
                    's_zalo_state_msg': str(e)
                })
                error_results.append({
                    'res_id': self.id,
                    'state': 'server_error',
                })

        return {
            'success_results': success_results,
            'error_results': error_results,
        }

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """ This method tries to send SMS after checking the number (presence and
        formatting). """
        s_zalo_sms = self.filtered(lambda s: s.mailing_id and s.mailing_id.s_is_zalo_sms_marketing)
        s_sms = self - s_zalo_sms
        try:
            if len(s_zalo_sms) > 0:
                try:
                    zalo_results = self._zalo_send()
                except Exception as e:
                    _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(self.ids), self.ids, e)
                    if raise_exception:
                        raise
                    self._postprocess_iap_sent_sms(
                        [{'res_id': sms.id, 'state': 'server_error'} for sms in self],
                        unlink_failed=unlink_failed, unlink_sent=unlink_sent)
                else:
                    _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, 'iap_results')
                    if zalo_results:
                        if zalo_results.get('success_results'):
                            self._postprocess_iap_sent_sms(zalo_results.get('success_results'),
                                                           unlink_failed=unlink_failed, unlink_sent=unlink_sent)
                        if zalo_results.get('error_results'):
                            self._postprocess_iap_sent_sms(zalo_results.get('error_results'),
                                                           unlink_failed=unlink_failed,
                                                           unlink_sent=unlink_sent)
            if len(s_sms) > 0:
                iap_data = [{
                    'res_id': record.id,
                    'number': record.number,
                    'content': record.body,
                } for record in s_sms]

                try:
                    iap_results = self.env['sms.api']._send_sms_batch(iap_data)
                except Exception as e:
                    _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(s_sms.ids), s_sms.ids, e)
                    if raise_exception:
                        raise
                    self._postprocess_iap_sent_sms(
                        [{'res_id': sms.id, 'state': 'server_error'} for sms in s_sms],
                        unlink_failed=unlink_failed, unlink_sent=unlink_sent)
                else:
                    _logger.info('Send batch %s SMS: %s: gave %s', len(s_sms.ids), s_sms.ids, 'iap_results')
                    self._postprocess_iap_sent_sms(iap_results, unlink_failed=unlink_failed, unlink_sent=unlink_sent)
        except Exception as e:
            _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(s_sms.ids), s_sms.ids, e)
            # if raise_exception:
            #     raise
            # self._postprocess_iap_sent_sms(
            #     [{'res_id': sms.id, 'state': 'server_error'} for sms in self],
            #     unlink_failed=unlink_failed, unlink_sent=unlink_sent)

    def _postprocess_iap_sent_sms(self, iap_results, failure_reason=None, unlink_failed=False, unlink_sent=True):
        all_sms_ids = [item['res_id'] for item in iap_results]
        if any(sms.mailing_id for sms in self.env['sms.sms'].sudo().browse(all_sms_ids)):
            for state in self.IAP_TO_SMS_STATE.keys():
                sms_ids = [item['res_id'] for item in iap_results if item['state'] == state]
                traces = self.env['mailing.trace'].sudo().search([
                    ('sms_sms_id_int', 'in', sms_ids)
                ])
                if traces and state == 'success':
                    traces.set_sent()
                    if len(all_sms_ids) == len(sms_ids):
                        if traces.mass_mailing_id and traces.mass_mailing_id.s_type == 'repeat_send':
                            traces.mass_mailing_id.write({
                                'state': 'in_queue'
                            })
                    if traces.mass_mailing_id and traces.mass_mailing_id.s_type_send_sms == 'completed_buy':
                        for trace_id in traces:
                            if trace_id.marketing_trace_id.participant_id:
                                trace_id.marketing_trace_id.participant_id.resource_ref.is_send_message = True
                elif traces:
                    traces.set_failed(failure_type=self.IAP_TO_SMS_STATE[state])
        return super(SmsSmsInherit, self)._postprocess_iap_sent_sms(
            iap_results, failure_reason=failure_reason,
            unlink_failed=unlink_failed, unlink_sent=unlink_sent)

    def s_send_data_zns(self, data):
        api = "/message/template"
        response = self.env['base.integrate.zalo'].post_data_zalo_zns(api, data=data, params=None)
        if response:
            if response['error'] == 0:
                return {
                    'res_id': self.id,
                    'state': 'success',
                    'msg_id': response['data']['msg_id'],
                    'quota': response['data']['quota']['remainingQuota']}

            else:
                return {
                    'res_id': self.id,
                    'state': 'server_error',
                    'message': response['message']}

    @api.model
    def _process_queue(self, ids=None):
        """ Send immediately queued messages, committing after each message is sent.
        This is not transactional and should not be called during another transaction!

       :param list ids: optional list of emails ids to send. If passed no search
         is performed, and these ids are used instead.
        """
        domain = [('state', '=', 'outgoing')]

        filtered_ids = self.search(domain, limit=400).ids  # TDE note: arbitrary limit we might have to update
        if ids:
            ids = list(set(filtered_ids) & set(ids))
        else:
            ids = filtered_ids
        ids.sort()

        res = None
        try:
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.current_thread(), 'testing', False)
            res = self.browse(ids).send(unlink_failed=False, unlink_sent=True, auto_commit=auto_commit,
                                        raise_exception=False)
        except Exception:
            _logger.exception("Failed processing SMS queue")
        return res
