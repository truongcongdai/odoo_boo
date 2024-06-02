from odoo import api, models


class ExportMagento2xAttributes(models.TransientModel):
    _inherit = ['export.attributes.magento']

    @api.model
    def magento2x_get_attribute_value(self, attribute_id, channel_id):
        # since super function creates a list of dictionary with label as the only key
        # calling it ensure everything works fine!
        super(ExportMagento2xAttributes, self).magento2x_get_attribute_value(attribute_id, channel_id)
        res = []
        value_mappings = channel_id.match_attribute_value_mappings(limit=None)
        domain = [
            ('attribute_id', '=', attribute_id.id),
            ('id', 'not in', value_mappings.mapped('odoo_attribute_value_id'))
        ]
        for value in self.env['product.attribute.value'].search(domain):
            if attribute_id.type == 'color':
                if value.code:
                    # res.append({
                    #     'label': value.name,
                    #     'value': '#' + str(value.code) if value.code else '',
                    # })
                    res.append({
                        'label': str(value.code) if value.code else '',
                        'value': '#' + str(value.code) if value.code else '',
                        "store_labels": [
                            {
                                "store_id": 1,
                                "label": value.name
                            }
                        ]
                    })
            else:
                # res.append({
                #     'label': value.name,
                # })
                res.append({
                    'label': value.name,
                    'value': '',
                    "store_labels": [
                        {
                            "store_id": 1,
                            "label": value.name
                        }
                    ]
                })
        return res
