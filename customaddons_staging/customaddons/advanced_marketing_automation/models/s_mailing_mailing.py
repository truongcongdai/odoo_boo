from datetime import datetime, timedelta
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.osv import expression
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SMailingMailingInherit(models.Model):
    _inherit = 'mailing.mailing'

    s_is_zalo_sms_marketing = fields.Boolean("Is Zalo Sms Marketing")
    s_zalo_zns_template_id = fields.Many2one('zns.template', string='ZNS Template')
    s_type = fields.Selection([("once_send", "Gửi một lần"), ("repeat_send", "Gửi nhiều lần")],
                              string="Kiểu gửi tin nhắn", default="once_send", required=True)
    s_type_send_sms = fields.Selection([('birthday', "Chúc mừng sinh nhật"), ('completed_buy', 'Hoàn thành mua hàng')],
                                       string="Loại tin nhắn")
    apply_order = fields.Selection([
        ('sale_order', 'Sale Order'),
        ('pos_order', 'Pos Order')
    ], string='Áp dụng cho')
    s_is_check_quota_remaining = fields.Boolean(string="Check quota", compute='_compute_quota_remaining', store=True)

    # Compute check quota remaining SMS Zalo
    def _compute_quota_remaining(self):
        for rec in self:
            rec.s_is_check_quota_remaining = False
            ir_config_param_obj = rec.env['ir.config_parameter'].sudo()
            if (ir_config_param_obj.get_param("advanced_integrate_zalo.zalo_mode") and
                    ir_config_param_obj.get_param("advanced_marketing_automation.zalo_remaining_quota")):
                if (ir_config_param_obj.get_param("advanced_integrate_zalo.zalo_mode") == "product"
                        and ir_config_param_obj.get_param("advanced_marketing_automation.zalo_remaining_quota") == 0):
                    rec.s_is_check_quota_remaining = True

    @api.onchange("s_zalo_zns_template_id")
    def _onchange_body_plaintex(self):
        if self.s_zalo_zns_template_id:
            self.body_plaintext = self.s_zalo_zns_template_id.name
        else:
            self.body_plaintext = ""

    # Default domain khi thay đổi field áp dụng
    @api.onchange('apply_order')
    def onchange_type_marketing(self):
        if self.apply_order == 'pos_order':
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'pos.order')], limit=1)
            if model_id:
                self.sudo().write({
                    "mailing_model_id": model_id.id
                })
                self.sudo().write({
                    "mailing_domain": "[['is_order_payment', '=', True], ['is_send_message', '=', False]]"
                })
        elif self.apply_order == 'sale_order':
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'sale.order')], limit=1)
            if model_id:
                self.sudo().write({
                    "mailing_model_id": model_id.id
                })
                self.sudo().write({
                    "mailing_domain": "[['is_order_done', '=', True], ['is_send_message', '=', False]]"
                })

    def _send_sms_get_composer_values(self, res_ids):
        res = super(SMailingMailingInherit, self)._send_sms_get_composer_values(res_ids)
        s_total_amount = 0
        s_point = 0
        if '${total_amount}' in res.get('body') or '${point}' in res.get('body'):
            if self.marketing_activity_ids.campaign_id.type_marketing == 'hon_thanh_mua_hang':

                if self.marketing_activity_ids.campaign_id.apply_order == 'pos_order':
                    pos_order = self.marketing_activity_ids.trace_ids.participant_id.resource_ref
                    if pos_order:
                        s_total_amount = pos_order.amount_total
                        s_point = pos_order.loyalty_points
                elif self.marketing_activity_ids.campaign_id.apply_order == 'sale_order':
                    sale_order = self.marketing_activity_ids.trace_ids.participant_id.resource_ref
                    if sale_order:
                        s_total_amount = sale_order.amount_total
                        s_point = sale_order.loyalty_points
        s_body = res.get('body')
        s_body = s_body.replace('${total_amount}', str(s_total_amount))
        s_body = s_body.replace('${point}', str(s_point))
        res.update({
            'body': s_body
        })
        return res

    # Check nếu bị duplicate sms thì sms không đổi state
    @api.model
    def _process_mass_mailing_queue(self):
        mass_mailings = self.search(
            [('state', 'in', ('in_queue', 'sending')), '|', ('schedule_date', '<', fields.Datetime.now()),
             ('schedule_date', '=', False)])
        for mass_mailing in mass_mailings:
            user = mass_mailing.write_uid or self.env.user
            mass_mailing = mass_mailing.with_context(**user.with_user(user).context_get())
            if len(mass_mailing._get_remaining_recipients()) > 0:
                mass_mailing.state = 'sending'
                mass_mailing.action_send_mail()
            else:
                if mass_mailing.s_type == 'repeat_send':
                    mass_mailing.write({
                        'state': 'in_queue',
                    })
                else:
                    mass_mailing.write({
                        'state': 'done',
                        'sent_date': fields.Datetime.now(),
                        # send the KPI mail only if it's the first sending
                        'kpi_mail_required': not mass_mailing.sent_date,
                    })

    # Check nếu có traces = outgoing thì mới đổi state = sent
    def action_send_sms(self, res_ids=None):
        for mailing in self:
            if not res_ids:
                res_ids = mailing._get_remaining_recipients()
            if res_ids:
                composer = self.env['sms.composer'].with_context(active_id=False).create(
                    mailing._send_sms_get_composer_values(res_ids))
                composer._action_send_sms()

                if mailing.s_type == 'repeat_send' and mailing.mailing_trace_ids:
                    for trace_id in mailing.mailing_trace_ids:
                        if trace_id.sent_datetime:
                            if trace_id.sent_datetime.strftime("%Y/%m/%d") != datetime.now().strftime("%Y/%m/%d") and trace_id.trace_status == 'sent' and trace_id.s_done_repeat == False:
                                trace_id.s_done_repeat = True

            # Create sms blacklist in bounced
            if mailing.mailing_trace_ids:
                for trace_id in mailing.mailing_trace_ids:
                    if trace_id.failure_type == 'sms_blacklist':
                        trace_id.set_bounced()
            if not mailing.s_type == 'repeat_send':
                mailing.write({
                    'state': 'done',
                    'sent_date': fields.Datetime.now(),
                    'kpi_mail_required': not mailing.sent_date,
                })
            else:
                traces_status = mailing.mailing_trace_ids.search([('mass_mailing_id', '=', mailing.id)]).mapped(
                    'trace_status')
                if traces_status:
                    if 'outgoing' in traces_status:
                        mailing.write({
                            'state': 'done',
                            'sent_date': fields.Datetime.now(),
                            'kpi_mail_required': not mailing.sent_date,
                        })
                    else:
                        mailing.write({
                            'state': 'in_queue',
                        })
        return True

    # Xóa những sms đã được nhận
    def _get_remaining_recipients(self):
        res_ids = self._get_recipients()
        trace_domain = [('model', '=', self.mailing_model_real)]
        if self.ab_testing_enabled and self.ab_testing_pc == 100:
            trace_domain = expression.AND(
                [trace_domain, [('mass_mailing_id', 'in', self._get_ab_testing_siblings_mailings().ids)]])
        else:
            trace_domain = expression.AND([trace_domain, [
                ('res_id', 'in', res_ids),
                ('mass_mailing_id', '=', self.id),
            ]])
        already_mailed = self.env['mailing.trace'].search_read(trace_domain, ['res_id'])
        done_res_ids = {record['res_id'] for record in already_mailed}
        if self.s_type == 'repeat_send' and self.mailing_trace_ids:
            for trace_id in self.mailing_trace_ids:
                if trace_id.sent_datetime:
                    if trace_id.sent_datetime.strftime("%Y/%m/%d") != datetime.now().strftime(
                            "%Y/%m/%d") and trace_id.trace_status == 'sent' and trace_id.res_id in done_res_ids and trace_id.s_done_repeat == False:
                        done_res_ids.remove(trace_id.res_id)
        return [rid for rid in res_ids if rid not in done_res_ids]

    # Xóa danh sách tin nhắn đã seen
    def _get_seen_list_sms(self):
        """Returns a set of emails already targeted by current mailing/campaign (no duplicates)"""
        self.ensure_one()
        target = self.env[self.mailing_model_real]

        partner_fields = []
        if issubclass(type(target), self.pool['mail.thread.phone']):
            phone_fields = ['phone_sanitized']
        elif issubclass(type(target), self.pool['mail.thread']):
            phone_fields = [
                fname for fname in target._sms_get_number_fields()
                if fname in target._fields and target._fields[fname].store
            ]
            partner_fields = target._sms_get_partner_fields()
        else:
            phone_fields = []
            if 'mobile' in target._fields and target._fields['mobile'].store:
                phone_fields.append('mobile')
            if 'phone' in target._fields and target._fields['phone'].store:
                phone_fields.append('phone')
        partner_field = next(
            (fname for fname in partner_fields if
             target._fields[fname].store and target._fields[fname].type == 'many2one'),
            False
        )
        if not phone_fields and not partner_field:
            raise UserError(_("Unsupported %s for mass SMS", self.mailing_model_id.name))

        query = """
            SELECT %(select_query)s
              FROM mailing_trace trace
              JOIN %(target_table)s target ON (trace.res_id = target.id)
              %(join_add_query)s
             WHERE (%(where_query)s)
               AND trace.mass_mailing_id = %%(mailing_id)s
               AND trace.model = %%(target_model)s
        """
        if phone_fields:
            # phone fields are checked on target mailed model
            select_query = 'target.id, ' + ', '.join('target.%s' % fname for fname in phone_fields)
            where_query = ' OR '.join('target.%s IS NOT NULL' % fname for fname in phone_fields)
            join_add_query = ''
        else:
            # phone fields are checked on res.partner model
            partner_phone_fields = ['mobile', 'phone']
            select_query = 'target.id, ' + ', '.join('partner.%s' % fname for fname in partner_phone_fields)
            where_query = ' OR '.join('partner.%s IS NOT NULL' % fname for fname in partner_phone_fields)
            join_add_query = 'JOIN res_partner partner ON (target.%s = partner.id)' % partner_field

        query = query % {
            'select_query': select_query,
            'where_query': where_query,
            'target_table': target._table,
            'join_add_query': join_add_query,
        }
        params = {'mailing_id': self.id, 'target_model': self.mailing_model_real}
        self._cr.execute(query, params)
        query_res = self._cr.fetchall()
        if self.s_type == 'repeat_send' and self.mailing_trace_ids:
            for trace_id in self.mailing_trace_ids:
                if trace_id.sent_datetime:
                    if trace_id.sent_datetime.strftime("%Y/%m/%d") != datetime.now().strftime(
                            "%Y/%m/%d") and trace_id.trace_status == 'sent' and trace_id.s_done_repeat == False:
                        query_res.remove((trace_id.res_id, trace_id.sms_number))
        seen_list = set(number for item in query_res for number in item[1:] if number)
        seen_ids = set(item[0] for item in query_res)
        _logger.info("Mass SMS %s targets %s: already reached %s SMS", self, target._name, len(seen_list))
        return list(seen_ids), list(seen_list)

    @api.onchange('s_type_send_sms')
    def _onchange_is_birthday(self):
        if self.s_type_send_sms == 'birthday':
            model_id = self.env['ir.model'].sudo().search([('model', '=', 'res.partner')], limit=1)
            if model_id:
                self.sudo().write({
                    "mailing_model_id": model_id.id
                })
            self.mailing_domain = [['is_birthday', '=', True]]
