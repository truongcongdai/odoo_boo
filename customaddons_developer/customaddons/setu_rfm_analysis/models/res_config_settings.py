# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.api import Environment
import os
from odoo.models import ValidationError
import logging

_logger = logging.getLogger(__name__)
import odoo

ADMIN_USER_ID = odoo.SUPERUSER_ID
from contextlib import contextmanager


class Groups(models.Model):
    """ Update of res.groups class
        - if adding users from a group, check mail.channels linked to this user
          group and subscribe them. This is done by overriding the write method.
    """
    _inherit = 'res.groups'

    def write(self, vals, context=None):
        enable_sales = self.env.ref('setu_rfm_analysis.group_sales_team_rfm').id
        dynamic_rules = self.env.ref('setu_rfm_analysis.group_dynamic_rules').id
        gp_to_append = self.env.ref('setu_rfm_analysis.group_rfm_show_team_conf').id
        has_enable_sales_group = self.env.user.has_group('setu_rfm_analysis.group_sales_team_rfm')
        has_dynamic_rules_group = self.env.user.has_group('setu_rfm_analysis.group_dynamic_rules')
        grp_user = self.env.ref('base.group_user')
        if 'implied_ids' in vals:
            if vals['implied_ids'][0][1] == enable_sales and has_dynamic_rules_group:
                vals['implied_ids'].append((vals['implied_ids'][0][0], gp_to_append))
            if vals['implied_ids'][0][1] == dynamic_rules and has_enable_sales_group:
                vals['implied_ids'].append((vals['implied_ids'][0][0], gp_to_append))
            if vals['implied_ids'][0][0] == 3:
                self.env.ref('setu_rfm_analysis.group_rfm_show_team_conf').write(
                    {'users': [(3, user.id) for user in grp_user.users]})

        write_res = super(Groups, self).write(vals)

        return write_res


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # past_x_days_sales = fields.Integer("Use X days sales history in RFM Segmentation")
    group_dynamic_rules = fields.Boolean(implied_group='setu_rfm_analysis.group_dynamic_rules',
                                         string="Enable Dynamic Rules")
    group_sales_team_rfm = fields.Boolean(implied_group='setu_rfm_analysis.group_sales_team_rfm',
                                          string="Enable Sales Team Segments")
    module_setu_rfm_analysis_extended = fields.Boolean(string="Install PoS Sales")
    extended_module_in_registry = fields.Boolean(string='Extended Module in Registry', config_parameter="setu_rfm_analysis.extended_module_in_registry")

    def open_actions_setu_rfm_configuration(self):
        point_of_sale = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'point_of_sale')],
            limit=1)
        if point_of_sale.state != 'installed':
            raise ValidationError(_('In order to use this feature please install Point of Sale app first and try to '
                                    'activate this.'))
        action_values = self.sudo().env.ref('setu_rfm_analysis.actions_setu_rfm_configuration').sudo().read()[0]
        return action_values

    # @api.model
    # def set_values(self):
    #     self.env['ir.config_parameter'].sudo().set_param('setu_rfm_analysis.install_setu_rfm_analysis_extended',
    #                                                      self.install_setu_rfm_analysis_extended)
    #     return super(ResConfigSettings, self).set_values()
