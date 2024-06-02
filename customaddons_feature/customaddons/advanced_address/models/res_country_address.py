from odoo import _, api, fields, models
from odoo.addons.http_routing.models.ir_http import slugify


class ResCountryAddress(models.Model):
    _name = 'res.country.address'
    _description = 'Country Address'
    _rec_name = 'name_with_type'
    _order = 'type, name, id DESC'

    name = fields.Char(
        string='Name',
    )
    slug_name = fields.Char(
        string='Slug Name',
        compute='_compute_name',
        store=True
    )
    code = fields.Char(
        string='Code',
    )
    name_with_type = fields.Char(
        string='Name With Type',
        compute='_compute_name',
        store=True
    )
    type = fields.Selection(
        selection=[
            ('1_province', 'Tỉnh'),
            ('1_city', 'Thành phố'),
            ('2_province_district', 'Huyện'),
            ('2_province_town', 'Thị xã'),
            ('2_province_city', 'Thành phố trực thuộc'),
            ('2_city_district', 'Quận'),
            ('3_province_village', 'Xã'),
            ('3_province_burgh', 'Thị trấn'),
            ('3_city_block', 'Phường'),
        ],
        string='Address Type',
    )
    state_id = fields.Many2one(
        comodel_name='res.country.state'
    )
    parent_id = fields.Many2one(
        comodel_name='res.country.address',
        copy=False,
        ondelete='restrict'
    )
    country_id = fields.Many2one(
        comodel_name='res.country',
        copy=False,
        ondelete='restrict'
    )
    full_name = fields.Char(
        string='Full Name',
        compute='_compute_name',
        store=True
    )
    full_name_with_type = fields.Char(
        string='Full Name With Type',
        compute='_compute_name',
        store=True
    )

    _sql_constraints = [
        (
            'code_country_uniq',
            'UNIQUE(code, country_id)',
            'Code should be unique per country!'
        )
    ]

    @api.depends('name', 'type', 'parent_id')
    def _compute_name(self):
        type_field = self.env.ref('advanced_address.field_res_country_address__type')
        for r in self:
            convert = type_field.selection_ids.filtered(lambda rec: rec.value == r.type).name
            r.slug_name = slugify(r.name)
            r.name_with_type = f'{convert} {r.name}'
            if not r.parent_id:
                r.full_name_with_type = r.name_with_type
                r.full_name = r.name
            else:
                r.full_name_with_type = f'{r.name_with_type}, {r.parent_id.full_name_with_type}'
                r.full_name = f'{r.name}, {r.parent_id.name}'
