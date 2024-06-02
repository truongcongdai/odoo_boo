from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import json
from odoo.tools import date_utils


class PosConfigInherit(models.Model):
    _inherit = 'pos.config'

    s_coupon_domain = fields.Char(string="Coupon program domain")
    s_promo_domain = fields.Char(string="Promotion program domain")
    program_fields = fields.Text('Program cache')
    is_active_program_cache = fields.Boolean(
        string='Đã lưu Cache CTKM', compute="check_active_program_cache", store=True)
    enable_program_cache = fields.Boolean(
        string='Bật chức năng lưu Cache CTKM',default=False)

    # cache_ids = fields.One2many('pos.cache', 'config_id')
    def cron_refresh_cache_programs(self):
        pos_config = self.env['pos.config'].sudo().search([('enable_program_cache', '=', True),('is_active_program_cache', '=', False)])
        if len(pos_config) > 0:
            pos_config.s_action_load_coupon_program()

    def s_action_load_coupon_program(self, programs=None):
        for rec in self:
            try:
                if not programs:
                    programs = self.env['coupon.program'].sudo().search_read([('id', 'in', rec.program_ids.ids)])
                if programs:
                    program_cache = self.env['s.pos.cache'].sudo().search([('config_id', '=', rec.id)])
                    if program_cache:
                        program_cache.sudo().write({
                            'program_fields': json.dumps(programs, default=date_utils.json_default).encode('utf-8'),
                        })
                    else:
                        program_cache = self.env['s.pos.cache'].sudo().create({
                            'program_fields': json.dumps(programs, default=date_utils.json_default).encode('utf-8'),
                            'config_id': rec.id,
                        })
                    if program_cache:
                        rec.sudo().write({
                            'is_active_program_cache': True,
                        })
                else:
                    return []
            except Exception as e:
                self.env['ir.logging'].sudo().create({
                    'type': 'server',
                    'name': 's_action_load_coupon_program',
                    'path': 'path',
                    'line': 'line',
                    'func': 's_action_load_coupon_program',
                    'message': str(e)
                })

    @api.depends('promo_program_ids', 'coupon_program_ids','enable_program_cache')
    def check_active_program_cache(self):
        for rec in self:
            if rec.is_active_program_cache:
                rec.sudo().write({
                    'is_active_program_cache': False
                })

    def get_program_cache(self):
        for rec in self:
            program_cache = self.env['s.pos.cache'].sudo().search([('config_id', '=', rec.id)], limit=1)
            if program_cache.program_fields:
                return program_cache.program_fields
            return []

    def s_set_domain_program(self):
        view_id = self.env.ref('advanced_reload_program.action_set_pos_program_form').id
        program_ids = []
        coupon_ids = []
        if self.s_promo_domain:
            promo_domain_dict = json.loads(self.s_promo_domain.replace("'", '"'))
            promo_domain = safe_eval(str(promo_domain_dict['domain']))
            program_ids = self.env['coupon.program'].sudo().search(promo_domain).ids
        if self.s_coupon_domain:
            coupon_domain_dict = json.loads(self.s_coupon_domain.replace("'", '"'))
            coupon_domain = safe_eval(str(coupon_domain_dict['domain']))
            coupon_ids = self.env['coupon.program'].sudo().search(coupon_domain).ids
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'action.set.pos.program',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_pos_config_id': self.id,
                'default_program_ids': [(6, 0, program_ids)],
                'default_coupon_ids': [(6, 0, coupon_ids)],
            }
        }
