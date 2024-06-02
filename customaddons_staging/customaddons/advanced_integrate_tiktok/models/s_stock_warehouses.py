from odoo.exceptions import UserError, ValidationError
from odoo import fields, api, models, tools
import urllib3
from ..tools.api_wrapper_tiktok import validate_integrate_token

urllib3.disable_warnings()


class SWarehousesTiktokShop(models.Model):
    _inherit = "stock.warehouse"

    is_default = fields.Boolean()
    s_warehouse_tiktok_id = fields.Char(string='ID kho hàng Tiktok')
    is_mapping_warehouse = fields.Boolean('Đã đồng bộ lên sàn TMĐT Tiktok')
    e_commerce = fields.Selection(selection_add=[('tiktok', 'Tiktok')])

    @api.constrains('e_commerce')
    def _onchange_e_commerce1_tiktok(self):
        if self.e_commerce != 'tiktok':
            self.is_mapping_warehouse = False

    @api.constrains("e_commerce")
    def _onchange_synchronized_e_commerce(self):
        search_count = self.env['stock.warehouse'].search_count([('e_commerce', '=', 'tiktok')])
        if search_count > 1:
            raise ValidationError('Sàn Tiktok đã có kho')

    # @validate_integrate_token
    def button_sync_warehouse_tiktok(self):
        url_api = '/api/logistics/get_warehouse_list'
        req = self.env['base.integrate.tiktok']._get_data_tiktok(url_api=url_api).json()
        if req['code'] == 0:
            for rec in req['data']['warehouse_list']:
                if rec.get('is_default'):
                    search_warehouse_name = self.env['stock.warehouse'].sudo().search(
                        [('e_commerce', '=', 'tiktok')], limit=1)
                    if search_warehouse_name and search_warehouse_name.id != self.id:
                        raise UserError(('Sàn Tiktok đã có kho %s') % (search_warehouse_name.name,))
                    elif search_warehouse_name and search_warehouse_name.id == self.id:
                        search_warehouse_name.sudo().write({
                            'is_default': rec['is_default'],
                            's_warehouse_tiktok_id': rec['warehouse_id'],
                            'e_commerce': 'tiktok',
                            'is_mapping_warehouse': True
                        })
                else:
                    self.env['ir.logging'].sudo().create({
                        'name': '#Tiktok: button_sync_warehouse_tiktok',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'INFO',
                        'path': 'url',
                        'message': "is_default not in rec, rec: %s" % str(rec),
                        'func': 'button_sync_warehouse_tiktok',
                        'line': '0',
                    })
        else:
            self.env['ir.logging'].sudo().create({
                'name': '#Tiktok: button_sync_warehouse_tiktok',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': str(req),
                'func': 'button_sync_warehouse_tiktok',
                'line': '0',
            })
        ##Xóa warehouse tiktok id cũ
        search_warehouse_warehouse_id = self.sudo().search(
            [('s_warehouse_tiktok_id', '!=', False), ('e_commerce', '!=', 'tiktok')])
        if search_warehouse_warehouse_id:
            for rec_delete_warehouse_id in search_warehouse_warehouse_id:
                rec_delete_warehouse_id.sudo().write({
                    's_warehouse_tiktok_id': False,
                    'is_mapping_warehouse': False,
                    'is_default': False
                })
