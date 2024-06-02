from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class CouponCouponInherit(models.Model):
    _inherit = 'coupon.coupon'
    _rec_name = 'boo_code'

    @api.model
    def _generate_boo_code(self):
        return str(uuid4())[:22]

    boo_code = fields.Char(default=lambda self: self._generate_code())
    code = fields.Char(readonly=False)
    expiration_date = fields.Date(readonly=False)
    s_order_reference = fields.Char(string='Mã đơn hàng', compute='_computed_order_reference' )

    @api.constrains('boo_code')
    def _check_code_import(self):
        if self.boo_code:
            if self.expiration_date:
                if self.expiration_date > fields.Date.today():
                    coupon = self.env['coupon.coupon'].search([('boo_code', '=', self.boo_code),
                                                               ('state', '!=', ('used', 'expired', 'cancel'))])
                    if len(coupon) > 1:
                        raise ValidationError(_(f'{self.boo_code} Coupon code already exists!'))
                else:
                    raise ValidationError(_(f'{self.boo_code} Coupon is not used!'))
        else:
            raise ValidationError(_(f'{self.boo_code} Coupon code is empty!'))

    def _check_coupon_code(self, order_date, partner_id, **kwargs):
        self.ensure_one()
        check_login = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_magento.is_boo_code_coupon','False')
        if check_login != 'True':
            coupon_check_code = self.code
        else:
            coupon_check_code = self.boo_code
            message = {}
            if self.state == 'used':
                message = {'error': _('This coupon has already been used (%s).') % (coupon_check_code)}
            elif self.state == 'reserved':
                message = {'error': _('This coupon %s exists but the origin sales order is not validated yet.') % (coupon_check_code)}
            elif self.state == 'cancel':
                message = {'error': _('This coupon has been cancelled (%s).') % (coupon_check_code)}
            elif self.state == 'expired' or (self.expiration_date and self.expiration_date < order_date):
                message = {'error': _('This coupon is expired (%s).') % (coupon_check_code)}
            elif not self.program_id.active:
                message = {'error': _('The coupon program for %s is in draft or closed state') % (coupon_check_code)}
            elif self.partner_id and self.partner_id.id != partner_id:
                message = {'error': _('Invalid partner.')}
            return message

    @api.depends('pos_order_id')
    def _computed_order_reference(self):
        for rec in self:
            if rec.pos_order_id:
                rec.s_order_reference = rec.pos_order_id.pos_reference
            elif rec.sales_order_id:
                rec.s_order_reference = rec.sales_order_id.name
            else:
                rec.s_order_reference = ''

    def _compute_expiration_date(self):
        res = super(CouponCouponInherit, self)._compute_expiration_date()
        for coupon in self.filtered(lambda x: x.program_id.validity_duration > 0):
            if coupon.boo_code and coupon.state not in ['used', 'cancel'] and coupon.program_id.program_type == 'coupon_program':
                coupon.expiration_date = coupon.program_id.expiration_date
                if coupon.state == 'expired' and coupon.expiration_date > fields.Date.today():
                    coupon.write({
                        'state': 'new'
                    })
            elif coupon.boo_code and coupon.state not in ['used', 'cancel'] and coupon.program_id.program_type == 'promotion_program':
                coupon.expiration_date = (coupon.create_date + relativedelta(days=coupon.program_id.validity_duration)).date()
                if coupon.expiration_date < fields.Date.today():
                    coupon.sudo().write({
                        'state': 'expired'
                    })
                elif coupon.state == 'expired' and coupon.expiration_date > fields.Date.today():
                    coupon.sudo().write({
                        'state': 'new'
                    })
            else:
                coupon.expiration_date = (coupon.create_date + relativedelta(days=coupon.program_id.validity_duration)).date()
        return res

    def write(self, vals):
        ###Khi remove coupon khỏi pos -> core sẽ cho write state lại thành new
        ###Thêm điều kiện nếu coupon đã được sử dụng và có pos_order_id -> không update state thành new
        if 'state' in vals:
            for rec in self:
                if vals.get('state') == 'new':
                    if rec.state == 'used' and rec.pos_order_id:
                        if not rec.pos_order_id.is_cancel_order:
                            vals.update({'state': 'used'})
        res = super(CouponCouponInherit, self).write(vals)
        return res

    def cron_expire_coupon(self):
        self._cr.execute("""
            SELECT C.id FROM COUPON_COUPON as C
            INNER JOIN COUPON_PROGRAM as P ON C.program_id = P.id
            WHERE C.STATE in ('reserved', 'new', 'sent')
                AND P.validity_duration > 0
                AND P.expiration_date < now()""")

        expired_ids = [res[0] for res in self._cr.fetchall()]
        self.browse(expired_ids).write({'state': 'expired'})

    def check_coupon_is_used(self):
        ###Check xem coupon đã được sử dụng hay chưa
        if self.state == 'used' or len(self.pos_order_id) > 0:
            return False, str(self.boo_code)
        return True, str(self.boo_code)
