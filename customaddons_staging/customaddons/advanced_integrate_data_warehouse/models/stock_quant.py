from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockQuant(models.Model):
    _inherit = ['stock.quant']
    check_stock_compute = fields.Boolean(default=False)

    @api.model
    def create(self, vals):
        res = super(StockQuant, self).create(vals)
        if 'location_id' in vals.keys() and 'product_id' in vals.keys():
            stock_location = self.env['stock.location'].sudo().search([('id', '=', vals.get('location_id'))], limit=1)
            if stock_location.usage == 'internal' and not stock_location.s_is_transit_location and not stock_location.scrap_location:
                s_stock_quant_id = self.env['s.stock.quant'].sudo().search([
                    ('product_id', '=', vals.get('product_id')), ('location_id', '=', vals.get('location_id'))], limit=1)
                if not s_stock_quant_id:
                    self.env['s.stock.quant'].sudo().create(vals)
                else:
                    s_stock_quant_id.sudo().write(vals)
        return res

    def write(self, vals):
        res = super(StockQuant, self).write(vals)
        for r in self:
            if r.location_id.usage == 'internal' and not r.location_id.s_is_transit_location and not r.location_id.scrap_location:
                s_stock_quant_id = self.env['s.stock.quant'].sudo().search([
                    ('product_id', '=', r.product_id.id), ('location_id', '=', r.location_id.id)], limit=1)
                if s_stock_quant_id:
                    s_stock_quant_id.sudo().write(vals)
                else:
                    self.env['s.stock.quant'].sudo().create({
                        'accounting_date': r.accounting_date,
                        'inventory_date': r.inventory_date,
                        'inventory_quantity': r.inventory_quantity,
                        'inventory_quantity_set': r.inventory_quantity_set,
                        'location_id': r.location_id.id if r.location_id else False,
                        'lot_id': r.lot_id.id if r.lot_id else False,
                        'owner_id': r.owner_id.id if r.owner_id else False,
                        'package_id': r.package_id.id if r.package_id else False,
                        'product_id': r.product_id.id if r.product_id else False,
                        'user_id': r.user_id.id if r.user_id else False
                    })
        return res

    def unlink(self):
        for r in self:
            if r.location_id.usage == 'internal' and not r.location_id.s_is_transit_location and not r.location_id.scrap_location:
                s_stock_quant_id = self.env['s.stock.quant'].sudo().search([
                    ('product_id', '=', r.product_id.id), ('location_id', '=', r.location_id.id)], limit=1)
                if s_stock_quant_id:
                    s_stock_quant_id.sudo().write({
                        'inventory_quantity': 0,
                        'inventory_diff_quantity': 0,
                        'reserved_quantity': 0,
                        'quantity': 0,
                        'in_date': r.in_date
                    })
        return super(StockQuant, self).unlink()

    def cron_compute_stock_quant_to_s_stock_quant(self):
        stock_quant_ids = self.sudo().search([('check_stock_compute', '=', False)])
        s_stock_quant_obj = self.env['s.stock.quant'].sudo()
        for stock_quant_id in stock_quant_ids:
            if stock_quant_id.location_id.usage == 'internal' and not stock_quant_id.location_id.s_is_transit_location and not stock_quant_id.location_id.scrap_location:
                s_stock_quant_id = s_stock_quant_obj.search([('product_id', '=', stock_quant_id.product_id.id),
                    ('location_id', '=', stock_quant_id.location_id.id)], limit=1)
                if s_stock_quant_id:
                    s_stock_quant_id.unlink()
                vals = stock_quant_id.read(['quantity', 'reserved_quantity', 'in_date', 'inventory_quantity',
                    'inventory_diff_quantity', 'inventory_date', 'inventory_quantity_set', 'user_id'
                ])[0]
                vals.update({
                    'product_id': stock_quant_id.read(['product_id'])[0].get('product_id')[0],
                    'location_id': stock_quant_id.read(['location_id'])[0].get('location_id')[0]
                })
                if stock_quant_id.read(['user_id']) and stock_quant_id.read(['user_id'])[0].get('user_id'):
                    vals.update({
                        'user_id': stock_quant_id.read(['user_id'])[0].get('user_id')[0]
                    })
                s_stock_quant_obj.create(vals)
                self._cr.execute(
                    """UPDATE stock_quant SET check_stock_compute = True WHERE id = %s""", (stock_quant_id.id,))

    def cron_update_s_stock_quant(self):
        stock_quant_ids = self.sudo().search([('check_stock_compute', '=', False),
                                              ('location_id.usage', '=', 'internal'),
                                              ('location_id.s_is_transit_location', '=', False),
                                              ('location_id.scrap_location', '=', False)])
        s_stock_quant_obj = self.env['s.stock.quant'].sudo()
        for stock_quant_id in stock_quant_ids:
            s_stock_quant_id = s_stock_quant_obj.search([('product_id', '=', stock_quant_id.product_id.id),
                                                         ('location_id', '=', stock_quant_id.location_id.id)],
                                                        limit=1)
            vals = stock_quant_id.read(['quantity', 'reserved_quantity', 'in_date', 'inventory_quantity',
                                        'inventory_diff_quantity', 'inventory_date', 'inventory_quantity_set',
                                        'user_id'
                                        ])[0]
            vals.update({
                'product_id': stock_quant_id.read(['product_id'])[0].get('product_id')[0],
                'location_id': stock_quant_id.read(['location_id'])[0].get('location_id')[0]
            })
            if stock_quant_id.read(['user_id']) and stock_quant_id.read(['user_id'])[0].get('user_id'):
                vals.update({
                    'user_id': stock_quant_id.read(['user_id'])[0].get('user_id')[0]
                })
            if not s_stock_quant_id:
                s_stock_quant_obj.create(vals)
                self._cr.execute(
                    """UPDATE stock_quant SET check_stock_compute = True WHERE id = %s""", (stock_quant_id.id,))
            if s_stock_quant_id and (s_stock_quant_id.quantity != stock_quant_id.quantity or
                                     s_stock_quant_id.reserved_quantity != stock_quant_id.reserved_quantity or
                                     s_stock_quant_id.inventory_quantity != stock_quant_id.inventory_quantity):
                s_stock_quant_id.unlink()
                s_stock_quant_obj.create(vals)
                self._cr.execute(
                    """UPDATE stock_quant SET check_stock_compute = True WHERE id = %s""", (stock_quant_id.id,))

    def cron_delete_s_stock_quant_is_duplicate(self):
        s_stock_quant_ids = self.env['s.stock.quant'].sudo().search([('create_date', '>=', '30/06/2023')])
        for s_stock_quant_id in s_stock_quant_ids:
            s_stock_quant_id.sudo().unlink()
        stock_quant_ids = self.sudo().search([('check_stock_compute', '=', True)])
        if stock_quant_ids:
            for stock_quant_id in stock_quant_ids:
                self._cr.execute(
                    """UPDATE stock_quant SET check_stock_compute = False WHERE id = %s""", (stock_quant_id.id,))
        self.cron_update_s_stock_quant()