import ast
import numbers

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval
from datetime import datetime, timedelta, date
from odoo.exceptions import ValidationError
import pytz


class CouponProgram(models.Model):
    _inherit = 'coupon.program'

    description = fields.Char()
    # product_coupon_line_ids = fields.One2many(
    #     comodel_name='s.product.coupon.program',
    #     inverse_name='coupon_id',
    #     help='This is a technical field, for filter record only.'
    # )
    ma_ctkm = fields.Char(
        string='Mã chương trình',
        help="Mã của chương trình khuyến mãi, mục đích để phân biệt các chương trình khuyến mãi khác và đồng bộ CTKM trên Magento (Không phải mã code để áp dụng khuyến mãi)")
    is_expires_ctkm = fields.Boolean(string='Là CTKM hết hạn', compute='_compute_expired_ctkm')
    rule_date_from_onchange = fields.Datetime(string='Ngày bắt đầu')
    rule_date_to_onchange = fields.Datetime(string='Ngày kết thúc')
    is_filter_expires_ctkm = fields.Boolean(string='Là CTKM hết hạn')
    pos_order_ids = fields.Many2many(
        "pos.order", copy=False,
    )
    m2_so_ids = fields.Many2many(
        "sale.order", copy=False, string='Sale Orders'
    )
    name = fields.Char(translate=False)
    free_discount_cheapest_products = fields.Boolean(string='Tặng SP rẻ nhất áp dụng nhiều lần', default=False)
    unremove_ctkm_expired = fields.Boolean(string='Không xóa CTKM khỏi POS khi hết hạn', default=False)
    s_is_program_discard = fields.Boolean(string='DISCARD', default=False)
    s_type_discount = fields.Selection([
        ('chanel', 'Channel'),
        ('crm', 'CRM'),
        ('hr', 'HR')
    ], string='Loại Discount')

    @api.onchange('promo_code_usage')
    def onchange_program_discard(self):
        if self.promo_code_usage == 'no_code_needed':
            self.s_is_program_discard = False

    @api.onchange('rule_date_from_onchange')
    def _onchange_date_from(self):
        user_tz = self.env.user.tz or pytz.utc
        if self.rule_date_from_onchange:
            tz = pytz.utc.localize(self.rule_date_from_onchange).astimezone(pytz.timezone(user_tz))
            str_tz = datetime.strftime(tz, "%Y-%m-%d %H:%M:%S")
            datetime_tz = datetime.strptime(str_tz, '%Y-%m-%d %H:%M:%S')
            if datetime_tz:
                self.update({
                    'rule_date_from': datetime_tz,
                })
        else:
            self.update({
                'rule_date_from': False,
            })

    @api.onchange('rule_date_to_onchange')
    def _onchange_date_to(self):
        user_tz = self.env.user.tz or pytz.utc
        if self.rule_date_to_onchange:
            tz = pytz.utc.localize(self.rule_date_to_onchange).astimezone(pytz.timezone(user_tz))
            str_tz = datetime.strftime(tz, "%Y-%m-%d %H:%M:%S")
            datetime_tz = datetime.strptime(str_tz, '%Y-%m-%d %H:%M:%S')
            if datetime_tz:
                self.update({
                    'rule_date_to': datetime_tz,
                })
        else:
            self.update({
                'rule_date_to': False,
            })

    def _compute_rule_date_coupon_programs(self):
        for rec in self:
            user_tz = self.env.user.tz or pytz.utc
            if rec.rule_date_to_onchange == False and rec.rule_date_from_onchange == False:
                if rec.rule_date_to:
                    tz_date_to = pytz.utc.localize(rec.rule_date_to).astimezone(pytz.timezone(user_tz))
                    str_tz_date_to = datetime.strftime(tz_date_to, "%Y-%m-%d %H:%M:%S")
                    datetime_tz_date_to = datetime.strptime(str_tz_date_to, '%Y-%m-%d %H:%M:%S')
                    rec.update({
                        'rule_date_to_onchange': rec.rule_date_to,
                        'rule_date_to': datetime_tz_date_to,
                    })
                if rec.rule_date_from:
                    tz_date_from = pytz.utc.localize(rec.rule_date_from).astimezone(pytz.timezone(user_tz))
                    str_tz_date_from = datetime.strftime(tz_date_from, "%Y-%m-%d %H:%M:%S")
                    datetime_tz_date_from = datetime.strptime(str_tz_date_from, '%Y-%m-%d %H:%M:%S')
                    rec.update({
                        'rule_date_from_onchange': rec.rule_date_from,
                        'rule_date_from': datetime_tz_date_from,
                    })

    s_free_products = fields.Many2many('product.product', 'free_products_coupon_program_rel',
                                       string='Sản phẩm miễn phí')
    s_is_free_products = fields.Boolean(
        string='Tặng nhiều sản phẩm')
    s_discount_line_product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Sản phẩm dòng phần thưởng')

    # @api.onchange('discount_line_product_ids')
    # def onchange_discount_line_product_ids(self):
    #     for rec in self:
    #         list_free_products = []
    #         for product in rec.s_free_products:
    #             values = {
    #                 'name': _("Free Product - %s", product.name),
    #                 's_free_product_id':product.id,
    #                 'type': 'service',
    #                 'taxes_id': False,
    #                 'supplier_taxes_id': False,
    #                 'sale_ok': False,
    #                 'purchase_ok': False,
    #                 'lst_price': 0,  # Do not set a high value to avoid issue with coupon code
    #             }
    #             discount_line_product_id = self.env['product.product'].create(values)
    #             list_free_products.append(discount_line_product_id.id)
    #         rec.write({'s_discount_line_product_ids': [(6, 0, list_free_products)]})
    # rule_date_from_onchange = fields.Datetime(string='Ngày bắt đầu')
    # rule_date_to_onchange = fields.Datetime(string='Ngày kết thúc')
    #
    # @api.onchange('rule_date_from_onchange')
    # def _onchange_date_from(self):
    #     if self.rule_date_from_onchange:
    #         # self.rule_date_from = self.rule_date_from_onchange + timedelta(hours=7)
    #         date_from = self.rule_date_from_onchange + timedelta(hours=7)
    #         self.update({
    #             'rule_date_from': date_from,
    #         })
    #
    # @api.onchange('rule_date_to_onchange')
    # def _onchange_date_to(self):
    #     if self.rule_date_to_onchange:
    #         # self.rule_date_to = self.rule_date_to_onchange + timedelta(hours=7)
    #         date_to = self.rule_date_to_onchange + timedelta(hours=7)
    #         self.update({
    #             'rule_date_to': date_to,
    #         })

    @api.onchange('rule_date_to', 'rule_date_from')
    def _check_rule_date_from_to(self):
        if any(applicability for applicability in self
               if applicability.rule_date_to and applicability.rule_date_from
                  and applicability.rule_date_to < applicability.rule_date_from):
            raise ValidationError(_('Ngày bắt đầu phải trước ngày kết thúc'))

    @api.depends('rule_date_to', 'expiration_date')
    def _compute_expired_ctkm(self, promo_program_ids=False, coupon_program_ids=False):
        user_tz = self.env.user.tz or pytz.utc
        time_now = fields.Datetime.now()
        datetime_tz = datetime.strptime(
            datetime.strftime(pytz.utc.localize(time_now).astimezone(pytz.timezone(user_tz)), "%Y-%m-%d %H:%M:%S"),
            '%Y-%m-%d %H:%M:%S')
        if not promo_program_ids and not coupon_program_ids:
            for r in self:
                r.sudo().is_expires_ctkm = False
                if r.sudo().program_type != "coupon_program":
                    if r.sudo().rule_date_to != False:
                        if r.sudo().rule_date_to < datetime_tz:
                            r.sudo().is_expires_ctkm = True
                            r.sudo().is_filter_expires_ctkm = True
                        else:
                            r.sudo().is_filter_expires_ctkm = False
                    else:
                        r.sudo().is_filter_expires_ctkm = False
                else:
                    if r.sudo().expiration_date != False:
                        if r.sudo().expiration_date <= date.today():
                            r.sudo().is_expires_ctkm = True
                            r.sudo().is_filter_expires_ctkm = True
                        else:
                            r.sudo().is_filter_expires_ctkm = False
                    else:
                        r.sudo().is_filter_expires_ctkm = False
        if promo_program_ids:
            for r in promo_program_ids:
                r.sudo().is_expires_ctkm = False
                if r.sudo().rule_date_to != False:
                    if r.sudo().rule_date_to < datetime_tz:
                        r.sudo().is_expires_ctkm = True
        if coupon_program_ids:
            for r in coupon_program_ids:
                r.sudo().is_expires_ctkm = False
                if r.sudo().expiration_date != False:
                    if r.sudo().expiration_date < date.today():
                        r.sudo().is_expires_ctkm = True

    @api.model
    def get_default_expiration_date(self):
        today = fields.Date.today()
        expiration_date = today + relativedelta(days=30)
        return expiration_date

    expiration_date = fields.Date('Ngày Hết Hạn', default=get_default_expiration_date)
    count_order_m2_used_coupon = fields.Integer(compute='_compute_count_order_m2_used_coupon')
    count_order_m2_used_coupon_program = fields.Integer(compute='_compute_count_order_m2_used_coupon_program')

    def _compute_order_count(self):
        # Tính lại số lượng đơn hàng sử dụng CTKM
        res = super(CouponProgram, self)._compute_order_count()
        for program in self:
            program.order_count = self.env['sale.order.line'].sudo().search_count([
                ('product_id', '=', program.discount_line_product_id.id), ('is_magento_order', '=', False)])
        return res

    def action_view_sales_orders(self):
        res = super(CouponProgram, self).action_view_sales_orders()
        orders = self.env['sale.order.line'].search([('product_id', '=', self.discount_line_product_id.id),
                                                     ('is_magento_order', '=', False)]).mapped('order_id')
        res['domain'] = [('id', 'in', orders.ids)]
        return res

    # validity_duration
    def _compute_count_order_m2_used_coupon(self):
        # Đếm số lượng đơn M2 sử dụng chương trình khuyến mãi
        for program in self:
            sale_order_magento = []
            sale_order_magento_used_program = 0
            sale_order_magento_ids = self.env['sale.order'].sudo().search([
                '|',
                '|',
                ('s_promo_code', '!=', False),
                ('s_facebook_sender_id', '!=', False),
                ('s_zalo_sender_id', '!=', False),
                ('is_magento_order', '=', True)
            ])
            for sale_order_magento_id in sale_order_magento_ids:
                line_coupon_program_ids = sale_order_magento_id.order_line.mapped('coupon_program_id')
                if (sale_order_magento_id.s_promo_code and program.ma_ctkm in sale_order_magento_id.s_promo_code.split(',')) or program in line_coupon_program_ids:
                    sale_order_magento_used_program += 1
                if sale_order_magento_id.s_promo_code:
                    if program.ma_ctkm in sale_order_magento_id.s_promo_code.split(','):
                        sale_order_magento.append(sale_order_magento_id.id)
            program.count_order_m2_used_coupon = sale_order_magento_used_program
            if len(sale_order_magento):
                self.sudo().m2_so_ids = self.env['sale.order'].sudo().browse(sale_order_magento)

    def _compute_count_order_m2_used_coupon_program(self):
        # Đếm số lượng đơn M2 sử dụng chương trình phiếu giảm giá
        for rec in self:
            count_result = False
            if not isinstance(rec.name, str):
                count_result = self.env['sale.order'].sudo().search_count(
                    [('coupon_code', 'in', rec.coupon_ids.mapped('boo_code'))])
            else:
                coupon_used = self.env['coupon.coupon'].sudo().search([('program_id', '=', rec.id)])
                if len(coupon_used) > 0:
                    coupon_used_id = coupon_used.filtered(
                        lambda r: r.sales_order_id != False and r.sales_order_id.is_magento_order).mapped(
                        'sales_order_id.id')
                    count_result = len(coupon_used_id)
            rec.count_order_m2_used_coupon_program = count_result

    def order_m2_used_coupon_program(self):
        coupon_used_id = False
        coupon_used = self.env['coupon.coupon'].sudo().search([('program_id', '=', self.id)])
        if len(coupon_used) > 0:
            coupon_used_id = coupon_used.filtered(lambda r: r.sales_order_id != False).mapped('sales_order_id.id')
        sale_orders = self.env['sale.order'].sudo().search([('id', 'in', coupon_used_id)])
        return {
            'name': _('Sale Order'),
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sale_orders.ids)],
            'target': 'current',
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    @api.onchange('expiration_date')
    def onchange_validity_duration(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.expiration_date:
                rec.validity_duration = 0
            else:
                if rec.expiration_date > today:
                    rec.validity_duration = (rec.expiration_date - today).days
                else:
                    rec.expiration_date = rec.get_default_expiration_date()
                    raise UserError('Ngày hết hạn phải lớn hơn ngày hiện tại')

    def order_m2_used_coupon(self):
        # Danh sách đơn M2 sử dụng CTKM
        sale_order_magento = []
        sale_order_magento_ids = self.env['sale.order'].sudo().search([
            '|',
            '|',
            ('s_promo_code', '!=', False),
            ('s_facebook_sender_id', '!=', False),
            ('s_zalo_sender_id', '!=', False),
            ('is_magento_order', '=', True)
        ])
        for sale_order_magento_id in sale_order_magento_ids:
            line_coupon_program_ids = sale_order_magento_id.order_line.mapped('coupon_program_id')
            if sale_order_magento_id.s_promo_code:
                if (sale_order_magento_id.s_promo_code and self.ma_ctkm in sale_order_magento_id.s_promo_code.split(',')) or self in line_coupon_program_ids:
                    sale_order_magento.append(sale_order_magento_id.id)
        return {
            'name': _('Sale Order'),
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sale_order_magento)],
            'target': 'current',
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    # @api.model
    # def create(self, vals):
    #     self._set_product_promo(vals)
    #     res = super(CouponProgram, self).create(vals)
    #     return res
    #
    # def write(self, vals):
    #
    #     res = super(CouponProgram, self).write(vals)
    #     if vals.get('rule_products_domain') or vals.get('discount_apply_on') or vals.get(
    #             'discount_specific_product_ids') or 'active' in vals:
    #         self._set_product_promo(vals)
    #     return res

    def _set_product_promo(self, vals):
        s_product_coupon_program = self.env['s.product.coupon.program'].sudo().search(
            [('coupon_id', 'in', self.ids)]).unlink()
        if vals.get('rule_products_domain') or vals.get('discount_apply_on') or vals.get(
                'discount_specific_product_ids') or vals.get('active') == True:
            for rec in self:
                if rec.rule_products_domain and rec.discount_apply_on != 'specific_products':
                    domain = safe_eval(rec.rule_products_domain)
                    product_ids = self.env['product.product'].sudo().search(domain)
                else:
                    product_ids = rec.discount_specific_product_ids
                for product in product_ids:
                    product.coupon_ids = [(0, 0, {'coupon_id': rec.id, 'product_id': product.id})]

    @api.model
    def create(self, vals):
        vals['ma_ctkm'] = self.env['ir.sequence'].next_by_code('coupon.program')
        res = super(CouponProgram, self).create(vals)
        if not vals.get('discount_line_product_ids', False) and res.s_is_free_products:
            list_free_products = []
            for product in res.s_free_products:
                values = {
                    'name': _("Free Product - %s",
                              product.default_code if product.default_code else product.display_name),
                    'type': 'service',
                    's_free_product_id': product.id,
                    'taxes_id': False,
                    'supplier_taxes_id': False,
                    'sale_ok': False,
                    'purchase_ok': False,
                    'lst_price': 0,  # Do not set a high value to avoid issue with coupon code
                }
                product_free_id = self.env['product.product'].search([('s_free_product_id', '=', product.id)], limit=1)
                if not product_free_id:
                    discount_line_product_id = self.env['product.product'].sudo().create(values)
                else:
                    discount_line_product_id = product_free_id
                list_free_products.append(discount_line_product_id.id)
            res.write({'s_discount_line_product_ids': [(6, 0, list_free_products)]})
        return res

    def write(self, vals):
        res = super(CouponProgram, self).write(vals)
        reward_fields = [
            'reward_type', 'reward_product_id', 'discount_type', 'discount_percentage',
            'discount_apply_on', 'discount_specific_product_ids', 'discount_fixed_amount', 's_free_products',
            's_is_free_products'
        ]
        if any(field in reward_fields for field in vals):
            if self.s_is_free_products:
                if len(self.s_free_products) > 0:
                    list_discount_line_product = []
                    for product in self.s_free_products:
                        product_free_id = self.env['product.product'].sudo().search(
                            [('s_free_product_id', '=', product.id)],
                            limit=1)
                        if len(product_free_id) > 0:
                            product_free_id.sudo().write({
                                'name': _("Free Product - %s",
                                          product.default_code if product.default_code else product.display_name),
                                's_free_product_id': product.id,
                            })
                            list_discount_line_product.append(product_free_id.id)
                        else:
                            discount_line_product_id = self.env['product.product'].sudo().create({
                                'name': _("Free Product - %s", product.default_code),
                                'type': 'service',
                                's_free_product_id': product.id,
                                'taxes_id': False,
                                'supplier_taxes_id': False,
                                'sale_ok': False,
                                'purchase_ok': False,
                                'lst_price': 0,  # Do not set a high value to avoid issue with coupon code
                            })
                            if discount_line_product_id:
                                list_discount_line_product.append(discount_line_product_id.id)
                    if len(list_discount_line_product) > 0:
                        self.write({'s_discount_line_product_ids': [(6, 0, list_discount_line_product)]})
            else:
                self.mapped('discount_line_product_id').write({'name': self[0].reward_id.display_name})
                self.mapped('discount_line_product_id').write({'is_gift_free_product': True})
        return res

    @api.depends("rule_partners_domain")
    def get_program_for_partner(self, customer_id):
        for rec in self:
            programs = rec.env['coupon.program'].sudo().search([('id', '=', rec.id)])
            if programs:
                for program in programs:
                    domain = ast.literal_eval(program.rule_partners_domain) if program.rule_partners_domain else []
                    if domain:
                        domain.append(['id', '=', customer_id])
                    valid_partner_ids = self.env["res.partner"].sudo().search(domain)
                    if customer_id in valid_partner_ids.ids:
                        return True
                    else:
                        return False

    # @api.depends('s_free_products')
    # def _compute_s_free_products(self):
    #     for rec in self:
    #         if rec.s_is_free_products:
    #             list_free_products = []
    #             for product in rec.s_free_products:
    #                 values = {
    #                     'name': _("Free Product - %s", product.name),
    #                     'type': 'service',
    #                     's_free_product_id': product.id,
    #                     'taxes_id': False,
    #                     'supplier_taxes_id': False,
    #                     'sale_ok': False,
    #                     'purchase_ok': False,
    #                     'lst_price': 0,  # Do not set a high value to avoid issue with coupon code
    #                     'is_gift_product': True
    #                 }
    #                 product_free_id = self.env['product.product'].search([('s_free_product_id', '=', product.id)], limit=1)
    #                 if not product_free_id:
    #                     discount_line_product_id = self.env['product.product'].create(values)
    #                 else:
    #                     if not product_free_id.is_gift_product:
    #                         product_free_id.is_gift_product = True
    #                     discount_line_product_id = product_free_id
    #                 list_free_products.append(discount_line_product_id.id)
    #             rec.write({'s_discount_line_product_ids': [(6, 0, list_free_products)]})

    def _compute_remove_coupon_prgrams(self):
        for rec in self:
            remove_order_ids = []
            if len(rec.pos_order_ids) > 0:
                if len(rec.pos_order_line_ids) > 0:
                    order_ids = rec.pos_order_ids.filtered(lambda l: l.id not in rec.pos_order_line_ids.mapped('order_id').ids)
                    if order_ids:
                        remove_order_ids = order_ids.ids
                else:
                    remove_order_ids = rec.pos_order_ids.ids
            if len(remove_order_ids) > 0:
                rec.write({
                    'pos_order_ids': [(3, order) for order in remove_order_ids]
                })
                self.env['ir.logging'].sudo().create({
                    'name': '_compute_remove_coupon_prgrams',
                    'type': 'server',
                    'dbname': 'boo',
                    'level': 'INFO',
                    'message': str(remove_order_ids),
                    'path': 'url',
                    'func': '_compute_remove_coupon_prgrams',
                    'line': '0',
                })

    def compute_count_coupon_program_pos_order(self):
        order_error = self.env['pos.order'].sudo().search([('lines.program_id', '!=', False), ('applied_program_ids', '=', False)])
        if len(order_error) > 0:
            for order_id in order_error:
                program_id = order_id.lines.filtered(lambda l: l.program_id).mapped('program_id')
                order_id.sudo().write({
                    'applied_program_ids': program_id
                })

    def compute_pos_order_lost_coupon_program(self):
        orders = self.env['pos.order'].sudo().search(
            [('lines.product_id.from_coupon_program', '!=', False), ('applied_program_ids', '=', False),
             ('lines.program_id', '=', False)])
        if len(orders) > 0:
            for order in orders:
                order_lines = order.lines.filtered(lambda l: l.is_product_service and not l.program_id)
                for line in order_lines:
                    if line.product_id.from_coupon_program.id:
                        self._cr.execute("""
                            INSERT INTO coupon_program_pos_order_rel (pos_order_id, coupon_program_id)
                            VALUES (%s, %s);
                        """, (order.id, line.product_id.from_coupon_program.id,))
                        self._cr.execute("""
                            UPDATE pos_order_line
                            SET program_id = %s
                            WHERE id = %s
                        """, (line.product_id.from_coupon_program.id, line.id,))

    # def _get_discount_product_values(self):
    #     if self.s_is_free_products:
    #         return {
    #             'name': _("Free Product - %s", self.ma_ctkm),
    #             'type': 'service',
    #             'taxes_id': False,
    #             'supplier_taxes_id': False,
    #             'sale_ok': False,
    #             'purchase_ok': False,
    #             'lst_price': 0,  # Do not set a high value to avoid issue with coupon code
    #         }
    #     else:
    #         return {
    #             'name': self.reward_id.display_name,
    #             'type': 'service',
    #             'taxes_id': False,
    #             'supplier_taxes_id': False,
    #             'sale_ok': False,
    #             'purchase_ok': False,
    #             'lst_price': 0,  # Do not set a high value to avoid issue with coupon code
    #         }
