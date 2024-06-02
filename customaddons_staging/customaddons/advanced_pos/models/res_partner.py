from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo import api, models
from datetime import datetime, timedelta


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    # is_new_customer = fields.Boolean(
    #     string='Khách hàng mới',
    #     compute='_compute_is_new_customer',
    #     search='_search_is_new_customer',
    #     compute_sudo=True
    # )
    is_new_customer = fields.Boolean(string='Khách hàng mới')
    last_order = fields.Datetime(string="Thời điểm mua lần cuối")
    district = fields.Char(string="Quận - Text")
    birthday = fields.Date(string="Ngày sinh")
    gender = fields.Selection(selection=[("male", "Male"), ("female", "Female"), ("other", "Other")], tracking=True)
    customer_ranked = fields.Char("Hạng", tracking=True)
    related_customer_ranked = fields.Many2one(comodel_name='s.customer.rank', string='Hạng khách hàng')
    # default=lambda self: self.related_customer_ranked.id (get default rank Member)
    pos_create_customer = fields.Char(string="Địa điểm tạo khách hàng", compute='_compute_pos_create_customer', store=True)
    s_pos_order_id = fields.Many2one('pos.config', string="Địa điểm tạo khách hàng POS")
    history_points_ids = fields.One2many('s.order.history.points', 'res_partner_id', string='Lịch sử tích điểm')
    history_green_points_ids = fields.One2many('s.history.green.points', 'res_partner_id', string='Lịch sử điểm Green')
    check_sync_customer_rank = fields.Boolean(string="Đồng bộ hạng khách hàng")
    # format_birthday = fields.Char(string='Format Birthday', compute="_compute_format_birthday", store=True)
    # property_account_position_id = fields.Many2one('account.fiscal.position', company_dependent=False, default=False)
    # barcode = fields.Char(help="Use a barcode to identify this contact.", copy=False, company_dependent=False, default=False)
    partner_note = fields.Char(string="Ghi chú")
    s_separate_loyalty_points = fields.Char(string="Điểm loyalty")
    s_history_loyalty_point_so_ids = fields.One2many(
        comodel_name='s.history.loyalty.point.so',
        inverse_name='res_partner_id',
        string='Lịch sử tích điểm đơn Online cũ'
    )
    loyalty_points = fields.Float(company_dependent=True,
                                  help='The loyalty points the user won as part of a Loyalty Program', tracking=True)
    # phone_delivery = fields.Char(string='Điện thoại giao hàng')
    is_compute_history_loyalty_point = fields.Boolean(string='Là khách hàng đã Compute lịch sử tích điểm')

    ### Check trùng số điện thoại bên module : advanced_integrate_magento
    # @api.constrains('phone')
    # def constrains_phone(self):
    #     if self.phone:
    #         phone = self.env['res.partner'].search([('phone', '=', self.phone)])
    #         if len(phone) > 1:
    #             raise ValidationError(_('Số điện thoại đã tồn tại.'))

    # Giới hạn dữ liệu tên (tối đa 30 ký tự)
    @api.constrains('name', 'is_warehouse')
    def check_customer_name(self):
        if self.name and len(self.name) > 30 and self.is_warehouse is False:
            raise ValidationError('Trường tên khách hàng chỉ được phép nhập tối đa 30 ký tự (tính cả khoảng trắng).'
                                  '\nSố ký tự tên khách hàng này đang có: %s ' % len(
                self.name) + '\nVui lòng nhập lại.')

    def get_amount_so_invoice(self, sale_order_ids):
        amount_total = 0
        if len(sale_order_ids) > 0:
            for order in sale_order_ids:
                if order.invoice_ids:
                    for invoice in order.invoice_ids:
                        if invoice.payment_state in ['paid', 'partial']:
                            amount_total += invoice.amount_total - invoice.amount_residual
        return amount_total

    def get_amount_pos_order(self, pos_order_ids):
        amount_pos_order = 0
        if len(pos_order_ids) > 0:
            for pos in pos_order_ids:
                amount_pos_order += pos.amount_total
        return amount_pos_order

    ###Chuyển code vào module advanced_loyalty_program
    # def write(self, vals):
    #     res = super(ResPartnerInherit, self).write(vals)
    #     if vals.get('loyalty_points'):
    #         all_ranks = self.env['s.customer.rank'].sudo().search([('total_amount', '<=', self.loyalty_points)]).sorted(
    #             key='total_amount')
    #         # rank_list = all_ranks.filtered(lambda rank: rank.total_amount <= self.loyalty_points).sorted(
    #         #     key='total_amount')
    #         if all_ranks:
    #             self.sudo().write({
    #                 'customer_ranked': all_ranks[-1].rank,
    #                 'related_customer_ranked': all_ranks[-1].id,
    #             })
    #             # self.customer_ranked = all_ranks[-1].rank
    #             # self.sudo().related_customer_ranked = all_ranks[-1].id
    #     return res

    # @api.model
    # def create(self, vals_list):
    #     res = super(ResPartnerInherit, self).create(vals_list)
    #     if res and res.loyalty_points == 0 and not res.parent_id:
    #         customer_rank = self.env['s.customer.rank'].sudo().search([('total_amount', '<=', 0)], limit=1)
    #         if customer_rank:
    #             res.write({
    #                 'customer_ranked': customer_rank[-1].rank,
    #                 'related_customer_ranked': customer_rank[-1].id,
    #             })
    #     return res
    #
    # def _compute_customer_rank(self):
    #     all_ranks = self.env['s.customer.rank'].sudo().search([])
    #     for rec in self:
    #         record_customer_ranked = ''
    #         # pos_order_ids = rec.pos_order_ids.filtered(lambda am: am.state == 'paid' or am.state == 'invoiced')
    #         # sale_order_invoiced = self.get_amount_so_invoice(rec.sale_order_ids)
    #         # amount_pos_order = self.get_amount_pos_order(pos_order_ids)
    #         # total_amount = amount_pos_order + sale_order_invoiced
    #         if not rec.parent_id:
    #             rank_list = all_ranks.filtered(lambda rank: rank.total_amount <= rec.loyalty_points).sorted(
    #                 key='total_amount')
    #             if rank_list:
    #                 rec.customer_ranked = rank_list[-1].rank
    #                 rec.sudo().related_customer_ranked = rank_list[-1].id

    def _edit_last_order(self):
        self.write({
            'last_order': fields.Datetime.now(),
            'check_sync_customer_rank': False
        })

    @api.depends('sale_order_ids', 'pos_order_ids')
    def _compute_is_new_customer(self):
        for r in self:
            if len(r.sale_order_ids) + len(r.pos_order_ids) > 1:
                r.is_new_customer = False
            else:
                r.is_new_customer = True

    def _search_is_new_customer(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValidationError(_('Search not supported!'))
        if operator != '=':
            value = not value

        self._cr.execute("""
        SELECT COUNT(pos.id) + COUNT(so.id) AS count, p.id
        FROM res_partner p LEFT JOIN sale_order so ON so.partner_id = p.id
        LEFT JOIN pos_order pos ON pos.partner_id = p.id
        GROUP BY 2
        HAVING COUNT(pos.id) + COUNT(so.id) > 1
        """)

        old_customer_ids = [r[1] for r in self._cr.fetchall()]
        return [('id', 'not in' if value else 'in', old_customer_ids)]

    @api.onchange('ward_id')
    def _onchange_ward(self):
        self.update({'district': self.district_id.name_with_type})
        return super(ResPartnerInherit, self)._onchange_ward()

    # format date dd/mm/yyyy
    # @api.depends('birthday')
    # def _compute_format_birthday(self):
    #     for r in self:
    #         if not r.birthday:
    #             r.format_birthday = ''
    #         else:
    #             r.format_birthday = str(r.birthday)[8:10] + '/' + str(r.birthday)[5:7] + '/' + str(r.birthday)[0:4]

    @api.model
    def create_from_ui(self, partner):
        if partner.get('birthday'):
            partner.update({
                'birthday': datetime.strptime(partner.get('birthday'), "%d/%m/%Y")
            })
        if partner.get('district'):
            district_id = self.env['res.country.address'].search([('name', '=ilike', partner.get('district'))], limit=1)
            if district_id:
                partner.update({
                    'district_id': district_id.id
                })
        return super(ResPartnerInherit, self).create_from_ui(partner)

    def _compute_loyalty_point_history(self):
        for rec in self:
            if len(rec.history_points_ids) > 0:
                for r in rec.history_points_ids:
                    if r.order_id:
                        if r.order_id.refunded_orders_count > 0 and r.order_id.amount_total < 0 and r.diem_cong > 0:
                            r.diem_cong = -r.diem_cong

    def _cron_update_create_customer_location(self):
        partner_ids = self.env['res.partner'].sudo().search(
            [('pos_order_count', '>', 0), ('sale_order_count', '>', 0), ('pos_create_customer', '=', False)])
        if len(partner_ids) > 0:
            for partner in partner_ids:
                pos_order = False
                sale_order = False
                if partner.pos_order_count > 0:
                    pos_order = partner.pos_order_ids[-1]
                    # pos_order = partner.sale_order_ids
                if partner.sale_order_count > 0:
                    sale_order = partner.sale_order_ids[-1]
                if pos_order and sale_order:
                    if pos_order.create_date < sale_order.create_date:
                        self._cr.execute(
                            """UPDATE res_partner SET pos_create_customer = %s,s_pos_order_id=%s WHERE id = %s""",
                            (pos_order.config_id.name, pos_order.config_id.id, partner.id))
                    else:
                        self._cr.execute(
                            """UPDATE res_partner SET pos_create_customer = %s WHERE id = %s""",
                            ('POS ecommerce', partner.id))
                elif pos_order:
                    self._cr.execute(
                        """UPDATE res_partner SET pos_create_customer = %s,s_pos_order_id=%s WHERE id = %s""",
                        (pos_order.config_id.name, pos_order.config_id.id, partner.id))
                elif sale_order:
                    self._cr.execute(
                        """UPDATE res_partner SET pos_create_customer = %s WHERE id = %s""",
                        ('POS ecommerce', partner.id))

    @api.depends('s_pos_order_id.name')
    def _compute_pos_create_customer(self):
        for rec in self:
            rec.write({
                'pos_create_customer': rec.s_pos_order_id.name
            })

    # def message_track(self, tracked_fields, initial_values):
    #     try:
    #         if self._name in ['res.partner']:
    #             tracking_fields = []
    #             fields = ['name', 'phone', 'email', 'mobile', 'date_not_buy', 'membership_code', 'gender',
    #                       'birthday', 'customer_ranked', 'is_new_customer', 'check_sync_customer_rank',
    #                       'is_connected_vani', 'month', 'day', 'company_type', 'street', 'ward_id', 'district_id',
    #                       'state_id', 'country_id']
    #             tracking_fields.extend(fields)
    #             for field in tracking_fields:
    #                 if field not in tracked_fields:
    #                     tracked_fields.add(field)
    #                     if self._fields[field].type in ['many2many', 'many2one', 'one2many']:
    #                         for partner_id in self.mapped('id'):
    #                             initial_values[partner_id].update({
    #                                 field: self.browse(partner_id).mapped(field)[0]
    #                             })
    #                     else:
    #                         for partner_id in self.mapped('id'):
    #                             initial_values[partner_id].update({
    #                                 field: self.browse(partner_id).mapped(field)[0]
    #                             })
    #     except Exception as e:
    #         self.env['ir.logging'].sudo().create({
    #             'name': 'Tracking Partner field',
    #             'type': 'server',
    #             'dbname': 'boo',
    #             'level': 'Error',
    #             'path': 'url',
    #             'message': str(e),
    #             'func': 'message_track_partner',
    #             'line': '0',
    #         })
    #
    #     return super(ResPartnerInherit, self).message_track(tracked_fields, initial_values)