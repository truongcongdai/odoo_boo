from uuid import uuid4
from odoo import _, fields, models, api
from odoo.exceptions import ValidationError

from ..tools.api_wrapper import _create_log


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    url_integrate_magento = fields.Char(
        string='Url', config_parameter='magento.url')
    user_integrate_magento = fields.Char(
        string='Tài khoản', config_parameter='magento.user')
    password_integrate_magento = fields.Char(
        string='Mật khẩu', config_parameter='magento.password')
    is_connected = fields.Boolean(
        string='Đã kết nối', default=False, config_parameter='magento.is_connected')
    token_for_integrate = fields.Char(
        string='Connect Token',
        readonly=True,
        config_parameter='integrate.token_for_integrate'
    )
    magento_long_live_token = fields.Char(
        string='M2 Long-live Token',
        config_parameter='magento.m2_long_live_token'
    )
    is_boo_code_coupon = fields.Boolean('Push Notifications', config_parameter='advanced_integrate_magento.is_boo_code_coupon', default=True)

    def generate_token_for_integrate(self):
        self.ensure_one()
        if self.env['ir.config_parameter'].sudo().get_param('integrate.token_for_integrate'):
            return
        token = str(uuid4())
        self.env['ir.config_parameter'].sudo().set_param('integrate.token_for_integrate', token)

    def clear_token_for_integrate(self):
        token_for_integrate = self.env['ir.config_parameter'].search(
            [('key', '=', 'integrate.token_for_integrate')]
        )
        if token_for_integrate:
            token_for_integrate.unlink()

    # connect magento dong thoi sync san pham (chi sync sp mot lan duy nhat)
    def connect_magento(self):
        # for rec in self.filtered(lambda config: not config.is_connected):
        #     rec.export_product_magento()
        self.env['ir.config_parameter'].sudo().set_param('magento.is_connected', True)

    def disconnect_magento(self):
        self.env['ir.config_parameter'].sudo().set_param('magento.is_connected', False)

    @api.model
    def _update_magento_sale_channel(self, magento_sale_channel):
        magento_sale_channel.write({
            'url': self.url_integrate_magento,
            'email': self.user_integrate_magento,
            'api_key': self.password_integrate_magento,
            'environment': 'production',
            'active': True,
            'debug': 'disable'
        })
        if magento_sale_channel.state != 'validate':
            magento_sale_channel.test_connection()

    @api.model
    def _check_magento_sale_channel_default_product_attribute_set(self, magento_sale_channel, products):
        if not magento_sale_channel.default_product_set_id and products.attribute_line_ids.attribute_id:
            try:
                import_attributes = self.env['import.operation'].sudo().create({
                    'channel_id': magento_sale_channel.id,
                    'operation': 'import',
                    'object': 'product.attribute'
                })
                import_attributes.import_button()
                magento_sale_channel.set_to_draft()
                self.env.cr.commit()
                raise ValidationError(_('Please set a default attribute set into your Magento Odoo Bridge!'))
            except Exception as e:
                # _create_log(name='M2_import_action_fails', message=e.args,
                #             func='_check_magento_sale_channel_default_product_attribute_set')
                self.env.cr.rollback()
                raise ValidationError(e.args)
        if magento_sale_channel.default_product_set_id and products.attribute_line_ids.attribute_id:
            return magento_sale_channel.default_product_set_id.write({
                'attribute_ids': [(6, 0, products.attribute_line_ids.attribute_id.ids)]
            })

    def export_product_magento(self):
        self.ensure_one()
        if self.env['ir.config_parameter'].sudo().get_param('magento.is_connected'):
            return
        magento_sale_channel = self.env.ref('magento2x_odoo_bridge.magento2x_channel', raise_if_not_found=False)
        if not magento_sale_channel:
            raise ValidationError(_('Magento Odoo Bridge does not exist, pls contact your Administrator!'))
        self._update_magento_sale_channel(magento_sale_channel)
        products = self.env['product.template'].search([('sync_push_magento', '=', True)])
        self._check_magento_sale_channel_default_product_attribute_set(magento_sale_channel, products)
        to_create_mappings = []
        for product in products:
            res, remote_object = magento_sale_channel.export_magento2x(product)
            if res:
                to_create_mappings.append({
                    'channel_id': magento_sale_channel.id,
                    'ecom_store': 'magento2x',
                    'template_name': product.id,
                    'odoo_template_id': product.id,
                    'default_code': product.default_code,
                    'barcode': product.barcode,
                    'store_product_id': remote_object.get('id') if isinstance(remote_object, dict) else remote_object.id,
                    'operation': 'export',
                })
        if to_create_mappings:
            return self.env['channel.template.mappings'].create(to_create_mappings)

    def action_view_m2_sale_channel(self):
        cron_action = self.env.ref('odoo_multi_channel_sale.action_multi_channel_view').read()[0]
        view_id = self.env.ref('odoo_multi_channel_sale.multi_channel_view_form').id
        res_id = self.env.ref('magento2x_odoo_bridge.magento2x_channel').id
        cron_action['view_mode'] = 'form'
        cron_action['views'] = [[view_id, 'form']]
        cron_action['view_id'] = (view_id, 'multi.channel.sale.from')
        cron_action['res_id'] = res_id
        return cron_action
