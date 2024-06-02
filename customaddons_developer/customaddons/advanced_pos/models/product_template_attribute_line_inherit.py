from odoo import fields, models, api


class ProductTemplateAttributeLineInherit(models.Model):
    _inherit = 'product.template.attribute.line'

    value_ids_related = fields.Many2many(string="Values", related="value_ids")

    def action_add_variant_product_template(self):
        view_id = self.env.ref('advanced_pos.add_variant_product_template_view_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': "Thêm biến thể cho sản phẩm",
            'res_model': 'product.template.attribute.line',
            'target': 'new',
            'view_mode': 'form',
            'view_id': view_id,
            'domain': [('id', '=', self.product_template_value_ids.ids)],
            'context': {
                'default_product_tmpl_id': self.product_tmpl_id.id,
                'default_attribute_id': self.attribute_id.id,
            },
        }

    def action_submit_add_variant(self):
        attribute_id = self.attribute_id
        product_tmpl_id = self.product_tmpl_id
        product_attribute_value = self.value_ids
        product_attribute_line = self.id

        attribute_line_new = self.product_tmpl_id.attribute_line_ids.search([('id', '=', product_attribute_line)])
        if attribute_line_new:
            attribute_line_new.sudo().unlink()

        attribute_line_old = self.search([('product_tmpl_id', '=', product_tmpl_id.id), ('attribute_id', '=', attribute_id.id)])
        if attribute_line_old and product_attribute_value:
            attribute_line_old.value_ids += product_attribute_value

    @api.onchange('value_ids_related')
    def _onchange_value_ids_related(self):
        if len(self.value_ids_related) >= 0:
            self.value_ids = self.value_ids_related
