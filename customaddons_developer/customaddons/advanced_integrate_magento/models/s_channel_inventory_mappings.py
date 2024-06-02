from odoo import fields, models

class ChannelInventoryMappings(models.TransientModel):
    _name = 's.channel.inventory.mappings'
    _inherit = 'channel.mappings'
    _description = 'Inventory Mappings'

    code = fields.Char('Short Name')
    partner_id = fields.Many2one('res.partner', 'Address')

    def _compute_name(self):
        for r in self:
            r.name = r.partner_id and r.partner_id.name or 'Deleted'
