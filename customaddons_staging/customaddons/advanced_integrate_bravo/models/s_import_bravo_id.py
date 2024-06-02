from odoo import fields, models, api


class ImportBravoId(models.Model):
    _name = 's.import.bravo.id'

    name = fields.Char()
    s_product_sku = fields.Char(string='SKU')
    s_model = fields.Char(string='Models')
    s_bravo_id = fields.Integer(string='Bravo ID')
    s_odoo_id = fields.Integer(string='Odoo ID')

    def s_import_product_bravo_id(self):
        for rec in self:
            if rec.s_model == 'product.product':
                if rec.s_product_sku and rec.s_bravo_id:
                    product = self.env['product.product'].sudo().search([('default_code', '=', rec.s_product_sku)],
                                                                        limit=1)
                    if product:
                        product.sudo().write({
                            'bravo_system_child_id': rec.s_bravo_id
                        })
            elif rec.s_model == 'product.attribute':
                if rec.s_odoo_id and rec.s_bravo_id:
                    attribute = self.env['product.attribute'].sudo().search([('id', '=', rec.s_odoo_id)],
                                                                            limit=1)
                    if attribute:
                        attribute.sudo().write({
                            'bravo_id': rec.s_bravo_id
                        })
            elif rec.s_model == 'product.category':
                if rec.s_odoo_id and rec.s_bravo_id:
                    categ = self.env['product.category'].sudo().search([('id', '=', rec.s_odoo_id)],
                                                                       limit=1)
                    if categ:
                        categ.sudo().write({
                            'bravo_id': rec.s_bravo_id
                        })
            rec.sudo().unlink()
