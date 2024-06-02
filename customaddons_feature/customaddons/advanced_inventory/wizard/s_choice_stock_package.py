from odoo import fields, models, api
from odoo.exceptions import UserError


class SChoiceStockPackage(models.TransientModel):
    _name = 's.choice.stock.package'
    _description = 'Description'

    package_id = fields.Many2one('s.stock.picking.package', string='Kiện hàng')
    stock_picking_id = fields.Many2many('stock.picking')
    stock_picking_package = fields.Many2many('s.stock.picking.package')
    move_ids_without_package_id = fields.Many2one('stock.move')

    def action_add_to_stock_package(self):
        # Lấy product trong kiện hàng
        product_lines_ids = self.env['s.stock.picking.package.line'].sudo().search(
            [('package_id', 'in', self.stock_picking_id.stock_package_ids.ids),
             ('move_ids_without_package_id', '=', self.move_ids_without_package_id.id),
             ])

        if self.move_ids_without_package_id.product_uom_qty > self.move_ids_without_package_id.quantity_done: # Kiểm tra số lượng nhập vào có lớn hơn số lượng nhập vào không
            if self.package_id.product_lines_ids and product_lines_ids:

                for product in self.package_id.product_lines_ids:
                    if self.move_ids_without_package_id.id == product.move_ids_without_package_id.id:
                        qty = self.move_ids_without_package_id.product_uom_qty - self.move_ids_without_package_id.quantity_done
                        product.qty = qty
                    else:
                        for product_line in product_lines_ids:
                            # self.move_ids_without_package_id.quantity_done = product_line.qty # Cập nhật số lượng hoàn thành
                            if self.move_ids_without_package_id.id == product_line.move_ids_without_package_id.id:
                                qty = self.move_ids_without_package_id.product_uom_qty - self.move_ids_without_package_id.quantity_done
                            else:
                                qty = 0
                        if product_line.move_ids_without_package_id.quantity_done  < self.move_ids_without_package_id.product_uom_qty: # Kiểm tra số lượng nhập vào trong kiện hàng

                            # qty = self.move_ids_without_package_id.product_uom_qty - product_line.qty

                            qty_done =  self.move_ids_without_package_id.quantity_done + qty
                            self.move_ids_without_package_id.sudo().write({
                                'stock_package_ids': [(4, self.package_id.id)],
                                'quantity_done': qty_done,
                            })
                            self.package_id.sudo().write({
                                'product_lines_ids': [(0, 0, {
                                    'product_id': self.move_ids_without_package_id.product_id.id,
                                    'qty': qty,
                                    'qty_missing':qty,
                                    'uom_qty': self.move_ids_without_package_id.product_uom_qty,
                                    'move_ids_without_package_id': self.move_ids_without_package_id.id,
                                })],
                                'stock_picking_id': [self.stock_picking_id.id],
                            })
                        else:
                            raise UserError(f'Đơn hàng đã có trong kiện hàng')
            else:
                qty = self.move_ids_without_package_id.product_uom_qty - self.move_ids_without_package_id.quantity_done
                if qty:
                    self.move_ids_without_package_id.sudo().write({
                        'stock_package_ids': [(4, self.package_id.id)],
                    })
                    self.package_id.sudo().write({
                        'product_lines_ids': [(0, 0, {
                            'product_id': self.move_ids_without_package_id.product_id.id,
                            'qty': qty,
                            'qty_missing': qty,
                            'uom_qty': self.move_ids_without_package_id.product_uom_qty,
                            'move_ids_without_package_id': self.move_ids_without_package_id.id,
                        })],
                        'stock_picking_id': [self.stock_picking_id.id],
                    })
                    self.move_ids_without_package_id.sudo().write({
                        'quantity_done': self.move_ids_without_package_id.product_uom_qty,
                    })
                else:
                    raise UserError(f'Số lượng đã xuất không đủ để thêm vào kiện hàng: {self.package_id.name}')

        else:
            raise UserError(f'Số lượng đã xuất không đủ để thêm vào kiện hàng: {self.package_id.name}')
