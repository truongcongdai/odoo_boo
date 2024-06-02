from odoo import fields, models, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    _rec_name = 's_complete_name'
    s_code = fields.Char(string='Mã kho', store=True)
    s_is_transit_location = fields.Boolean(string='Là kho đi trên đường')
    s_transit_location_id = fields.Many2one('stock.location', string='Kho đi trên đường')
    warehouse_id_store = fields.Many2one('stock.warehouse', related='warehouse_id', store=True)
    s_complete_name = fields.Char("Full Location Name", compute='_compute_s_complete_name', store=True)
    _sql_constraints = [
        (
            'code_location_uniq',
            'UNIQUE(s_code)',
            'Mã địa điểm kho phải là duy nhất!'
        )]

    # def name_get(self):
    #     warehouse_location = []
    #     for rec in self:
    #         if rec.s_code:
    #             warehouse_location.append((rec.id, "[%s] %s" % (rec.s_code, rec.s_complete_name)))
    #         else:
    #             warehouse_location.append((rec.id, "%s" % (rec.s_complete_name)))
    #     return warehouse_location

    @api.depends('name', 'warehouse_id.name', 'usage')
    def _compute_s_complete_name(self):
        for location in self:
            location.s_complete_name = location.name
            if location.location_id and location.usage != 'view':
                if location.warehouse_id.name:
                    location.s_complete_name = '%s/%s' % (location.warehouse_id.name, location.name)
            else:
                location.s_complete_name = location.name
