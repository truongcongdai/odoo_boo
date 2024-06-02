from odoo import fields, models, api


class ProductCouponProgram(models.Model):
    _name = 's.product.coupon.program'
    _description = 'Product Coupon Program'
    _order = 'product_id, coupon_id, id desc'

    product_id = fields.Many2one(
        comodel_name='product.product',
        ondelete='cascade',
        string='Product'
    )
    coupon_id = fields.Many2one(
        comodel_name='coupon.program',
        required=True,
        ondelete='restrict',
        string='Chương Trình'
    )
    pos_config_ids = fields.Many2many(
        comodel_name='pos.config', compute="_compute_pos_config",
        string='Cửa Hàng Áp Dụng'
    )
    description = fields.Char(
        string='Nội Dung',
        related='coupon_id.description',
    )

    # _sql_constraints = [
    #     (
    #         'coupon_id_product_id_unique',
    #         'UNIQUE(coupon_id, product_id)',
    #         'You should not add a promotion program into product twice!'
    #     )
    # ]
    def _compute_pos_config(self):
        for rec in self:
            if rec.sudo().coupon_id:
                rec.sudo().write({
                    'pos_config_ids': [(6, 0, rec.coupon_id.pos_config_ids.ids)]
                })
