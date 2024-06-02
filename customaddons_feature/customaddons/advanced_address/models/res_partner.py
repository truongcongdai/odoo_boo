from odoo import _, api, fields, models


class Partner(models.Model):
    _inherit = ['res.partner']

    ward_id = fields.Many2one(
        comodel_name='res.country.address',
        string='Phường',
        domain=[('type', 'like', '3')],
        tracking=True
    )
    district_id = fields.Many2one(
        comodel_name='res.country.address',
        related='ward_id.parent_id',
        store=True,
        readonly=False,
        string='Quận',
        domain=[('type', 'like', '2')]
    )
    city_id = fields.Many2one(
        comodel_name='res.country.address',
        related='district_id.parent_id',
        store=True,
        readonly=False,
        string='Thành phố',
        domain=[('type', 'like', '1')]
    )
    city_state_id = fields.Many2one(
        comodel_name='res.country.state',
        related='city_id.state_id'
    )
    ward_country_id = fields.Many2one(
        comodel_name='res.country',
        related='ward_id.country_id'
    )

    @api.onchange('ward_id')
    def _onchange_ward(self):
        self.update({
            'city': self.ward_id.parent_id.parent_id.name_with_type,
            'state_id': self.ward_id.parent_id.parent_id.state_id.id if self.ward_id.parent_id.parent_id.state_id.id else self.ward_id.parent_id.state_id.id,
        })

    @api.onchange('district_id')
    def _onchange_ward_id(self):
        district = self.district_id
        if district:
            return {'domain': {'ward_id': [('parent_id.name', '=', district.name)]}}

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template Khách hàng',
            'template': '/advanced_address/static/xlsx/template_import_khach_hang .xlsx'
        }]

    def update_customer_adddress(self):
        for r in self:
            if not r.district_id and r.district:
                district_id = self.env['res.country.address'].sudo().search(['|', '|', ('name', 'ilike', r.district),
                                                                             ('name_with_type', 'ilike', r.district),
                                                                             ('name', 'ilike', r.district.strip('Thành phố')),
                                                                             ('parent_id', '!=', None)], limit=1)
                if district_id:
                    r.write({
                        'district_id': district_id.id
                    })
                    if not r.state_id:
                        if r.district_id.parent_id.name:
                            state_id = self.env['res.country.state'].sudo().search(
                                [('name', 'ilike', r.district_id.parent_id.name)], limit=1)
                            if state_id:
                                r.write({
                                    'state_id': state_id.id
                                })
            if not r.state_id and r.city:
                state_id = self.env['res.country.state'].sudo().search([('name', 'ilike', r.city)], limit=1)
                if state_id:
                    r.write({
                        'state_id': state_id.id
                    })

            if not r.country_id and r.state_id:
                if r.state_id.country_id:
                    r.write({
                        'country_id': r.state_id.country_id.id
                    })

