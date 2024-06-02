from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import timedelta


class SInternalTransfer(models.Model):
    _name = 's.internal.transfer'
    _rec_name = 'code'

    code = fields.Char(string='Mã điều chuyển')
    note = fields.Char(string='Ghi chú')
    location_out_id = fields.Many2one('stock.location', string='Kho xuất hàng')
    location_out_code = fields.Char(string='Mã kho xuất hàng', related='location_out_id.s_code')
    location_in_id = fields.Many2one('stock.location', string='Kho nhập hàng')
    location_in_code = fields.Char(string='Mã kho nhập hàng', related='location_in_id.s_code')
    compute_qty_expect = fields.Float(compute='_compute_qty_expect')
    confirm_user_id = fields.Many2one('res.users', string='Người duyệt', copy=False)
    confirm_date = fields.Datetime(string='Ngày duyệt', copy=False)
    transfer_line = fields.One2many('s.internal.transfer.line', 'transfer_id', string='Chi tiết', copy=True)
    state = fields.Selection([('cancel', "Hủy"), ('draft', "Chờ AM duyệt"), ('done', "AM đã duyệt")],
                             string="Trạng thái", default='draft')

    picking_out_ids = fields.One2many('stock.picking', 'transfer_out_id', string='Lệnh xuất', copy=False)
    picking_out_ids_count = fields.Integer(string='Số Lệnh xuất', compute='_compute_picking_out_ids_count')
    picking_in_ids = fields.One2many('stock.picking', 'transfer_in_id', string='Lệnh nhập', copy=False)
    picking_in_ids_count = fields.Integer(string='Số Lệnh nhập', compute='_compute_picking_in_ids_count')
    delivery_priority_type_id = fields.Many2one('s.stock.type.delivery.priority', string='Mức độ ưu tiên')
    picking_out_undone_count = fields.Float(string='Số lượng phiếu xuất chưa hoàn thành',
                                            compute='_compute_picking_out_undone_count')
    picking_in_undone_count = fields.Float(string='Số lượng phiếu nhập chưa hoàn thành',
                                           compute='_compute_picking_in_undone_count')

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template Phiếu điều chuyển',
            'template': '/advanced_inventory/static/xlsx/template_dieu_chuyen.xlsx'
        }]

    def get_picking_out_undone_count(self, picking_out_ids):
        picking_out_undone_count = 0
        if len(picking_out_ids) > 0:
            picking_out_undone_count = len(picking_out_ids.filtered(lambda l: l.state != 'done'))
        return picking_out_undone_count

    def _compute_picking_out_undone_count(self):
        for rec in self:
            picking_out = self.get_picking_out_undone_count(rec.picking_out_ids)
            rec.picking_out_undone_count = picking_out

    def get_picking_in_undone_count(self, picking_in_ids):
        picking_in_undone_count = 0
        if len(picking_in_ids) > 0:
            picking_in_undone_count = len(picking_in_ids.filtered(lambda l: l.state != 'done'))
        return picking_in_undone_count

    def _compute_picking_in_undone_count(self):
        for rec in self:
            picking_in = self.get_picking_in_undone_count(rec.picking_in_ids)
            rec.picking_in_undone_count = picking_in

    def _compute_picking_out_ids_count(self):
        for rec in self:
            rec.picking_out_ids_count = len(rec.picking_out_ids)

    def _compute_picking_in_ids_count(self):
        for rec in self:
            rec.picking_in_ids_count = len(rec.picking_in_ids)

    def _compute_qty_expect(self):
        for rec in self:
            compute_qty_expect = 0
            for line in rec.transfer_line:
                compute_qty_expect += line.qty_expect
            rec.compute_qty_expect = compute_qty_expect

    @api.model
    def create(self, vals_list):
        sequence = self.env['ir.sequence'].next_by_code('s.internal.transfer')
        day = fields.Date.today().day
        if day < 10:
            day = '0' + str(day)
        month = fields.Date.today().month
        if month < 10:
            month = '0' + str(month)
        year = fields.Date.today().year % 100
        code = f"DCNB-{day}{month}{year}-{sequence}"
        vals_list['code'] = code
        res = super(SInternalTransfer, self).create(vals_list)
        return res

    # @api.onchange('transfer_line')
    # def onchange_transfer_line(self):
    #     product_ids = []
    #     for e in self.transfer_line:
    #         if e.product_id.id not in product_ids:
    #             product_ids.append(e.product_id.id)
    #         else:
    #             raise UserError('Chi tiết sản phẩm bị trùng : ' + e.product_id.name)

    @api.onchange('location_out_id', 'location_in_id')
    def onchange_location_in_out_id(self):
        if self.location_out_id and self.location_in_id and self.location_out_id.id == self.location_in_id.id:
            raise UserError('Kho xuất, nhập bị trùng')

    def action_confirm(self):
        vals = {}
        list_new_line = []
        for line in self.transfer_line:
            product_id = line.product_id.id
            if product_id in vals:
                qty = vals[product_id]
                vals[product_id] = qty + line.qty_expect
            else:
                vals[product_id] = line.qty_expect
        for key in vals:
            list_new_line.append(
                {
                    'product_id': key,
                    'qty_expect': vals[key],
                }
            )
        self.sudo().transfer_line = [(5, 0, 0)] + [(0, 0, val) for val in list_new_line]
        for rec in self:
            if not rec.transfer_line or len(rec.transfer_line) == 0:
                raise UserError('Thiếu chi tiết sản phẩm')

        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'internal')])
        if len(picking_type_id) > 0:
            # valid stock_quant
            for rec in self:
                product_ids = ""
                for e in rec.transfer_line:
                    if not e.product_id:
                        raise UserError('Thiếu thông tin sản phẩm trong chi tiết sản phẩm')
                    current_stock_quant = 0
                    current_stock_quant_list = self.env['stock.quant'].sudo().read_group([
                        ('product_id', '=', e.product_id.id),
                        ('location_id', '=', rec.location_out_id.id)
                    ], ['location_id', 'quantity', 'reserved_quantity'], ['location_id'])
                    for current_stock_quant_item in current_stock_quant_list:
                        if current_stock_quant_item['quantity'] >= current_stock_quant_item['reserved_quantity']:
                            current_stock_quant += current_stock_quant_item['quantity'] - current_stock_quant_item['reserved_quantity']
                    if e.qty_expect > current_stock_quant:
                        if e.product_default_code:
                            product_ids += '\n- ' + e.product_id.name + ' ' + '(' + e.product_default_code + ')'
                        else:
                            product_ids += '\n- ' + e.product_id.name + ' ' + '( SKU Rỗng )'
                if len(product_ids):
                    raise UserError('Số lượng xuất kho không được phép vượt qua tồn kho hiện tại.'
                                    '\nVui lòng kiểm tra lại số lượng tồn kho của sản phẩm (theo SKU):%s' % (
                                        product_ids,))
            picking_type_id = self.location_out_id.warehouse_id.int_type_id.id
            for rec in self:
                if rec.picking_out_ids:
                    raise UserError('Phiếu xuất điều chuyển %s đã được tạo' % rec.code)
                deadline = False
                move_ids_without_package = []
                if rec.delivery_priority_type_id:
                    deadline = rec.create_date + timedelta(hours=rec.delivery_priority_type_id.thoi_gian_thuc_hien / 2)
                rec.confirm_user_id = self.env.user.id
                rec.confirm_date = fields.Datetime.now()
                for e in rec.transfer_line:
                    move_ids_without_package.append((0, 0, {
                        'name': e.product_id.name,
                        'product_id': e.product_id.id,
                        'product_uom_qty': e.qty_expect,
                        'product_uom': e.product_id.uom_id.id,
                        'location_id': rec.location_out_id.id,
                        'location_dest_id': rec.location_in_id.s_transit_location_id.id,
                        'state': 'draft',
                    }))
                picking_out_id = self.env['stock.picking'].create({
                    'transfer_out_id': rec.id,
                    'picking_type_id': picking_type_id,
                    'location_id': rec.location_out_id.id,
                    'location_dest_id': rec.location_in_id.s_transit_location_id.id,
                    'delivery_priority_type': rec.delivery_priority_type_id.id,
                    'deadline': deadline,
                    'confirm_user_id': self.env.user.id,
                    'move_ids_without_package': move_ids_without_package,
                    'state': 'draft',
                    'immediate_transfer': False,
                })
                picking_out_id.action_confirm()
                ###Thêm log check bug kho xuất trùng kho nhận
                if picking_out_id.location_dest_id.id == rec.location_out_id.id:
                    param = {
                        'transfer_out_id': rec.id,
                        'picking_type_id': picking_type_id,
                        'location_id': rec.location_out_id.id,
                        'location_dest_id': rec.location_in_id.s_transit_location_id.id,
                        'delivery_priority_type': rec.delivery_priority_type_id.id,
                        'deadline': deadline,
                        'confirm_user_id': self.env.user.id,
                        'move_ids_without_package': move_ids_without_package,
                        'state': 'draft',
                        'immediate_transfer': False,
                    }
                    self.env['ir.logging'].sudo().create({
                        'name': 'Tracking DCNB trùng location',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'INFO',
                        'message': str(param),
                        'path': 'url',
                        'func': 'action_confirm',
                        'line': '0',
                    })
                rec.update({
                    'state': 'done'
                })
        else:
            raise UserError('Không tìm thấy stock.picking.type internal')

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError('Không thể hủy điều chuyển đang trong trạng thái AM đã duyệt.'
                                '\nDanh sách tích chọn đang có điều chuyển ở trạng thái AM đã duyệt. '
                                'Vui lòng kiểm tra lại.')
            else:
                rec.state = 'cancel'

    def action_open_stock_picking_in(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'name': 'Lệnh nhập kho cho ' + self.code,
            'domain': [('id', 'in', self.picking_in_ids.ids)],
            'view_mode': 'tree,form',
            'views': [(False, "tree"), (False, "form")],
        }

    def action_open_stock_picking_out(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'name': 'Lệnh xuất kho cho ' + self.code,
            'domain': [('id', 'in', self.picking_out_ids.ids)],
            'view_mode': 'tree,form',
            'views': [(False, "tree"), (False, "form")],
        }

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError('Không thể xóa điều chuyển đang trong trạng thái AM đã duyệt.'
                                '\nDanh sách tích chọn đang có điều chuyển ở trạng thái AM đã duyệt. '
                                'Vui lòng kiểm tra lại.')
            else:
                return super(SInternalTransfer, self).unlink()

    def merge_s_internal_transfer_line(self):
        vals = {}
        list_new_line = []
        for line in self.transfer_line:
            product_id = line.product_id.id
            if product_id in vals:
                qty = vals[product_id]
                vals[product_id] = qty + line.qty_expect
            else:
                vals[product_id] = line.qty_expect
        for key in vals:
            list_new_line.append(
                {
                    'product_id': key,
                    'qty_expect': vals[key],
                }
            )
        self.sudo().transfer_line = [(5, 0, 0)] + [(0, 0, val) for val in list_new_line]
        print(list_new_line)