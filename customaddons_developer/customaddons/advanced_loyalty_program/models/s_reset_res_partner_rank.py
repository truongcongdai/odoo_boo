from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import pytz
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class SResetPartnerRank(models.Model):
    _name = 'reset.partner.rank'
    # ranked = fields.Many2one('s.customer.rank', string='Hạng')
    # date_scheduler = fields.Date(string='Ngày thực thi')
    # run_scheduler = fields.Boolean(string='Thực thi')
    # time_run_scheduler = fields.Datetime(string='Thời gian thực thi reset', readonly=True)

    @api.constrains('run_scheduler')
    def _check_run_scheduler(self):
        self.ensure_one()
        if self.run_scheduler:
            if self.env['reset.partner.rank'].search_count([('run_scheduler', '=', True)]) > 1:
                raise ValidationError('Config thực thi reset hạng khách hàng đã đạt giới hạn)')
    def _cron_reset_customer_ranked(self):
        start_time = time.time()
        config_time = self.env['ir.config_parameter'].sudo().get_param('loyalty.period_reset_customer_rank', False)
        value_config_period = self.env['ir.config_parameter'].sudo().get_param('loyalty.value_config_period', False)
        if config_time and value_config_period:
            run_scheduler = datetime.strptime(config_time, '%Y-%m-%d %H:%M:%S')
            user_tz = self.env.user.tz or pytz.utc
            time_now = fields.Datetime.now()
            datetime_tz_now = datetime.strptime(datetime.strftime(pytz.utc.localize(time_now).astimezone(pytz.timezone(user_tz)), "%Y-%m-%d %H:%M:%S"), '%Y-%m-%d %H:%M:%S')
            if datetime_tz_now >= run_scheduler:
                customer_rank_was_reset = self.env.ref('advanced_loyalty_program.s_parameter_customer_rank_was_reset')
                all_rank = self.env['s.customer.rank'].sudo().search([]).sorted(key='total_amount')
                lowest_rank = all_rank[0].rank
                if len(all_rank) > 0:
                    if customer_rank_was_reset.value == 'True':
                        for rank_id in all_rank:
                            log = []
                            if rank_id.id != all_rank[0].id:
                                query_partner = self._cr.execute("""
                                    SELECT id FROM res_partner WHERE type = 'contact' AND phone IS NOT NULL AND customer_ranked = %s AND active = TRUE;
                                """, (rank_id.rank,))
                                result = [res[0] for res in self._cr.fetchall()]
                                if len(result) > 0:
                                    ###Tìm khách hàng có doanh thu trong kỳ đủ điều kiện giữ hạng
                                    query_keep_rank = self._cr.execute("""
                                        SELECT id FROM res_partner WHERE id IN %s AND total_period_revenue IS NOT NULL AND total_period_revenue > 0 AND total_period_revenue >= %s;
                                    """, (tuple(result), rank_id.total_amount))
                                    result_keep_rank = [res[0] for res in self._cr.fetchall()]
                                    if result_keep_rank:
                                        update_keep_rank = self._cr.execute("""
                                            UPDATE res_partner SET s_keep_rank = TRUE WHERE id IN %s
                                        """, (tuple(result_keep_rank),))
                                    ###Tìm khách hàng có doanh thu trong kỳ không đủ điều kiện giữ hạng
                                    query_down_rank = self._cr.execute("""
                                        SELECT id FROM res_partner WHERE id IN %s AND (total_period_revenue >= 0 AND total_period_revenue < %s);
                                    """, (tuple(result), rank_id.total_amount))
                                    result_down_rank = [res[0] for res in self._cr.fetchall()]
                                    if result_down_rank:
                                        update_down_rank = self._cr.execute("""
                                            UPDATE res_partner SET customer_ranked = %s,check_sync_customer_rank = FALSE,s_keep_rank = FALSE,related_customer_ranked = %s WHERE id in %s
                                        """, (lowest_rank, all_rank[0].id, tuple(result_down_rank)))
                                    ###Tự động reset doanh thu trong kỳ về 0 khi reset hạng khách hàng
                                    query_update_partner = self._cr.execute("""
                                        UPDATE res_partner SET total_period_revenue = 0 WHERE id in %s;
                                    """, (tuple(result),))
                                    log.append({
                                        'old_rank': rank_id.rank,
                                        'customer_id': result
                                    })
                                    self.env['ir.logging'].sudo().create({
                                        'name': 'Ghi nhận reset hạng khách hàng',
                                        'type': 'server',
                                        'dbname': 'boo',
                                        'level': 'INFO',
                                        'message': str(log),
                                        'path': 'url',
                                        'func': '_cron_reset_customer_ranked',
                                        'line': '0',
                                    })
                            else:
                                query_partner = self._cr.execute("""
                                    UPDATE res_partner SET total_period_revenue = 0,s_keep_rank = FALSE,related_customer_ranked = %s,check_sync_customer_rank = FALSE WHERE type = 'contact' AND phone IS NOT NULL AND customer_ranked = %s;
                                """, (rank_id.id, rank_id.rank))
                    else:
                        query_update_partner = self._cr.execute("""
                            UPDATE res_partner SET total_period_revenue = 0,s_keep_rank = TRUE WHERE customer_ranked is not null and type = 'contact' AND phone IS NOT NULL;
                        """)
                        ###Lần đầu reset hạng sẽ set loyalty_points = 0 (không sử dụng query được -> sử dụng hàm write)
                        # query_update_partner = self.env['res.partner'].sudo().search([('customer_ranked', '!=', False), ('type', '=', 'contact'), ('phone', '!=', False)]).write({
                        #     'loyalty_points': 0,
                        # })
                    next_scheduler = str(run_scheduler + relativedelta(years=int(value_config_period)))
                    self.env['ir.config_parameter'].sudo().set_param('loyalty.period_reset_customer_rank', next_scheduler)
                    customer_rank_was_reset.value = 'True'
                    check_time = time.time() - start_time
                    print('Thời gian chạy: ', check_time)


