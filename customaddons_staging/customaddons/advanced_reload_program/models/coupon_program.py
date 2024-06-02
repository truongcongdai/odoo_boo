from odoo import fields, models, api


class SCouponProgram(models.Model):
    _inherit = 'coupon.program'

    def write(self, vals):
        res = super(SCouponProgram, self).write(vals)
        reward_fields = [
            'valid_product_ids', 'valid_partner_ids', 's_free_products', 's_discount_line_product_ids',
            'rule_partners_domain', 'rule_min_quantity', 'rule_minimum_amount', 'rule_date_to', 'rule_date_from',
            'reward_type', 'reward_product_quantity', 'reward_product_id', 'reward_id', 'promo_code_usage',
            'promo_code', 'promo_barcode', 'promo_applicability', 'program_type', 'maximum_use_number',
            'expiration_date', 'discount_type', 'discount_specific_product_ids', 'discount_percentage',
            'discount_max_amount', 'discount_line_product_id', 'discount_fixed_amount', 'discount_apply_on', 'name', 'rule_products_domain', 'is_expires_ctkm'
        ]
        deny_load_cache = ['is_active_program_cache']
        if any(field in reward_fields for field in vals):
            try:
                if len(self.pos_config_ids) > 0:
                    for pos in self.pos_config_ids:
                        pos.sudo().write({
                            'is_active_program_cache': False,
                        })
                self.env['ir.logging'].sudo().create({
                    'name': 'Refresh Cache Coupon Program',
                    'type': 'server',
                    'dbname': 'OdooBoo',
                    'level': 'INFO',
                    'message': str(vals),
                    'path': 'url',
                    'func': 'write',
                    'line': '0',
                })
            except Exception as e:
                self.env['ir.logging'].sudo().create({
                    'name': 'Refresh Cache Coupon Program',
                    'type': 'server',
                    'dbname': 'OdooBoo',
                    'level': 'ERROR',
                    'message': str(e),
                    'path': 'url',
                    'func': 'write',
                    'line': '0',
                })
        return res
