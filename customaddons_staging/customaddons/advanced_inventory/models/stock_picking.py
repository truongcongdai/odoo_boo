from datetime import timedelta
import inspect
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transfer_in_id = fields.Many2one('s.internal.transfer', string='Lệnh nhập của phiếu điều chuyển', copy=False)
    transfer_out_id = fields.Many2one('s.internal.transfer', string='Lệnh xuất của phiếu điều chuyển', copy=False)
    deadline = fields.Datetime(string='Hạn chót')
    delivery_priority_type = fields.Many2one('s.stock.type.delivery.priority', string='Mức độ ưu tiên')
    is_notification_deadline = fields.Boolean(string='Thông báo hạn chót')
    confirm_user_id = fields.Many2one('res.users', string='Người duyệt')
    stock_package_ids = fields.Many2many('s.stock.picking.package', string='Kiện hàng')
    count_stock_package = fields.Integer(compute='_compute_count_stock_package', string='Số lượng kiện hàng')
    transfer_note = fields.Char(string='Ghi chú của phiếu điều chuyển', compute='_compute_note_of_transfer', store=True)
    receiver_id = fields.Many2one('res.users', string="Người nhận hàng")
    total_quantity_done = fields.Integer(string='Tổng số lượng hoàn thành', compute='_compute_total_quantity')
    total_quantity_demand = fields.Integer(string='Tổng số lượng nhu cầu', compute='_compute_total_quantity')
    code_transfer = fields.Char(string='Mã điều chuyển', compute="_compute_code_transfer", store=True)

    smart_product_barcode = fields.Char(string='Sản phẩm - Barcode')
    note = fields.Char(string='Ghi chú')
    s_warehouse_id = fields.Many2one('stock.warehouse', related="picking_type_id.warehouse_id")
    dia_diem_nguon = fields.Char(string='Từ (# Điều chuyển)', compute='_compute_s_internal_transfer')
    dia_diem_dich = fields.Char(string='Đến (# Điều chuyển)', compute='_compute_s_internal_transfer')
    s_origin = fields.Char(string='Mã biên lai', compute='_compute_s_origin', readonly=True, store=True)
    transfer_type = fields.Selection([('in', 'Phiếu nhập'), ('out', 'Phiếu xuất')],
                                     string='Loại điều chuyển',
                                     compute='_compute_transfer_type', readonly=True)
    negative_product_list = fields.Char(string='Danh sách sản phẩm lỗi tồn âm',
                                        compute='_compute_negative_product_list')
    s_location_usage = fields.Selection(related='location_id.usage', string="Loại địa điểm kho của địa điểm nguồn")
    s_location_dest_usage = fields.Selection(related='location_dest_id.usage',
                                             string="Loại địa điểm kho của địa điểm đích")
    is_pos_order = fields.Boolean(string='Là đơn hàng POS', compute='_compute_is_pos_order')

    @api.depends('move_ids_without_package')
    def _compute_negative_product_list(self):
        for rec in self:

            rec.negative_product_list = ''
            product_name = ''

            if rec.move_ids_without_package:
                for line in rec.move_ids_without_package:

                    product_line = line.product_id.display_name
                    temp_quant = line.env['stock.quant'].search([
                        ('location_id', '=', rec.location_id.id),
                        ('product_id', '=', line.product_id.id)
                    ])

                    if line.product_id.detailed_type in [
                        'product'] and line.quantity_done > 0 and rec.location_id.usage in ['internal', 'transit']:
                        if temp_quant:
                            if line.quantity_done > temp_quant[0].quantity:
                                product_name += '\n- ' + product_line
                        if not temp_quant:
                            product_name += '\n- ' + product_line
                rec.negative_product_list = product_name

    @api.depends('pos_order_id')
    def _compute_is_pos_order(self):
        for rec in self:
            if rec.pos_order_id:
                rec.is_pos_order = True
            else:
                rec.is_pos_order = False

    def write(self, vals):
        try:
            if vals.get('state'):
                for rec in self:
                    if rec.state == 'done' and vals.get('state') == 'assigned':
                        func = inspect.getouterframes(inspect.currentframe())[1][3]
                        self.env['ir.logging'].sudo().create({
                            'name': 'Tracking stock picking state',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'INFO',
                            'message': str(inspect.getouterframes(inspect.currentframe())),
                            'path': 'url',
                            'func': str(func),
                            'line': '0',
                        })
        except Exception as e:
            self.env['ir.logging'].sudo().create({
                'name': 'Tracking stock picking state',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'message': str(e),
                'path': 'url',
                'func': 'write',
                'line': '0',
            })
        res = super(StockPicking, self).write(vals)
        return res

    # def update_show_set_quantities_button(self):
    #     for rec in self:
    #         if rec.state in ['assigned']:
    #             rec.immediate_transfer = False

    @api.depends('picking_type_id', 'location_id', 'location_dest_id')
    def _compute_transfer_type(self):
        for rec in self:
            rec.transfer_type = None
            if rec.picking_type_id.code in ['internal']:
                # Phiếu nhập điều chuyển
                if rec.location_id.usage in ['internal'] and rec.location_id.s_is_transit_location is True:
                    if rec.location_dest_id.usage in [
                        'internal'] and rec.location_dest_id.s_is_transit_location is False:
                        rec.transfer_type = 'in'
                # Phiếu xuất điều chuyển
                elif rec.location_dest_id.usage in ['internal'] and rec.location_dest_id.s_is_transit_location is True:
                    if rec.location_id.usage in ['internal'] and rec.location_id.s_is_transit_location is False:
                        rec.transfer_type = 'out'
                # Phiếu xuất (Đơn POS)
                if rec.location_id.usage in ['internal']:
                    if rec.location_dest_id.usage in ['customer']:
                        rec.transfer_type = 'out'
                # Phiếu nhập (Đơn hoàn POS)
                if rec.location_id.usage in ['customer']:
                    if rec.location_dest_id.usage in ['internal']:
                        rec.transfer_type = 'in'
                # Kiểm kê
                if rec.location_id.usage in ['inventory']:
                    # Phiếu nhập kiểm kê
                    if rec.location_dest_id.usage in ['internal']:
                        rec.transfer_type = 'in'
                    # Phiếu nhập kho xem
                    if rec.location_dest_id.usage in ['view']:
                        rec.transfer_type = 'in'
                if rec.location_id.usage in ['internal']:
                    # Phiếu xuất kiểm kê
                    if rec.location_dest_id.usage in ['inventory']:
                        rec.transfer_type = 'out'
                    # Phiếu xuất điểm hàng hư (Địa điểm nguồn là một điểm hàng hư)
                    elif rec.location_dest_id.usage in ['internal'] and rec.location_dest_id.scrap_location is True:
                        rec.transfer_type = 'out'
                if rec.location_id.usage in ['view']:
                    # Phiếu xuất kho xem
                    if rec.location_dest_id.usage in ['inventory', 'internal']:
                        rec.transfer_type = 'out'
            # Nhận hàng
            if rec.picking_type_id.code in ['incoming']:
                rec.transfer_type = 'in'
                if rec.origin or rec.returned_picking_id:
                    returned_picking_id = self.sudo().search(['|', '|', ('name', '=', rec.origin.strip('Trả lại')),
                                                              ('name', '=', rec.origin.strip('Return of')),
                                                              ('id', '=', rec.returned_picking_id.id)], limit=1)
                    if returned_picking_id and returned_picking_id.transfer_type == 'in':
                        rec.transfer_type = 'out'
            # Giao hàng (Tên kiểu hoạt động: Các đơn hàng POS VD: 'BOO - Lê Chân: Các đơn hàng POS')
            if rec.picking_type_id.code in ['outgoing']:
                # Phiếu xuất (Đơn POS)
                if rec.location_id.usage in ['internal']:
                    if rec.location_dest_id.usage in ['customer', 'supplier', 'inventory']:
                        rec.transfer_type = 'out'
                # Phiếu nhập (Đơn hoàn POS)
                if rec.location_id.usage in ['customer']:
                    if rec.location_dest_id.usage in ['internal']:
                        rec.transfer_type = 'in'

    @api.depends('pos_order_id', 'sale_id')
    def _compute_s_origin(self):
        for rec in self:
            if rec.pos_order_id:
                rec.s_origin = rec.pos_order_id.pos_reference
            elif rec.sale_id:
                rec.s_origin = rec.sale_id.name
            else:
                rec.s_origin = False

    @api.depends('transfer_out_id', 'transfer_in_id')
    def _compute_s_internal_transfer(self):
        for r in self:
            r.dia_diem_nguon = ''
            r.dia_diem_dich = ''
            if r.transfer_out_id:
                r.dia_diem_nguon = r.transfer_out_id.location_out_id.s_complete_name
                r.dia_diem_dich = r.transfer_out_id.location_in_id.s_complete_name
            elif r.transfer_in_id:
                r.dia_diem_nguon = r.transfer_in_id.location_out_id.s_complete_name
                r.dia_diem_dich = r.transfer_in_id.location_in_id.s_complete_name

    @api.onchange('smart_product_barcode')
    def _onchange_smart_product_barcode(self):
        if self.state not in ('done', 'cancel') and self.smart_product_barcode and len(self.ids) > 0:
            current_product = self.env['product.product'].search([('barcode', '=', self.smart_product_barcode)],
                                                                 limit=1)
            if current_product:
                existing_move_line = None
                for move_line in self.move_ids_without_package:
                    if move_line.product_id.id == current_product.id:
                        existing_move_line = move_line
                    else:
                        move_line.update({
                            'sequence': move_line.sequence + 1
                        })
                if not existing_move_line:
                    new_data = {
                        'product_id': current_product.id,
                        'name': current_product.display_name,
                        'product_uom': current_product.uom_id.id,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.location_dest_id.id,
                        # 'quantity_done': 1,
                        # 'product_uom_qty': 1,
                        'sequence': 1
                    }
                    if self.state == 'draft':
                        new_data['product_uom_qty'] = 1
                        new_data['quantity_done'] = 0
                    else:
                        new_data['product_uom_qty'] = 0
                        new_data['quantity_done'] = 1
                    self.move_ids_without_package = [(0, 0, new_data)]
                else:
                    if self.state == 'draft':
                        existing_move_line.update({
                            # 'quantity_done': existing_move_line.quantity_done + 1,
                            'product_uom_qty': existing_move_line.product_uom_qty + 1,
                            'sequence': 1
                        })
                    else:
                        existing_move_line.update({
                            'quantity_done': existing_move_line.quantity_done + 1,
                            # 'product_uom_qty': existing_move_line.product_uom_qty + 1,
                            'sequence': 1
                        })

            self.smart_product_barcode = None

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template Phiếu Xuất/Nhập',
            'template': '/advanced_inventory/static/xlsx/phieu_xuat_nhap.xlsx'
        }]

    @api.depends('transfer_in_id', 'transfer_out_id')
    def _compute_code_transfer(self):
        for rec in self:
            rec.sudo().code_transfer = None
            if rec.sudo().transfer_in_id:
                rec.code_transfer = rec.transfer_in_id.code
            elif rec.sudo().transfer_out_id:
                rec.code_transfer = rec.transfer_out_id.code

    def _compute_total_quantity(self):
        for rec in self:
            rec.total_quantity_done = 0
            rec.total_quantity_demand = 0
            if rec.move_ids_without_package:
                for item in rec.move_ids_without_package:
                    rec.total_quantity_demand += item.product_uom_qty
                    if rec.state == 'done':
                        rec.total_quantity_done += item.quantity_done

    def unlink(self):
        for rec in self:
            if rec.transfer_in_id or rec.transfer_out_id:
                raise UserError(
                    'Lệnh nhập kho và lệnh xuất kho được sinh ra từ phiếu điều chuyển thì không được phép xóa.')

    @api.depends("transfer_in_id", "transfer_out_id", "note")
    def _compute_note_of_transfer(self):
        for rec in self:
            if rec.transfer_in_id:
                rec.transfer_note = rec.transfer_in_id.note
            elif rec.transfer_out_id:
                rec.transfer_note = rec.transfer_out_id.note
            elif rec.note:
                rec.transfer_note = rec.note
            else:
                rec.transfer_note = ''

    @api.model
    def create(self, vals_list):
        if 'backorder_id' in vals_list:
            if vals_list['backorder_id']:
                bo = self.env['stock.picking'].browse(vals_list['backorder_id'])
                if bo.transfer_in_id:
                    vals_list['transfer_in_id'] = bo.transfer_in_id.id
                elif bo.transfer_out_id:
                    vals_list['transfer_out_id'] = bo.transfer_out_id.id
        if 'active_model' in self.env.context and self.env.context[
            'active_model'] == 'stock.picking' and 'active_id' in self.env.context and self.id:
            if self.transfer_in_id:
                vals_list['transfer_in_id'] = self.transfer_in_id.id
            elif self.transfer_out_id:
                vals_list['transfer_out_id'] = self.transfer_out_id.id
        elif 'active_model' in self.env.context and self.env.context[
            'active_model'] == 's.internal.transfer' and 'active_id' in self.env.context and self.id:
            if self.transfer_in_id:
                vals_list['transfer_in_id'] = self.transfer_in_id.id
            elif self.transfer_out_id:
                vals_list['transfer_out_id'] = self.transfer_out_id.id
        result = super(StockPicking, self).create(vals_list)
        return result

    def _compute_count_stock_package(self):
        for rec in self:
            package_ids = self.env['s.stock.picking.package'].sudo().search([('stock_picking_id', 'in', rec.ids)])
            rec.count_stock_package = len(package_ids)

    def _pre_action_done_hook(self):
        if self.env.context.get('force_create_backorder'):
            return True
        return super(StockPicking, self)._pre_action_done_hook()

    def button_scrap(self):
        self.ensure_one()
        if self.env.user.has_group('advanced_sale.s_boo_group_thu_ngan') and not self.env.user.has_group(
                'base.group_system'):
            if self.picking_type_id and self.picking_type_id.warehouse_id:
                if self.picking_type_id.warehouse_id.id not in self.env.user.boo_warehouse_ids.ids:
                    raise UserError(_('Bạn không thể tạo phế liệu cho điều chuyển này.'))
        action = super(StockPicking, self).button_scrap()
        return action

    def button_validate(self):
        # Thu ngân của cửa hàng nào chỉ được xác nhận phiếu Xuất/ Nhập của cửa hàng đó
        if self.env.user.has_group('advanced_sale.s_boo_group_thu_ngan') and not self.env.user.has_group(
                'base.group_system'):
            if self.picking_type_id and self.picking_type_id.warehouse_id:
                if self.picking_type_id.warehouse_id.id not in self.env.user.boo_warehouse_ids.ids:
                    raise UserError(_('Bạn không thể xác nhận điều chuyển này.'))
        if self.magento_do_id:
            if self.move_ids_without_package:
                for line in self.move_ids_without_package:
                    if line.product_uom_qty > line.quantity_done:
                        raise UserError(_('Số lượng hoàn thành nhỏ hơn nhu cầu. DO từ M2 không thể tạo phần dang dở.'))
        if self.move_ids_without_package:
            for line in self.move_ids_without_package:
                if line.product_uom_qty and line.quantity_done:
                    if line.product_uom_qty < line.quantity_done:
                        raise UserError(_('Số lượng hoàn thành lớn hơn nhu cầu'))
                # check location_id, location_dest_id cua stock move voi location_id, location_dest_id cua stock picking
                if self.location_id and line.location_id:
                    if self.location_id.id != line.location_id.id:
                        raise UserError(
                            _('Dữ liệu kho xuất ở điều chuyển và dịch chuyển kho bị sai. Vui lòng kiểm tra lại hoặc liên hệ với Admin.'))
                if self.location_dest_id and line.location_dest_id:
                    if self.location_dest_id.id != line.location_dest_id.id:
                        raise UserError(
                            _('Dữ liệu kho nhận ở điều chuyển và dịch chuyển kho bị sai. Vui lòng kiểm tra lại hoặc liên hệ với Admin.'))
                if line.location_id and line.location_dest_id:
                    if line.location_id.id == line.location_dest_id.id:
                        raise UserError(
                            _('Dữ liệu kho nhận và kho xuất bị trùng ở dịch chuyển kho. Vui lòng kiểm tra lại hoặc liên hệ với Admin.'))
        if self.negative_product_list != '' and self.location_id.usage in ['internal', 'transit']:
            raise UserError(
                'Lỗi tồn âm sản phẩm hoặc sản phẩm hiện đang không có ở trong kho địa điểm nguồn (theo SKU): ' + self.negative_product_list)

        if self.transfer_in_id and 'force_create_backorder' not in self.env.context:
            ctx = dict(self.env.context)
            ctx['force_create_backorder'] = True
            #  Check move in
            if self.move_ids_without_package:
                move_out_done_dict = {}
                for e in self.transfer_in_id.transfer_line:
                    # move_out_done_dict[e.product_id.id] = e.qty_out_real - e.qty_in_real
                    for stock_move in self.move_ids_without_package:
                        line_product_ids = stock_move.picking_id.transfer_in_id.transfer_line.product_id.ids
                        if stock_move.product_id.id == e.product_id.id and stock_move.product_id.id in line_product_ids:
                            move_out_done_dict[e.product_id.id] = e.qty_out_real - e.qty_in_real
                        elif stock_move.product_id.id not in line_product_ids and stock_move.quantity_done == 0:
                            move_out_done_dict[stock_move.product_id.id] = 0
                move_in_dict = {}
                for e in self.move_ids_without_package:
                    if e.product_id.id not in move_in_dict:
                        move_in_dict[e.product_id.id] = e.quantity_done
                    else:
                        move_in_dict[e.product_id.id] += e.quantity_done

                for product_id in move_in_dict:
                    if product_id not in move_out_done_dict:
                        raise UserError('Bạn đang nhập kho sản phẩm không có trong lệnh điều chuyển')
                    elif move_in_dict[product_id] > move_out_done_dict[product_id]:
                        raise UserError('Bạn không thể nhận nhiều hơn số lượng xuất trong phiếu xuất')
            result = super(StockPicking, self).with_context(ctx).button_validate()
            if self.transfer_in_id and not isinstance(result, dict):
                check_raise = True
                qty_missing = []
                for move_line_id in self.move_line_ids:
                    check_done = False
                    if move_line_id.state == 'done':
                        for package in move_line_id.picking_id.stock_package_ids:
                            for product in package.product_lines_ids:
                                if not product.is_done:
                                    if move_line_id.qty_done == product.uom_qty:
                                        product.is_done = True
                                    elif move_line_id.product_id.id == product.product_id.id and package.state != 'da_nhan':
                                        if move_line_id.qty_done == product.qty_missing:
                                            product.qty_missing = 0
                                            product.is_done = True
                                        elif move_line_id.qty_done > product.qty_missing:
                                            qty_miss = move_line_id.qty_done - product.qty_missing
                                            if qty_miss <= 0:
                                                product.qty_missing = 0
                                                product.is_done = True
                                            elif product.qty > qty_miss:
                                                product.is_done = True
                                                qty_missing.append(
                                                    {'package': package.id, 'product': product.product_id.id,
                                                     'qty_missing': move_line_id.qty_done - product.qty_missing})

                                            for miss in qty_missing:
                                                if package.id != miss['package'] and miss[
                                                    'product'] == product.product_id.id:
                                                    product.qty_missing = miss['qty_missing']
                                        else:
                                            product.qty_missing = product.qty_missing - move_line_id.qty_done
                                            product.is_done = False
                for package in self.stock_package_ids:
                    for product in package.product_lines_ids:
                        if product.qty_missing <= 0 or product.is_done:
                            check_done = True
                        else:
                            check_done = False
                            break
                    if check_done:
                        package.state = 'da_nhan'

        else:
            self.is_notification_deadline = True
            if self.sale_id and self.sale_id.is_magento_order:
                result = super(StockPicking, self.with_context(skip_backorder=True)).button_validate()
            else:
                result = super(StockPicking, self).button_validate()
            if not isinstance(result, dict):
                check_done = True
                pickings_to_backorder = self.env.context.get('button_validate_picking_ids')
                not_to_backorder = self.env.context.get('picking_ids_not_to_backorder')
                if self.transfer_out_id:  # Điều chuyển nhập
                    # Check move out
                    if self.move_ids_without_package:
                        move_out_expect_dict = {}
                        for e in self.transfer_out_id.transfer_line:
                            related_current_stock_move_qty_done = 0
                            for stock_move in self.move_ids_without_package:
                                #     if stock_move.product_id.id == e.product_id.id:
                                #         related_current_stock_move_qty_done += stock_move.quantity_done
                                # move_out_expect_dict[e.product_id.id] = e.qty_expect - e.qty_out_real + related_current_stock_move_qty_done
                                line_product_ids = stock_move.picking_id.transfer_out_id.transfer_line.product_id.ids
                                if stock_move.product_id.id == e.product_id.id and stock_move.product_id.id in line_product_ids:
                                    related_current_stock_move_qty_done += stock_move.quantity_done
                                    move_out_expect_dict[
                                        e.product_id.id] = e.qty_expect - e.qty_out_real + related_current_stock_move_qty_done
                                elif stock_move.product_id.id not in line_product_ids and stock_move.quantity_done == 0:
                                    move_out_expect_dict[stock_move.product_id.id] = 0
                        move_out_dict = {}
                        for e in self.move_ids_without_package:
                            if e.product_id.id not in move_out_dict:
                                move_out_dict[e.product_id.id] = e.quantity_done
                            else:
                                move_out_dict[e.product_id.id] += e.quantity_done

                        for product_id in move_out_dict:
                            if product_id not in move_out_expect_dict:
                                raise UserError('Bạn đang xuất kho sản phẩm không có trong lệnh điều chuyển')
                            elif move_out_dict[product_id] > move_out_expect_dict[product_id]:
                                raise UserError(
                                    'Không điều chuyển vượt số lượng đề xuất. Vui lòng kiểm tra lại số lượng hoàn thành')

                    for move_id in self.move_ids_without_package:  # Kiểm tra hàng đã có kiện hàng chưa
                        if move_id.is_package:
                            if not_to_backorder or move_id.quantity_done > 0:
                                if not move_id.stock_package_ids:
                                    raise UserError(
                                        _('Bạn chưa chọn kiện hàng cho sản phẩm: %s') % move_id.product_id.name)
                    # if not pickings_to_backorder:
                    deadline = self.deadline
                    delivery_priority_type_id = self.delivery_priority_type
                    if delivery_priority_type_id:
                        deadline = fields.Datetime.now() + timedelta(
                            hours=delivery_priority_type_id.thoi_gian_thuc_hien / 2)  # Thời gian thực hiện / 2
                    move_ids_without_package = []

                    for e in self.move_ids_without_package:
                        if e.quantity_done > 0 or e.reserved_availability > 0:
                            move_ids_without_package.append((0, 0, {
                                'name': e.product_id.name,
                                'product_id': e.product_id.id,
                                'product_uom_qty': e.quantity_done,
                                'product_uom': e.product_id.uom_id.id,
                                'location_id': self.transfer_out_id.location_in_id.s_transit_location_id.id,
                                'location_dest_id': self.transfer_out_id.location_in_id.id,
                                'state': 'draft',
                            }))
                    picking_in_id = self.env['stock.picking'].create({
                        'stock_package_ids': self.stock_package_ids,
                        'transfer_in_id': self.transfer_out_id.id,
                        'picking_type_id': self.transfer_out_id.location_in_id.warehouse_id.int_type_id.id,
                        'location_id': self.transfer_out_id.location_in_id.s_transit_location_id.id,
                        'location_dest_id': self.transfer_out_id.location_in_id.id,
                        'delivery_priority_type': delivery_priority_type_id.id,
                        'deadline': deadline,
                        'confirm_user_id': self.env.user.id,
                        'move_ids_without_package': move_ids_without_package,
                        'state': 'draft',
                        'immediate_transfer': False,
                    })
                    picking_in_id.action_confirm()
                    for stock_move in self.move_ids_without_package:
                        if stock_move.product_uom_qty == stock_move.quantity_done:
                            for package in self.stock_package_ids:
                                package.state = 'dang_giao'
                                package.update({
                                    'stock_picking_id': [(4, picking_in_id.id)],
                                })
                        else:
                            for package_product in self.stock_package_ids:
                                check_done = True
                                for product in package_product.product_lines_ids:
                                    if product.qty == product.move_ids_without_package_id.quantity_done:
                                        check_done = True
                                    else:
                                        check_done = False
                                if check_done:
                                    package_product.update({
                                        'stock_picking_id': [(4, picking_in_id.id)],
                                    })
                                    package_product.update({
                                        'state': 'dang_giao',
                                    })

        if (
                self.location_id.s_is_inventory_adjustment_location or self.location_dest_id.s_is_inventory_adjustment_location) and not self.sale_id:
            for stock_move in self.move_ids_without_package:
                if stock_move.location_id.usage in ['internal', 'view']:
                    location = stock_move.location_id.id
                elif stock_move.location_dest_id.usage in ['internal', 'view']:
                    location = stock_move.location_dest_id.id
                quant = self.env['stock.quant'].sudo().search(
                    [('location_id', '=', location), ('product_id', '=', stock_move.product_id.id)])
                if quant:
                    inventory_adjustment_quantity = quant.quantity
                    stock_move.sudo().write({
                        'inventory_adjustment_quantity': inventory_adjustment_quantity
                    })
        return result

    def action_cancel(self):
        if len(self.move_ids_without_package) == 0:
            self.sudo().state = 'cancel'
            return super(StockPicking, self).action_cancel()
        if self.transfer_in_id and self.backorder_id:
            raise UserError('Không được hủy phiếu Back-order này. Liên hệ với nhà quản lý để xử lý điều chuyển này')
        # Thu ngân có quyền hủy DO của cửa hàng mình
        if self.env.user.has_group('advanced_sale.s_boo_group_thu_ngan') and not self.env.user.has_group(
                'base.group_system'):
            if self.picking_type_id and self.picking_type_id.warehouse_id:
                if self.picking_type_id.warehouse_id.id not in self.env.user.boo_warehouse_ids.ids:
                    raise UserError(_('Bạn không thể hủy điều chuyển này.'))
                # Thu ngân chỉ có thể hủy DO M2
                if not self.magento_do_id:
                    if not self.sale_id.is_magento_order:
                        raise UserError('Bạn chỉ có thể hủy điều chuyển M2.')
        return super(StockPicking, self).action_cancel()

    @api.onchange('delivery_priority_type')
    def _onchange_delivery_priority_type(self):
        for rec in self:
            rec.deadline = False
            if rec.create_date:
                if rec.delivery_priority_type:
                    rec.deadline = rec.create_date + timedelta(hours=rec.delivery_priority_type.thoi_gian_thuc_hien / 2)
            else:
                if rec.delivery_priority_type:
                    rec.deadline = rec.date + timedelta(hours=rec.delivery_priority_type.thoi_gian_thuc_hien / 2)

    def action_view_stock_package(self):
        return {
            'name': _('Kiện hàng'),
            'view_mode': 'tree,form',
            'res_model': 's.stock.picking.package',
            'domain': [('stock_picking_id', 'in', self.ids)],
            'type': 'ir.actions.act_window',
            'context': {'default_stock_picking_id': [self.id], 'create': False},
            'target': 'current',
        }

    def _cron_notification_deadline(self):
        today = fields.Datetime.now()
        stock_picking_ids = self.sudo().search(
            [('deadline', '!=', False), ('deadline', '<', today), ('is_notification_deadline', '=', False),
             ('confirm_user_id', '!=', False)])
        if len(stock_picking_ids) > 0:
            for rec in stock_picking_ids:
                rec.sudo().is_notification_deadline = True
                rec.sudo().message_post(
                    body=_("Phiếu điều chuyển đã quá hạn"),
                    partner_ids=[rec.confirm_user_id.partner_id.id],
                    message_type='notification',
                )

    def action_block_validate_picking(self):
        raise ValidationError('Không cho phép Xác nhận hàng loạt.')

    def action_block_unreserve_picking(self):
        raise ValidationError('Không cho phép Hủy giữ hàng hàng loạt.')

    # @api.onchange('move_line_ids', 'move_ids_without_package', 'move_line_ids_without_package')
    # def onchange_move_line_ids_check_s_transfer(self):
    #     for rec in self:
    #         if rec.transfer_out_id:
    #             move_out_expect_dict = {}
    #             for e in rec.transfer_out_id.transfer_line:
    #                 move_out_expect_dict[e.product_id.id] = e.qty_expect - e.qty_out_real
    #             # Check move_line_ids
    #             if rec.move_line_ids:
    #                 move_out_done_dict = {}
    #                 for e in rec.move_line_ids:
    #                     if e.product_id.id not in move_out_done_dict:
    #                         move_out_done_dict[e.product_id.id] = e.qty_done
    #                     else:
    #                         move_out_done_dict[e.product_id.id] += e.qty_done
    #
    #                 for product_id in move_out_done_dict:
    #                     if product_id not in move_out_expect_dict:
    #                         raise UserError('Bạn đang xuất kho sản phẩm không có trong lệnh điều chuyển')
    #                     elif move_out_done_dict[product_id] > move_out_expect_dict[product_id]:
    #                         raise UserError(
    #                             'Không điều chuyển vượt số lượng đề xuất. Vui lòng kiểm tra lại số lượng hoàn thành')
    #
    #             # Check move_line_ids_without_package
    #             if rec.move_line_ids_without_package:
    #                 move_line_out_done_dict = {}
    #                 for e in rec.move_line_ids_without_package:
    #                     if e.product_id.id not in move_line_out_done_dict:
    #                         move_line_out_done_dict[e.product_id.id] = e.qty_done
    #                     else:
    #                         move_line_out_done_dict[e.product_id.id] += e.qty_done
    #
    #                 for product_id in move_line_out_done_dict:
    #                     if product_id not in move_out_expect_dict:
    #                         raise UserError('Bạn đang xuất kho sản phẩm không có trong lệnh điều chuyển')
    #                     elif move_line_out_done_dict[product_id] > move_out_expect_dict[product_id]:
    #                         raise UserError(
    #                             'Không điều chuyển vượt số lượng đề xuất. Vui lòng kiểm tra lại số lượng hoàn thành')
    #
    #             #Check move out
    #             if rec.move_ids_without_package:
    #                 move_out_dict = {}
    #                 for e in rec.move_ids_without_package:
    #                     if e.product_id.id not in move_out_dict:
    #                         move_out_dict[e.product_id.id] = e.quantity_done
    #                     else:
    #                         move_out_dict[e.product_id.id] += e.quantity_done
    #
    #                 for product_id in move_out_dict:
    #                     if product_id not in move_out_expect_dict:
    #                         raise UserError('Bạn đang xuất kho sản phẩm không có trong lệnh điều chuyển')
    #                     elif move_out_dict[product_id] > move_out_expect_dict[product_id]:
    #                         raise UserError(
    #                             'Không điều chuyển vượt số lượng đề xuất. Vui lòng kiểm tra lại số lượng hoàn thành')
    #
    #         if rec.transfer_in_id:
    #             move_out_done_dict = {}
    #             for e in rec.transfer_in_id.transfer_line:
    #                 move_out_done_dict[e.product_id.id] = e.qty_out_real - e.qty_in_real
    #
    #             # Check move_line_ids
    #             if rec.move_line_ids:
    #                 move_in_done_dict = {}
    #                 for e in rec.move_line_ids:
    #                     if e.product_id.id not in move_in_done_dict:
    #                         move_in_done_dict[e.product_id.id] = e.qty_done
    #                     else:
    #                         move_in_done_dict[e.product_id.id] += e.qty_done
    #
    #                 for product_id in move_in_done_dict:
    #                     if product_id not in move_out_done_dict:
    #                         raise UserError('Bạn đang nhập kho sản phẩm không có trong lệnh điều chuyển')
    #                     elif move_in_done_dict[product_id] > move_out_done_dict[product_id]:
    #                         raise UserError('Bạn không thể nhận nhiều hơn số lượng xuất trong phiếu xuất')
    #
    #             #  Check move_line_ids_without_package
    #             if rec.move_line_ids_without_package:
    #                 move_line_in_done_dict = {}
    #                 for e in rec.move_line_ids_without_package:
    #                     if e.product_id.id not in move_line_in_done_dict:
    #                         move_line_in_done_dict[e.product_id.id] = e.qty_done
    #                     else:
    #                         move_line_in_done_dict[e.product_id.id] += e.qty_done
    #
    #                 for product_id in move_line_in_done_dict:
    #                     if product_id not in move_out_done_dict:
    #                         raise UserError('Bạn đang nhập kho sản phẩm không có trong lệnh điều chuyển')
    #                     elif move_line_in_done_dict[product_id] > move_out_done_dict[product_id]:
    #                         raise UserError('Bạn không thể nhận nhiều hơn số lượng xuất trong phiếu xuất')
    #
    #             #  Check move in
    #             if rec.move_ids_without_package:
    #                 move_in_dict = {}
    #                 for e in rec.move_ids_without_package:
    #                     if e.product_id.id not in move_in_dict:
    #                         move_in_dict[e.product_id.id] = e.quantity_done
    #                     else:
    #                         move_in_dict[e.product_id.id] += e.quantity_done
    #
    #                 for product_id in move_in_dict:
    #                     if product_id not in move_out_done_dict:
    #                         raise UserError('Bạn đang nhập kho sản phẩm không có trong lệnh điều chuyển')
    #                     elif move_in_dict[product_id] > move_out_done_dict[product_id]:
    #                         raise UserError('Bạn không thể nhận nhiều hơn số lượng xuất trong phiếu xuất')

    @api.onchange('location_dest_id')
    def _onchange_location_dest_id(self):
        for rec in self:
            if rec.location_dest_id:
                for move in rec.move_ids_without_package:
                    move.location_dest_id = rec.location_dest_id.id
                    move.move_line_ids.location_dest_id = rec.location_dest_id.id

    def view_stock_picking_by_group(self):
        user = self.env.user
        has_group = [user._is_admin(),
                     user.has_group('advanced_sale.s_boo_group_area_manager'),
                     user.has_group('advanced_sale.s_boo_group_dieu_phoi'),
                     user.has_group('advanced_sale.s_boo_group_kiem_ke')]

        user_group = [user.has_group('advanced_sale.s_boo_group_thu_ngan'),
                      user.has_group('advanced_sale.s_boo_group_hang_hoa'),
                      user.has_group('advanced_sale.s_boo_group_ecom')]

        if any(user_group) and not any(has_group):
            self.clear_caches()
            # picking_ids = self.env['stock.picking'].sudo().search([]).ids
            return {
                'name': _('Điều chuyển hàng'),
                'view_mode': 'tree,kanban,form,calendar',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'target': 'current',
                # 'domain': [('id', 'in', picking_ids)],
                'context': {'create': 0, 'copy': 0}
            }
        else:
            self.clear_caches()
            # picking_ids = self.env['stock.picking'].sudo().search([]).ids
            return {
                'name': _('Điều chuyển hàng'),
                'view_mode': 'tree,kanban,form,calendar',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'target': 'current',
                # 'domain': [('id', 'in', picking_ids)],
                'context': {'create': 1}
            }

    @api.depends('transfer_note')
    def _compute_note(self):
        for rec in self:
            rec.note = None
            if rec.transfer_note:
                rec.note = rec.transfer_note
