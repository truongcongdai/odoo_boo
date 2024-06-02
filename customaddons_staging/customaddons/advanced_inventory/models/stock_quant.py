from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import pytz


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    sku = fields.Char(
        related='product_id.sku',
        store=True
    )
    barcode = fields.Char(
        related='product_id.barcode',
        store=True
    )
    mau_sac = fields.Char(
        related='product_id.mau_sac',
        store=True
    )
    kich_thuoc = fields.Char(
        related='product_id.kich_thuoc',
        store=True
    )
    gioi_tinh = fields.Selection([('male', 'Male'), ('female', 'Female'), ('unisex', 'Unisex'), ('other', 'Other')],
                                 string='Giới tính',
                                 related="product_id.gioi_tinh", store=True)

    ma_san_pham = fields.Char(
        related='product_id.ma_san_pham',
        store=True
    )

    ma_cu = fields.Char(
        related='product_id.ma_cu',
        store=True
    )
    ma_vat_tu = fields.Char(
        related='product_id.ma_vat_tu',
        store=True
    )

    thuong_hieu = fields.Many2one(
        string="Brand",
        comodel_name='s.product.brand',
        compute="_compute_brand_stock_quant",
        store=True
    )

    product_category = fields.Many2one(
        comodel_name='product.category',
        related='product_id.categ_id',
        store=True
    )
    category_id = fields.Many2one('product.category', string='Nhóm sản phẩm', related='product_id.categ_id', store=True)
    is_expired_warning = fields.Char(string='Đã quá hạn (Category)', compute='_compute_time_quantity_warning',
                                     store=True)
    s_product_uom_qty = fields.Float(string='Tồn sắp về', compute='_compute_s_product_uom_qty')
    s_inventory_quantity = fields.Float(string='Giá trị thực số lượng đã đếm', compute='_compute_s_inventory_quantity',
                                        store=True)
    time_product_expired_warning = fields.Integer(string='Đã quá hạn (Sản phẩm)',
                                                  compute='_compute_time_quantity_warning', store=True)

    @api.depends('product_id.thuong_hieu')
    def _compute_brand_stock_quant(self):
        for rec in self:
            if rec.id:
                thuong_hieu_id = rec.product_id.thuong_hieu.id
                if thuong_hieu_id and rec.id:
                    self._cr.execute("""UPDATE stock_quant SET thuong_hieu =%s WHERE id = %s""",
                                     (thuong_hieu_id, rec.id,))

    @api.depends('location_id')
    def _compute_s_product_uom_qty(self):
        for rec in self:
            sum_uom = 0
            if rec.inventory_quantity_set is False and rec.location_id.usage in [
                'internal'] and rec.location_id.s_is_transit_location is False and rec.location_id.scrap_location is False:
                if rec.location_id:
                    # stock_incoming = rec.env['stock.move'].sudo().search(
                    #     [('state', '=', 'assigned'),
                    #      ('location_dest_id', '=', rec.location_id.id),
                    #      ('product_id', '=', rec.product_id.id)])
                    move_line_ids = self.env['stock.move.line'].sudo().search(
                        [('product_id', '=', rec.product_id.id),
                         ('location_dest_id', '=', rec.location_id.id),
                         ('state', '=', 'assigned')])
                    if len(move_line_ids) > 0:
                        for line in move_line_ids:
                            sum_uom += line.product_uom_qty
                    # if len(stock_incoming) > 0:
                    #     for line in stock_incoming:
                    #         sum_uom += line.product_uom_qty
            rec.s_product_uom_qty = sum_uom

    @api.depends('product_categ_id.time_quantity_warning', 'quantity', 'product_tmpl_id.time_product_expired')
    def _compute_time_quantity_warning(self, data=False):
        stock_quant_expired = []
        if len(self.ids) > 0:
            stock_quant_expired = self
        if data:
            stock_quant_expired = self.env['stock.quant'].sudo().search([('id', 'in', data)])
        if len(stock_quant_expired) > 0:
            for r in stock_quant_expired:
                if r.location_id.usage == 'internal' and not r.location_id.s_is_transit_location and \
                        not r.location_id.return_location and not r.location_id.scrap_location:
                    stock_picking_ids = self.env['stock.picking'].search([
                        ('product_id', '=', r.product_id.id),
                        ('location_dest_id', '=', r.location_id.id),
                        ('transfer_type', '=', 'in'),
                        ('state', '=', 'done')])
                    if stock_picking_ids:
                        date_done_stock_picking_ids = sorted(stock_picking_ids.filtered(lambda x: x.date_done).mapped(
                            'date_done'))
                        if len(date_done_stock_picking_ids) > 0:
                            # Cảnh báo tồn kho theo category
                            if r.product_categ_id.time_quantity_warning > 0:
                                result_qty_date = (datetime.now() - date_done_stock_picking_ids[-1] - timedelta(
                                    days=r.product_categ_id.time_quantity_warning)).days
                                if result_qty_date > r.product_categ_id.time_quantity_warning:
                                    self._cr.execute("""UPDATE stock_quant SET is_expired_warning = %s WHERE id = %s""",
                                                     (result_qty_date, r.id))
                            # Cảnh bảo tồn kho theo sản phẩm
                            if r.product_tmpl_id.time_product_expired > 0:
                                user_tz = self.env.user.tz or pytz.utc
                                time_now = datetime.strptime(datetime.strftime(
                                    pytz.utc.localize(fields.datetime.today()).astimezone(pytz.timezone(user_tz)),
                                    "%Y-%m-%d %H:%M:%S"), '%Y-%m-%d %H:%M:%S')
                                time_date_done = datetime.strptime(datetime.strftime(
                                    pytz.utc.localize(date_done_stock_picking_ids[-1]).astimezone(
                                        pytz.timezone(user_tz)),
                                    "%Y-%m-%d %H:%M:%S"), '%Y-%m-%d %H:%M:%S')
                                result_date_expired = (time_now.date() - time_date_done.date() - timedelta(
                                    days=r.product_tmpl_id.time_product_expired)).days
                                if result_date_expired > r.product_tmpl_id.time_product_expired:
                                    self._cr.execute(
                                        """UPDATE stock_quant SET time_product_expired_warning = %s WHERE id = %s""",
                                        (result_date_expired, r.id))

    def _cron_compute_time_quantity_warning(self):
        query_stock_expired = self._cr.execute(
            """SELECT id FROM stock_quant WHERE is_expired_warning is not NULL 
            AND location_id in (select id from stock_location where usage = 'internal'
                                     and (s_is_transit_location is FALSE or s_is_transit_location is NULL)
                                     and (return_location is FALSE or return_location is null)
                                     and (scrap_location is FALSE or scrap_location is null)
                                     and (s_is_inventory_adjustment_location is FALSE or s_is_inventory_adjustment_location is null) and active is TRUE)""", )
        result_query_stock_expired = [item[0] for item in self._cr.fetchall()]
        if len(result_query_stock_expired) > 0:
            self._compute_time_quantity_warning(result_query_stock_expired)

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template nhập tồn kho',
            'template': '/advanced_inventory/static/xlsx/template_nhap_ton_kho.xlsx'
        }]

    def write(self, vals):
        res = super(StockQuant, self).write(vals)
        for rec in self:
            quant = self._gather(rec.product_id, rec.location_id, lot_id=None, package_id=None, owner_id=None,
                                 strict=True)
            if rec.quantity < 0 and rec.location_id.usage in ['internal', 'transit']:
                if 'inventory_quantity' in vals:
                    if vals['inventory_quantity'] < 0:
                        raise UserError('Lỗi tồn kho âm trên sản phẩm ' + rec.product_id.display_name)
                else:
                    if not len(quant) > 1:
                        raise UserError('Lỗi tồn kho âm trên sản phẩm ' + rec.product_id.display_name)
            if rec.inventory_quantity % 1 != 0:
                raise UserError('Lỗi số lượng đã đếm phải là số nguyên')
        return res

    @api.model
    def create(self, vals):
        res = super(StockQuant, self).create(vals)
        quant = self._gather(res.product_id, res.location_id, lot_id=None, package_id=None, owner_id=None, strict=False)
        if not quant:
            if res.quantity < 0 and res.location_id.usage in ['internal', 'transit']:
                raise UserError('Lỗi tồn kho âm trên sản phẩm ' + res.product_id.display_name)
        return res

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        stock_location = super(StockQuant, self)._gather(product_id, location_id, lot_id, package_id, owner_id, strict)
        if not strict:
            for stock in stock_location:
                if location_id.id == stock.location_id.id:
                    stock_location = stock
        return stock_location

    @api.depends('inventory_quantity')
    def _compute_s_inventory_quantity(self):
        for quant in self:
            quant.s_inventory_quantity = 0
            if quant.inventory_quantity != 0:
                quant.s_inventory_quantity = quant.inventory_quantity

    def _get_quants_action(self, domain=None, extend=False):
        res = super(StockQuant, self)._get_quants_action(extend=extend)
        # Load lại page không sử dụng view dashboard_open_quants
        res.update({
            'id': False
        })
        # Load lại page không sử dụng view dashboard_open_quants
        return res