class SPartnerRankReset(models.Model):
    _inherit = "res.partner"

    s_keep_rank = fields.Boolean(string='Giữ hạng', default=False)

    def write(self, vals):
        res = super(SPartnerRankReset, self).write(vals)
        ####Trước khi reset hạng khách hàng vẫn tính hạng theo loyalty point
        ####Sau khi reset hạng khách hàng sẽ tính hạng theo doanh thu trong kỳ
        customer_rank_was_reset = self.env.ref('advanced_loyalty_program.s_parameter_customer_rank_was_reset')
        if customer_rank_was_reset.sudo().value == 'True':
            if vals.get('total_period_revenue'):
                all_ranks = self.env['s.customer.rank'].sudo().search([('total_amount', '<=', self.total_period_revenue)]).sorted(key='total_amount')
                present_rank = self.env['s.customer.rank'].sudo().search([('rank', '=', self.customer_ranked)])
                if all_ranks and not self.s_keep_rank:
                    self.sudo().update({
                        'customer_ranked': all_ranks[-1].rank,
                        'related_customer_ranked': all_ranks[-1].id,
                    })
                elif all_ranks and self.s_keep_rank:
                    if present_rank.total_amount < all_ranks[-1].total_amount:
                        self.sudo().update({
                            'customer_ranked': all_ranks[-1].rank,
                            'related_customer_ranked': all_ranks[-1].id,
                            's_keep_rank': False,
                        })
                    elif present_rank.total_amount == all_ranks[-1].total_amount:
                        if not self.customer_ranked or not self.related_customer_ranked:
                            self.sudo().update({
                                'customer_ranked': present_rank.rank,
                                'related_customer_ranked': present_rank.id,
                            })
        else:
            if vals.get('loyalty_points'):
                all_ranks = self.env['s.customer.rank'].sudo().search([('total_amount', '<=', self.loyalty_points)]).sorted(key='total_amount')
                if all_ranks:
                    self.sudo().update({
                        'customer_ranked': all_ranks[-1].rank,
                        'related_customer_ranked': all_ranks[-1].id,
                    })
        return res

    @api.model
    def create(self, vals_list):
        res = super(SPartnerRankReset, self).create(vals_list)
        if res and res.loyalty_points == 0 and not res.parent_id:
            all_ranks = self.env['s.customer.rank'].sudo().search([]).sorted(key='total_amount')
            if all_ranks:
                self.sudo().write({
                    'customer_ranked': all_ranks[0].rank,
                    'related_customer_ranked': all_ranks[0].id,
                })
        return res

    def _compute_customer_rank(self):
        all_ranks = self.env['s.customer.rank'].sudo().search([])
        for rec in self:
            record_customer_ranked = ''
            # pos_order_ids = rec.pos_order_ids.filtered(lambda am: am.state == 'paid' or am.state == 'invoiced')
            # sale_order_invoiced = self.get_amount_so_invoice(rec.sale_order_ids)
            # amount_pos_order = self.get_amount_pos_order(pos_order_ids)
            # total_amount = amount_pos_order + sale_order_invoiced
            if not rec.parent_id:
                customer_rank_was_reset = self.env.ref('advanced_loyalty_program.s_parameter_customer_rank_was_reset')
                if customer_rank_was_reset.sudo().value == 'True':
                    rank_list = all_ranks.filtered(lambda rank: rank.total_amount <= rec.total_period_revenue).sorted(key='total_amount')
                    if rank_list:
                        rec.sudo().customer_ranked = rank_list[-1].rank
                        rec.sudo().related_customer_ranked = rank_list[-1].id
                else:
                    rank_list = all_ranks.filtered(lambda rank: rank.total_amount <= rec.loyalty_points).sorted(key='total_amount')
                    if rank_list:
                        rec.sudo().customer_ranked = rank_list[-1].rank
                        rec.sudo().related_customer_ranked = rank_list[-1].id
