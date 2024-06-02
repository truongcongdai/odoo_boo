from odoo import fields, models, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    # ['|', ('warehouse_id.employee_ids', 'in', user.employee_ids.ids), ('create_uid', '=', user.id)]

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        res = super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        if self.env.user.has_group('advanced_sale.s_boo_group_thu_ngan'):
        #     domain += [()]
            new_res = []
            for rec in res:
                warehouse_ids = self.env.user.boo_warehouse_ids.ids
                x = 0
                if 'warehouse_id' in rec:
                    if len(rec['warehouse_id']) > 0:
                        if rec['warehouse_id'][0] in warehouse_ids:
                            new_res.append(rec)
                    x += 1
            res = new_res
            return res
        return res