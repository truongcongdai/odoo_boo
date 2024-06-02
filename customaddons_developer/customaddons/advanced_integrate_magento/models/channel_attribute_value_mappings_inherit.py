from odoo import fields, models, api


class channelAttributeValueMappingsInherit(models.Model):
    _inherit = 'channel.attribute.value.mappings'
    attribute_value_code = fields.Char(string='Odoo Attribute Value Code', related="attribute_value_name.code",store=True)
