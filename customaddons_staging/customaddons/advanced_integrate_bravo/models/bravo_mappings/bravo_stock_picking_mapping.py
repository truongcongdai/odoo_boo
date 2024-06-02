from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import pytz
import time
from datetime import datetime, timedelta


class BravoStockPickingMappings(models.Model):
    _name = 'bravo.stock.picking.mappings'
    _description = 'Bravo Stock Picking Mapping'
    _order = "create_date desc"
    picking_id = fields.Many2one('stock.picking', 'Stock picking')
    move_id = fields.Many2one('stock.move', 'Stock move')
    pos_order_id = fields.Many2one('pos.order', 'Pos order')
    sale_order_id = fields.Many2one('sale.order', 'Sale order')
    status = fields.Char(string='Status')
    status_code = fields.Char(
        string='Status code',
        required=False)
    post_api = fields.Char(string='API')
    need_resync_manual = fields.Boolean(string='Cần đồng bộ lại thủ công', default=False)

    def import_mapping_bravo(self, model, res, api):
        vals = []
        for record in model:
            val = {
                'status': res[0]['error_message'] if res[0]['error_message'] else res['Message'],
                'status_code': res[0]['error_code'] if res[0]['error_code'] else None,
                'post_api': api
            }
            if api in ['CreateTransferOnlInv', 'CreateTransferExportInv', 'CreateTransferImporttInv',
                       'CreateExportInv','CreateDiffInv']:
                val['picking_id'] = record.get('parent_id')
            elif api in ['CreateRetail', 'CreateReturnRetail']:
                # val['pos_order_id'] = record.get('id')
                val['pos_order_id'] = record.get('parent_id')
            elif api in ['CreateSucessOrder', 'CreateReturnOrder', 'CreateFailOrder']:
                val['sale_order_id'] = record.get('parent_id')
            vals.append(val)
        return self.sudo().create(vals)

    def update_status_code(self):
        mapping_ids = self.search([('status_code', '=', False)])
        if mapping_ids:
            for rec in mapping_ids:
                if rec.status == 'Thành công':
                    rec.sudo().write({
                        'status_code': '00'
                    })
                elif rec.status == 'Cấu trúc dữ liệu không hợp lệ':
                    rec.sudo().write({
                        'status_code': '10'
                    })
                elif rec.status == 'Dữ liệu bị trống (Rỗng)':
                    rec.sudo().write({
                        'status_code': '11'
                    })
                elif rec.status == 'Có lỗi trong quá trình xử lý':
                    rec.sudo().write({
                        'status_code': '99'
                    })

    def _action_resync_manual(self):
        start_time = time.time()
        post_data = self.env['bravo.stock.picking.mappings'].browse([])
        for rec in self:
            user_tz = self.env.user.tz or pytz.utc
            date_time_now = datetime.strptime(
                datetime.strftime(pytz.utc.localize(fields.datetime.today()).astimezone(pytz.timezone(user_tz)), "%Y-%m-%d 00:00:00"), '%Y-%m-%d %H:%M:%S')
            if rec.post_api == 'CreateRetail':
                if rec.need_resync_manual:
                    pos = self.env['pos.order']._cron_post_bravo_retail_sale(str(date_time_now.date()), rec.pos_order_id.id)
                    post_data |= rec
            elif rec.post_api == 'CreateReturnRetail':
                if rec.need_resync_manual:
                    pos = self.env['pos.order']._cron_post_bravo_return_retail_sale(str(date_time_now.date()), rec.pos_order_id.id)
                    post_data |= rec
            elif rec.post_api == 'CreateExportInv':
                if rec.need_resync_manual:
                    picking = self.env['stock.picking']._cron_post_bravo_outgoing_stock(str(date_time_now.date()), rec.picking_id.id)
                    post_data |= rec
            elif rec.post_api == 'CreateSucessOrder':
                if rec.need_resync_manual:
                    sale = self.env['stock.picking']._cron_post_online_success_order(str(date_time_now.date()), rec.sale_order_id.id)
                    post_data |= rec
            elif rec.post_api == 'CreateReturnOrder':
                if rec.need_resync_manual:
                    sale = self.env['stock.picking'].cron_online_sale_success_was_return_bravo(str(date_time_now.date()), rec.sale_order_id.id)
                    post_data |= rec
            elif rec.post_api == 'CreateFailOrder':
                if rec.need_resync_manual:
                    sale = self.env['stock.picking'].cron_online_sale_failed_was_return_bravo(str(date_time_now.date()), rec.sale_order_id.id)
                    post_data |= rec
            elif rec.post_api == 'CreateTransferExportInv':
                if rec.need_resync_manual:
                    picking = self.env['stock.picking']._cron_post_bravo_internal_transfer_out_stock(str(date_time_now.date()), rec.picking_id.id)
                    post_data |= rec
            elif rec.post_api == 'CreateTransferImporttInv':
                if rec.need_resync_manual:
                    picking = self.env['stock.picking']._cron_post_bravo_internal_transfer_in_stock(str(date_time_now.date()), rec.picking_id.id)
                    post_data |= rec
            elif rec.post_api == 'CreateTransferOnlInv':
                if rec.need_resync_manual:
                    picking = self.env['stock.picking']._cron_post_bravo_transfer_online_stock(str(date_time_now.date()), rec.picking_id.id)
                    post_data |= rec
            # elif rec.post_api == 'CreateDiffInv':
            #     picking = self.env['stock.picking']._cron_post_bravo_adjustment_stock_details()
            self.env.cr.commit()
        if len(post_data) > 0:
            post_data.sudo().update({
                'need_resync_manual': False
            })
        # check = time.time() -start_time
        # print('thoi gian check la %s' % check)
