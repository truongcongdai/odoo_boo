from odoo import fields, models, api, tools
import os
from odoo.modules.module import get_module_resource
import base64
import logging
_logger = logging.getLogger(__name__)


class ModelName(models.TransientModel):
    _name = 'setu.rfm.configuration'
    _description = 'Setu RFM Configuration'

    install_setu_rfm_analysis_extended = fields.Boolean(string="Enable PoS Sales")
    install_image = fields.Binary(
        string='Installation Image',
        default=lambda s: s._default_install_image()
    )

    @api.model
    def _default_install_image(self):
        image_path = get_module_resource(
            'setu_rfm_analysis', 'static/src', 'install_pos_config2.png'
        )
        with open(image_path, 'rb') as handler:
            image_data = handler.read()
        return base64.encodebytes(image_data)

    @api.model
    def default_get(self, fields):
        res = super(ModelName, self).default_get(fields)
        install_setu_rfm_analysis = self.env['ir.config_parameter'].sudo().get_param(
            'setu_rfm_analysis.install_setu_rfm_analysis_extended')
        if install_setu_rfm_analysis:
            res['install_setu_rfm_analysis_extended'] = True if install_setu_rfm_analysis == 'installed' else False
        return res

    def execute(self):
        install_setu_rfm_analysis = self.sudo().env.ref('setu_rfm_analysis.install_setu_rfm_analysis_extended')
        self.unzip_and_install_extended_module(True, install_setu_rfm_analysis)
        self.env['ir.config_parameter'].set_param('setu_rfm_analysis.extended_module_in_registry', True)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def unzip_and_install_extended_module(self, state, install_setu_rfm_analysis):
        try:
            extended_rfm_analysis = self.env['ir.module.module'].sudo().search(
                [('name', '=', 'setu_rfm_analysis_extended')],
                limit=1)
            status = ''
            source_dir = __file__.replace('/wizard/setu_rfm_configuration.py',
                                          '/module/setu_rfm_analysis_extended.zip')
            target_dir = __file__.split('/setu_rfm_analysis/wizard/setu_rfm_configuration.py')[0]
            if not state and extended_rfm_analysis and extended_rfm_analysis.state == 'installed':
                status = 'uninstall'
            if state:
                if extended_rfm_analysis and extended_rfm_analysis.state != 'installed':
                    status = 'install'
                elif not extended_rfm_analysis:
                    import zipfile
                    with zipfile.ZipFile(source_dir, 'r') as zip_ref:
                        zip_ref.extractall(target_dir)
                    self.env['ir.module.module'].sudo().update_list_setu_rfm_analysis()
            return True
        except Exception as e:
            _logger.info("====================%s==================" % e)
            return False
