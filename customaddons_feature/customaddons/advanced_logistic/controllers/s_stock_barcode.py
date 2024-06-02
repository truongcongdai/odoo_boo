from collections import defaultdict

from odoo import http, _
from odoo.http import request
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController


class CustomStockBarcodeController(StockBarcodeController):

    def _try_open_picking(self, barcode):
        """ If barcode represents a picking, open it
        """
        # You can modify the function as needed here
        corresponding_picking = request.env['stock.picking'].search([
            ('name', '=', barcode),
        ], limit=1)
        if corresponding_picking:
            action = corresponding_picking.action_open_picking_client_action()
            return {'action': action}
        else:
            corresponding_picking_by_logistic_barcode = request.env['stock.picking'].search([
            ('logistic_barcode', '=', barcode),
        ], limit=1)
            if corresponding_picking_by_logistic_barcode:
                action = corresponding_picking_by_logistic_barcode.action_open_picking_client_action()
                return {'action': action}
        return False