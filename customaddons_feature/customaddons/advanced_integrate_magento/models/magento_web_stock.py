from odoo import _, api, fields, models


class MagentoWebStock(models.Model):
    _name = 'magento.web.stock'
    _inherit = ['mail.thread']
    _description = 'M2 Website Stock'

    name = fields.Char(
        string='External Website Stock',
        required=True,
        tracking=True,
        default='Main Website'
    )
    external_id = fields.Char(
        string='External System ID',
        default=1,
        required=True,
        copy=False,
        tracking=True
    )
    full_name = fields.Char(
        string='Full Name',
        compute='_compute_full_name',
        store=True
    )
    channel_id = fields.Many2one(
        comodel_name='multi.channel.sale',
        string='Channel',
        required=True,
        default=lambda self: self._get_default_channel(),
        ondelete='cascade',
        copy=False,
        tracking=True
    )
    warehouse_ids = fields.Many2many(
        comodel_name='stock.warehouse',
        relation='warehouse_magento_stock_rel',
        column1='magento_stock_id',
        column2='warehouse_id',
        string='Warehouses',
        domain=[('status_stock_warehouse', '=', True)]
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('sync', 'Synchronized')
        ],
        string='Status',
        required=True,
        default='draft',
        copy=False
    )

    _sql_constraints = [
        (
            'channel_external_id_uniq',
            'UNIQUE(external_id, channel_id)',
            'External ID should be unique each channel!'
        )
    ]

    @api.depends('external_id', 'channel_id', 'channel_id.name', 'name')
    def _compute_full_name(self):
        for r in self:
            r.full_name = f'[{r.external_id}] {r.channel_id.name.title()} {r.name}'

    @api.model
    def _get_default_channel(self):
        return self.env.ref('magento2x_odoo_bridge.magento2x_channel').id

    def action_push_external(self):
        self.ensure_one()
        self.warehouse_ids.magento_create_source()
        self.warehouse_ids.magento_assign_source_to_stock(self.external_id)
        if self.state != 'sync':
            return self.write({'state': 'sync'})
        return True

    @api.model
    def cron_synchronizing_stock(self):
        records = self.search([])
        for r in records:
            r.action_push_external()
