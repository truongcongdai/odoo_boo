from odoo import fields, models, api, _
from odoo.exceptions import UserError
import qrcode
import base64
from io import BytesIO


class SStockPickingPackage(models.Model):
    _name = 's.stock.picking.package'
    _description = 'Kiện hàng'
    _rec_name = 'name'

    sequence = fields.Char(default="New", string="Tên")
    name = fields.Char(string='Kiện hàng')
    stock_picking_id = fields.Many2many('stock.picking', string='Lệnh xuất', copy=False)
    shipper_id = fields.Many2one('res.users', string='Người vận chuyển', copy=False)
    recipient_id = fields.Many2one('res.users', string='Người nhận', compute="_compute_recipient_id", copy=False)
    product_lines_ids = fields.One2many('s.stock.picking.package.line', 'package_id', string='Chi tiết', copy=False)
    quantity_product = fields.Integer(string='Số lượng sản phẩm', compute='_compute_quantity_product')
    carton = fields.Char('Carton', compute='_compute_carton')
    qrcode = fields.Binary(string='QR Code', compute='_compute_qrcode')
    state = fields.Selection([('nhap', 'Nháp'), ('dang_giao', 'Đang giao'), ('da_nhan', 'Đã nhận')],
                             string='Trạng thái', default='nhap', copy=False)

    def _compute_recipient_id(self):
        for rec in self:
            rec.recipient_id = False
            if rec.stock_picking_id:
                for receive in rec.stock_picking_id:
                    if receive.receiver_id:
                        rec.recipient_id = receive.receiver_id
                        break

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('s.stock.picking.package')
        return super(SStockPickingPackage, self).create(vals)

    def unlink(self):
        if self.product_lines_ids:
            # for line in self.product_lines_ids:
            self.product_lines_ids.unlink()
        return super(SStockPickingPackage, self).unlink()

    def _compute_qrcode(self):
        for rec in self:
            io = BytesIO()
            img = qrcode.make(f"{rec.sequence}")
            img.save(io, format='PNG')
            rec.qrcode = base64.b64encode(io.getvalue())

    def _compute_quantity_product(self):
        for rec in self:
            total = 0
            for product in rec.product_lines_ids:
                total += product.qty
            rec.quantity_product = total

    def _compute_carton(self):
        for rec in self:
            package = self.env['s.stock.picking.package'].search([('stock_picking_id', '=', self.stock_picking_id.ids)])
            list_id = [rec.id for rec in package]
            list_id.sort()
            index = list_id.index(rec.id)
            rec.carton = f"{index + 1}/{len(list_id)}"

    def action_print_transfer_report(self):
        return self.env.ref('advanced_inventory.action_report_stock_picking_package').report_action(self)


class SStockPackageLine(models.Model):
    _name = 's.stock.picking.package.line'
    _description = 'Chi tiết kiện hàng'

    package_id = fields.Many2one('s.stock.picking.package', string='Kiện hàng')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    qty = fields.Integer(string='Số lượng')
    uom_qty = fields.Integer(string='Số lượng yêu cầu')
    qty_missing = fields.Integer(string='Còn thiếu ')
    move_ids_without_package_id = fields.Many2one('stock.move')
    is_done = fields.Boolean(string='Đã xong', default=False)

    def write(self, vals):
        res = super(SStockPackageLine, self).write(vals)
        if 'qty' in vals:
            if self.move_ids_without_package_id and self.qty <= self.move_ids_without_package_id.product_uom_qty:
                exits_product = self.env['s.stock.picking.package.line'].search([('move_ids_without_package_id', '=', self.move_ids_without_package_id.id)])
                if exits_product:
                    qty = 0
                    for line in exits_product:
                        if len(line.move_ids_without_package_id.stock_package_ids) > 1:
                            qty += line.qty
                        else:
                            qty = self.qty
                    self.move_ids_without_package_id.quantity_done = qty
                    self.qty_missing = self.qty
                else:
                    self.move_ids_without_package_id.quantity_done = self.qty
                    self.qty_missing = self.qty

            else:
                raise UserError(_('Số lượng nhập vào không được lớn hơn nhu cầu'))
        return res

    def unlink(self):
        for package_line in self:
            package_line.move_ids_without_package_id.stock_package_ids = [(3, package_line.package_id.id)]
            package_line.move_ids_without_package_id.quantity_done -= package_line.qty
        return super(SStockPackageLine, self).unlink()

