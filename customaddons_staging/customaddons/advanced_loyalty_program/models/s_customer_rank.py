from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class SCustomerRank(models.Model):
    _name = 's.customer.rank'
    _description = 'Phân hạng khách hàng'
    _rec_name = 'rank'
    _order = 'total_amount desc'
    rank = fields.Char(string='Rank', required=True)
    total_amount = fields.Float(string='Tổng điểm', required=True)

    @api.constrains('rank')
    def _constrains_rank_name(self):
        for r in self:
            if r.rank:
                rank_ids = self.search([('rank', '=', r.rank), ('id', '!=', r.id)])
                if rank_ids:
                    raise ValidationError('Hạng %s đã tồn tại' % r.rank)

    @api.model
    def create(self, vals_list):
        res = super(SCustomerRank, self).create(vals_list)
        res.update_all_customer()
        return res

    def write(self, vals):
        res = super(SCustomerRank, self).write(vals)
        if (vals.get('total_amount') or vals.get('rank')):
            self.update_all_customer()
        return res

    def check_reset_rank(self):
        is_reset_rank = False
        if self.env.ref('advanced_loyalty_program.s_parameter_customer_rank_was_reset').sudo().value == 'True':
            is_reset_rank = True
        return is_reset_rank

    def update_all_customer(self):
        all_customer_rank = self.env['s.customer.rank'].sudo().search([]).sorted(key='total_amount')
        all_customer_rank_list = []
        for e in all_customer_rank:
            all_customer_rank_list.append({
                'id': e.id,
                'rank': e.rank,
                'total_amount': e.total_amount
            })
        all_res_partner = self.env['res.partner'].sudo().search([('type', '=', 'contact')])
        check_reset_rank = self.check_reset_rank()
        for e in all_res_partner:
            if check_reset_rank:
                condition = e.total_period_revenue
            else:
                condition = e.loyalty_points
            current_max_rank_amount = 0
            new_rank_id = False
            new_rank_name = False
            for rank in all_customer_rank_list:
                if condition >= rank['total_amount']:
                    current_max_rank_amount = rank['total_amount']
                    new_rank_id = rank['id']
                    new_rank_name = rank['rank']
            if new_rank_id and new_rank_name:
                ### Chưa có rank
                if not e.related_customer_ranked:
                    e.write({
                        'check_sync_customer_rank': False,
                        'related_customer_ranked': new_rank_id,
                        'customer_ranked': new_rank_name,
                    })
                ### Cập nhập rank mới
                elif e.related_customer_ranked and e.related_customer_ranked.id != new_rank_id:
                    e.write({
                        'check_sync_customer_rank': False,
                        'related_customer_ranked': new_rank_id,
                        'customer_ranked': new_rank_name,
                    })
                ### Cập nhập tên rank mới
                elif e.related_customer_ranked and e.related_customer_ranked.rank != e.customer_ranked:
                    e.write({
                        'customer_ranked': new_rank_name,
                    })

    def unlink(self):
        partner_obj = self.env['res.partner'].sudo().search([('customer_ranked', '!=', False)])
        for r in self:
            # r.magento_delete_customer_group()
            # for partner in partner_obj.filtered(lambda pn: pn.customer_ranked == r.rank):
            #     partner.check_sync_customer_rank = False
            ### Cập nhập xóa rank : update res.partner
            result = partner_obj.filtered(lambda pn: pn.customer_ranked == r.rank)
            if result:
                for partner_id in result:
                    customer_ranked = None
                    customer_rank_ids = self.search(
                        [('total_amount', '<=', partner_id.total_period_revenue), ('id', '!=', self.id)]).sorted(
                        key='total_amount')
                    if customer_rank_ids:
                        customer_ranked = customer_rank_ids[-1].rank
                    if partner_id.check_sync_customer_rank:
                        partner_id.sudo().write({
                            'check_sync_customer_rank': False
                        })
                    partner_id.sudo().write({
                        'customer_ranked': customer_ranked,
                    })
        return super(SCustomerRank, self).unlink()
