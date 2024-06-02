from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SInternalTransferLine(models.Model):
    _name = 's.internal.transfer.line'

    transfer_id = fields.Many2one('s.internal.transfer', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Tên sản phẩm')
    product_barcode = fields.Char(string='Barcode', related='product_id.barcode')
    product_ma_cu = fields.Char(string='Mã Cũ', related='product_id.ma_cu')
    product_default_code = fields.Char(string='SKU', related='product_id.default_code')
    product_ma_vat_tu = fields.Char(string='Mã vật tư', related='product_id.ma_vat_tu')
    product_ma_san_pham = fields.Char(string='Mã sản phẩm', related='product_id.ma_san_pham')
    qty_expect = fields.Float(string='Số lượng đề xuất')
    qty_out_real = fields.Float(string='Số lượng thực xuất', compute='_compute_qty_in_out_real')
    qty_in_real = fields.Float(string='Số lượng thực nhâp', compute='_compute_qty_in_out_real')
    status = fields.Char(string='Trạng thái', compute='_compute_qty_in_out_real')
    transfer_create_date = fields.Datetime(related='transfer_id.create_date', store=True)
    transfer_code = fields.Char(related='transfer_id.code')
    transfer_note = fields.Char(related='transfer_id.note')
    size = fields.Char(string='Size', related='product_id.kich_thuoc')
    transfer_location_in_id = fields.Many2one('stock.location', related='transfer_id.location_in_id')
    transfer_location_out_id = fields.Many2one('stock.location', related='transfer_id.location_out_id')
    chenh_lech_dieu_chuyen = fields.Float(string='Chênh lệch điều chuyển', compute='_compute_chenh_lech_dieu_chuyen')
    chech_lech_xuat = fields.Float(string='Chênh lệch xuất', compute='_compute_chenh_xuat')
    ton_kho_xuat = fields.Float(string='Tồn kho xuất', compute='_compute_ton_kho_xuat')
    ton_kho_nhap = fields.Float(string='Tồn kho nhập', compute='_compute_ton_kho_nhap')
    ma_phieu_xuat = fields.Text(string="Mã phiếu xuất", compute="_compute_stock_picking_out", store=True)
    ma_phieu_nhap = fields.Text(string="Mã phiếu nhập", compute="_compute_stock_picking_in", store=True)
    # ma_phieu_nhap = fields.Text(string="Mã phiếu nhập", compute="_compute_stock_picking_in")
    gia_tri_bien_the = fields.Many2many('product.template.attribute.value', 'related_product_template_variant_value_ids', string="Thông tin bổ sung", related='product_id.product_template_variant_value_ids')
    picking_out_undone_count = fields.Float(string="Số lượng phiếu xuất chưa hoàn thành",
                                            related='transfer_id.picking_out_undone_count')
    picking_in_undone_count = fields.Float(string="Số lượng phiếu nhập chưa hoàn thành",
                                           related='transfer_id.picking_in_undone_count')
    state = fields.Selection([
        ('cancel', 'Hủy'),
        ('draft', 'Chờ AM duyệt'),
        ('done', 'AM đã duyệt')
    ], string='Trạng thái điều chuyển', related='transfer_id.state')

    @api.onchange('qty_expect')
    def _onchange_qty_expect(self):
        if self.qty_expect % 1 != 0:
            raise UserError(_('Số lượng đề xuất phải là số nguyên.'))

    @api.onchange('qty_expect')
    def _onchange_qty_expect(self):
        if self.qty_expect % 1 != 0:
            raise UserError(_('Số lượng đề xuất phải là số nguyên.'))

    @api.depends("transfer_id.picking_out_ids")
    def _compute_stock_picking_out(self):
        for rec in self:
            list_code = []
            if rec.transfer_id.picking_out_ids:
                for picking in rec.transfer_id.picking_out_ids:
                    list_code.append(picking.name)
            rec.ma_phieu_xuat = ", ".join(list_code)

    @api.depends("transfer_id.picking_in_ids")
    def _compute_stock_picking_in(self):
        for rec in self:
            list_code = []
            if rec.transfer_id.picking_in_ids:
                for picking in rec.transfer_id.picking_in_ids:
                    list_code.append(picking.name)
            rec.ma_phieu_nhap = ", ".join(list_code)



    def _compute_ton_kho_xuat(self):
        for rec in self:
            stock_move_line = self.env['stock.move.line'].search(
                [('product_id', '=', rec.product_id.id), ('location_id', '=', rec.transfer_location_out_id.id),
                 ('state', '=', 'done')])
            total_done = 0
            for line in stock_move_line:
                total_done += line.qty_done
            rec.ton_kho_xuat = total_done

    def _compute_ton_kho_nhap(self):
        for rec in self:
            stock_move_line = self.env['stock.move.line'].search(
                [('product_id', '=', rec.product_id.id), ('location_dest_id', '=', rec.transfer_location_in_id.id),
                 ('state', '=', 'done')])
            total_done = 0
            for line in stock_move_line:
                total_done += line.qty_done
            rec.ton_kho_nhap = total_done

    def _compute_chenh_xuat(self):
        for rec in self:
            chenh_lech = rec.qty_out_real - rec.qty_in_real
            rec.update({
                'chech_lech_xuat': chenh_lech
            })

    def _compute_chenh_lech_dieu_chuyen(self):
        for rec in self:
            chenh_lech = rec.qty_expect - rec.qty_out_real
            rec.update({
                'chenh_lech_dieu_chuyen': chenh_lech
            })

    def _compute_qty_in_out_real(self):
        for rec in self:
            qty_out_real = 0
            qty_in_real = 0
            status = 'Chưa hoàn thành'
            trans_in_state_undone = False
            for e in rec.transfer_id.picking_out_ids:
                if e.state == 'done':
                    for line in e.move_ids_without_package:
                        if line.product_id.id == rec.product_id.id:
                            qty_out_real += line.quantity_done
            for e in rec.transfer_id.picking_in_ids:
                if e.state == 'done':
                    for line in e.move_ids_without_package:
                        if line.product_id.id == rec.product_id.id:
                            qty_in_real += line.quantity_done
            ## 2 trạng thái điều chuyển phải khớp với nhau kể cả có duyệt thiếu
            if rec.transfer_id.picking_in_ids:
                for e in rec.transfer_id.picking_in_ids:
                    for line in e.move_ids_without_package:
                        if line.product_id.id == rec.product_id.id:
                            if e.state != 'done':
                                trans_in_state_undone = True
                if trans_in_state_undone != True:
                    status = 'Hoàn thành'
            if rec.qty_expect == qty_out_real and qty_out_real == qty_in_real:
                status = 'Hoàn thành'
            rec.update({
                'qty_out_real': qty_out_real,
                'qty_in_real': qty_in_real,
                'status': status
            })

    @api.model
    def create(self, vals):
        if vals.get('qty_expect'):
            if vals.get('qty_expect') % 1 != 0:
                raise UserError('Lỗi số lượng đề xuất phải là số nguyên')
        return super(SInternalTransferLine, self).create(vals)