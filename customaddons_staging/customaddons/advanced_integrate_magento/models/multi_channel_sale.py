from odoo import _, api, fields, models
from odoo.addons.magento2x_odoo_bridge.tools.magento_api import Magento2
from ..tools.api_wrapper import _create_log
import logging
import json
from urllib.parse import urljoin

_logger = logging.getLogger(__name__)


class MultiChannelSale(models.Model):
    _inherit = ['multi.channel.sale']

    long_life_token = fields.Char(
        string='Long-Life Token',
        help='For multiple times API calling, short-lives token is a waste of time and resource'
    )

    # def export_magento2x(self, exp_obj, **kwargs):
        # if exp_obj._name == 'product.template':
        #     for channel in self:
        #         channel.export_magento2x_categories()
        #         channel.export_magento2x_attributes()
        # res = super(MultiChannelSale, self).export_magento2x(exp_obj, **kwargs)
        # return res

    def set_info_urls(self):
        super(MultiChannelSale, self).set_info_urls()
        for rec in self:
            rec.blog_url = rec.store_url = ''

    @api.model
    def get_magento2x_sdk(self):
        if self.long_life_token:
            message = _('Long-live token is your input, use it with your own risk!')
            sdk = None
            try:
                debug = self.debug == 'enable'
                sdk = Magento2(
                    username=self.email,
                    password=self.api_key,
                    base_uri=self.url,
                    oauth_token=self.long_life_token,
                    store_code=str(self.store_code),
                    debug=debug
                )
            except Exception as e:
                message += '<br/>%s' % e.args
            return dict(
                sdk=sdk,
                message=message,
            )
        return super(MultiChannelSale, self).get_magento2x_sdk()

    def get_long_life_token(self):
        self.ensure_one()
        if self.channel != 'magento2x':
            return
        long_life_token = self.env['ir.config_parameter'].get_param('magento.m2_long_live_token', '')
        if long_life_token:
            self.long_life_token = long_life_token
            return self.test_connection()

    def clean_long_life_token(self):
        if not self.long_life_token:
            return
        self.long_life_token = False
        return self.set_to_draft()

    def cron_post_product_attributes_m2(self):
        records = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        records.export_magento2x_attributes()
        magento_attributes_set = records.default_product_set_id
        if len(magento_attributes_set.attribute_ids) > 0:
            for attribute in magento_attributes_set.attribute_ids:
                attribute.magento_assign_to_attribute_set(magento_attributes_set.store_id)
