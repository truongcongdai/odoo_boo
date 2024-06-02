from odoo import fields, models, api, _


class SProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    def _is_from_single_value_line(self, only_active=True):
        res = super(SProductTemplateAttributeValue, self)._is_from_single_value_line(only_active=True)
        attribute_value = self.ptav_product_variant_ids.product_template_attribute_value_ids
        if attribute_value:
            attribute_line_value = attribute_value.product_attribute_value_id
            if len(attribute_line_value) > 1:
                return False
        return res
