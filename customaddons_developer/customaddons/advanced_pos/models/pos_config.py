from odoo import fields, models, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError
from datetime import datetime
class PosConfig(models.Model):
    _inherit = 'pos.config'

    diem_khong_lay_bill = fields.Integer(string='Số điểm không lấy bill')
    iface_print_auto = fields.Boolean(string='Automatic Receipt Printing', default=True,
                                      help='The receipt will automatically be printed at the end of each order.')
    code = fields.Char()
    s_pos_adress = fields.Char(string='Địa chỉ')
    s_pos_phone_number = fields.Char(string='Số điện thoại')
    s_set_bill = fields.Boolean(string='Không lấy bill', default=False)
    warehouse_id_related = fields.Many2one('stock.warehouse', related='picking_type_id.warehouse_id', store=True)
    limited_price_list_amount = fields.Integer(default=20000)
    price_list_load_background = fields.Boolean()
    coupon_program_load_background = fields.Boolean()
    coupon_pricelist_item_load_background = fields.Boolean(default=True)
    limited_coupon_program_amount = fields.Integer(default=20000)
    s_apply_discout_percent = fields.Boolean(string='Cho phép chiết khấu % nhiều dòng')
    is_first_partner = fields.Boolean(string='Cho phép chọn khách hàng vị trí đầu tiên')
    first_partner = fields.Many2one('res.partner', string='Chọn khách hàng được hiện đầu tiên trong POS')
    first_partner_phone = fields.Char(related='first_partner.phone', string='Số điện thoại khách hàng hiện đầu tiên trong POS')
    is_create_customer_control = fields.Boolean(string='Kiểm soát tạo khách hàng')
    s_image_footer = fields.Binary(string='Ảnh chân trang', attachment=True)
    s_image_footer_name = fields.Char(string='Tên ảnh chân trang')

    @api.constrains('code')
    def unique_name(self):
        self.ensure_one()
        if self.code:
            if self.env['pos.config'].search_count([('code', '=', self.code)]) > 1:
                raise ValidationError('Mỗi cửa hàng chỉ có một mã(code) duy nhất và không được trùng nhau.'
                                      'Vui lòng đặt mã (code) khác.')
    ### Chỉ cần check trùng phone ở contact
    # @api.constrains('s_pos_phone_number')
    # def constrains_s_pos_phone_number(self):
    #     if self.s_pos_phone_number:
    #         phone = self.env['pos.config'].search([('s_pos_phone_number', '=', self.s_pos_phone_number)])
    #         if len(phone) > 1:
    #             raise ValidationError(_('Số điện thoại này đã tồn tại ở một điểm bán hàng khác.'
    #                                     '\nVui lòng kiểm tra lại.'))
    def copy(self, default=None):
        default = dict(default or {})
        default['iface_print_auto'] = True
        return super(PosConfig, self).copy(default)

    @api.model
    def create(self, values):
        values['iface_print_auto'] = True
        return super(PosConfig, self).create(values)

    def _set_tab_khuyen_mai(self, promo_ids):
        self._cr.execute("""DELETE FROM s_product_coupon_program WHERE coupon_id = %s""" % (self.id,))
        self._cr.execute("""DELETE FROM s_product_coupon_program WHERE id not in (SELECT s_product_coupon_program_id FROM pos_config_s_product_coupon_program_rel)""")

        for promo in promo_ids:
            if promo:
                if promo.discount_apply_on == 'specific_products':
                    product_ids = promo.discount_specific_product_ids
                else:
                    domain = promo.rule_products_domain
                    domain_query = ''
                    for domain_db in safe_eval(domain):
                        if len(domain_db) == 3:
                            for r in domain_db:
                                domain_query += str(r)
                            if domain_query:
                                domain_query += ' and '
                    domain_query = domain_query.rstrip(' and ')
                    if domain_query:
                        self._cr.execute("""SELECT * FROM product_product WHERE product_tmpl_id in 
                        (SELECT id FROM product_template WHERE %s)""" % (domain_query,))
                    else:
                        self._cr.execute("""SELECT * FROM product_product)""")
                    product_ids = self.env.cr.dictfetchall()
                for product in product_ids:
                    if product.get('id'):
                        self._cr.execute("""SELECT id FROM s_product_coupon_program WHERE product_id = %s""" % (product.get('id'),))
                        query_product_coupon_program_ids = self.env.cr.fetchall()
                        for promo_id in query_product_coupon_program_ids:
                            if promo.id not in promo_id:
                                self.env['s.product.coupon.program'].sudo().create({
                                    'coupon_id': promo.id,
                                    'product_id': product.get('id')
                                })

    # def _set_programs(self):
    #     res = super(PosConfig, self)._set_programs()
    #     # self._set_tab_khuyen_mai(self.promo_program_ids)
    #     return res

    def use_coupon_code(self, code, creation_date, partner_id, reserved_program_ids):
        check_login = self.env['ir.config_parameter'].sudo().get_param('advanced_integrate_magento.is_boo_code_coupon','False')
        if check_login != 'True':
            coupon_to_check = self.env["coupon.coupon"].search(
                [("code", "=", code), ("program_id", "in", self.program_ids.ids)])
        else:
            coupon_to_check = self.env["coupon.coupon"].search(
                [("boo_code", "=", code), ("program_id", "in", self.program_ids.ids)])
        if not coupon_to_check:
            return {
                "successful": False,
                "payload": {
                    "error_message": _("This coupon is invalid (%s).") % (code)
                },
            }
        for record in coupon_to_check.filtered(lambda code: code.state):
            coupon_to_check = coupon_to_check.filtered(lambda code: code.state == "new")
            if len(coupon_to_check) > 0:
                coupon_to_check = coupon_to_check[0]
            else:
                coupon_to_check = record
        message = coupon_to_check._check_coupon_code(
            fields.Date.from_string(creation_date[:11]),
            partner_id,reserved_program_ids=reserved_program_ids,)
        error_message = message.get("error", False)
        print(coupon_to_check)
        print(error_message)
        if error_message:
            return {
                "successful": False,
                "payload": {"error_message": error_message},
            }
        # coupon_to_check.sudo().write({"state": "used"})
        return {
            "successful": True,
            "payload": {
                "program_id": coupon_to_check.program_id.id,
                "coupon_id": coupon_to_check.id,
            },
        }

    def get_limited_partners_loading(self):
        self.env.cr.execute("""
            WITH pm AS
            (
                     SELECT   partner_id,
                              Count(partner_id) order_count
                     FROM     pos_order
                     GROUP BY partner_id)
            SELECT    id
            FROM      res_partner AS partner
            LEFT JOIN pm
            ON        (
                                partner.id = pm.partner_id)
            WHERE     partner.active=TRUE
            ORDER BY  COALESCE(pm.order_count, 0) DESC,
                      NAME limit %s;
        """, [str(self.limited_partners_amount)])
        result = self.env.cr.fetchall()
        return result

    def _cron_remove_program_expired(self):
        pos_config_ids = self.env['pos.config'].sudo().search([])
        for rec in pos_config_ids:
            if rec.use_coupon_programs == True:
                rec.promo_program_ids._compute_expired_ctkm(rec.promo_program_ids, rec.coupon_program_ids)
                promo_expired = rec.promo_program_ids.filtered(lambda r: r.is_expires_ctkm == True)
                if len(promo_expired) > 0:
                    for promo in promo_expired:
                        if promo.unremove_ctkm_expired != True:
                            rec.write({
                                'promo_program_ids': [(3, promo.id)]
                            })
                coupon_pro_expired = rec.coupon_program_ids.filtered(lambda c: c.is_expires_ctkm == True)
                if len(coupon_pro_expired) > 0:
                    for coupon_pro in coupon_pro_expired:
                        rec.write({
                            'coupon_program_ids': [(3, coupon_pro.id)]
                        })
