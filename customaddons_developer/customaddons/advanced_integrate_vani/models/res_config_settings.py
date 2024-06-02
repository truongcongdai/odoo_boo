from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    vani_api_key = fields.Char(
        string='API Key',
        config_parameter='vani.api.key'
    )
    vani_membership_id = fields.Char(
        string='Membership ID',
        config_parameter='vani.membership.id'
    )
    vani_brand_id = fields.Char(
        string='Brand ID',
        config_parameter='vani.brand.id'
    )
    vani_api_url = fields.Char(
        string='API URL',
        config_parameter='vani.api.url'
    )
    vani_point_api_url = fields.Char(
        string='POINT API URL',
        config_parameter='vani.point.api.url'
    )
