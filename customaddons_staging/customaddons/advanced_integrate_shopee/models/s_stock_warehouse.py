from odoo.exceptions import UserError, ValidationError
from odoo import fields, api, models
import requests
import json
from ..tools.api_wrapper_shopee import validate_integrate_token


class SStockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    s_shopee_location_id = fields.Char()
    s_shopee_warehouse_id = fields.Char()
    s_shopee_is_mapping_warehouse = fields.Boolean('Đã đồng bộ lên sàn TMĐT Shopee')
    e_commerce = fields.Selection(selection_add=[('shopee', 'Shopee')])

    @api.constrains('e_commerce')
    def _onchange_e_commerce_shopee(self):
        if self.e_commerce != 'shopee':
            self.s_shopee_is_mapping_warehouse = False

    @api.constrains("e_commerce")
    def _onchange_synchronized_e_commerce_shopee(self):
        search_count = self.env['stock.warehouse'].search_count([('e_commerce', '=', 'shopee')])
        if search_count > 1:
            raise ValidationError('Sàn Shopee đã có kho')

    def button_sync_warehouse_shopee(self):
        url_api = '/api/v2/shop/get_warehouse_detail'
        req = self.env['s.base.integrate.shopee']._get_data_shopee(api=url_api)
        req_json = req.json()
        search_warehouse_name = self.env['stock.warehouse'].sudo().search(
            [('e_commerce', '=', 'shopee')], limit=1)
        if req.status_code == 200:
            if req_json.get('response'):
                if search_warehouse_name and search_warehouse_name.id != self.id:
                    raise UserError(('Sàn Shopee đã có kho %s') % (search_warehouse_name.name,))
                elif search_warehouse_name and search_warehouse_name.id == self.id:
                    search_warehouse_name.sudo().write({
                        's_shopee_location_id': req.get('response')[0]['location_id'],
                        's_shopee_warehouse_id': req.get('response')[0]['warehouse_id'],
                        'e_commerce': 'shopee',
                        's_shopee_is_mapping_warehouse': True
                    })
            else:
                if search_warehouse_name and search_warehouse_name.id != self.id:
                    raise UserError(('Sàn Shopee đã có kho %s') % (search_warehouse_name.name,))
                elif search_warehouse_name and search_warehouse_name.id == self.id:
                    search_warehouse_name.sudo().write({
                        'e_commerce': 'shopee',
                        's_shopee_is_mapping_warehouse': True,
                        "s_shopee_location_id": ""
                    })

            ##Xóa warehouse shopee id cũ
            search_warehouse_warehouse_id = self.sudo().search(
                [('s_shopee_warehouse_id', '!=', False), ('e_commerce', '!=', 'shopee')])
            if search_warehouse_warehouse_id:
                for rec_delete_warehouse_id in search_warehouse_warehouse_id:
                    rec_delete_warehouse_id.sudo().write({
                        's_shopee_warehouse_id': False,
                        's_shopee_is_mapping_warehouse': False,
                        's_shopee_location_id': False
                    })
        else:
            self.env['ir.config_parameter'].sudo().set_param(
                'advanced_integrate_shopee.is_error_token_shopee', 'True')
            self.env['ir.logging'].sudo().create({
                'name': 'Shopee_button_sync_warehouse',
                'type': 'server',
                'dbname': 'boo',
                'level': 'INFO',
                'path': 'url',
                'message': req_json.get('message'),
                'func': 'button_sync_warehouse_shopee',
                'line': '0',
            })