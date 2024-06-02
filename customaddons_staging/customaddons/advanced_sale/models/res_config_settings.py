from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_advanced_integrate_magento = fields.Boolean(
        string='Advanced Integrate Magento'
    )
