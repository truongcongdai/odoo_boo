from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AdvancedGiftCard(models.Model):
    _inherit = 'gift.card'

    discount_percentage = fields.Integer(
        string='Giảm giá mặc định (%)')
    discount_amount = fields.Monetary(
        string='Giảm giá mặc định', currency_field='currency_id')
    code = fields.Char(default=False, copy=False, readonly=False)
    discount_type = fields.Selection([('percentage', 'Phần trăm'), ('discount_amount', 'Số tiền')], default='percentage')
    is_not_calculate_amount = fields.Boolean(string='Gift Card không trừ doanh thu', default=False)
    pos_payment_ids = fields.One2many('pos.payment', 's_gift_card_id', string='Phương thức thanh toán')
    active = fields.Boolean(string='Kích hoạt', default=True)
    is_used_gift_card = fields.Boolean(string='Đã được sử dụng', default=False)
    is_gift_card_discard = fields.Boolean(string='Gift Card Discard', default=False)

    @api.constrains('code', 'state')
    def _check_state_code(self):
        valid_codes = self.search([('state', '=', 'valid')]).mapped('code')
        for gift_card in self.filtered(lambda gc: gc.state == 'valid'):
            if valid_codes.count(gift_card.code) > 1:
                raise ValidationError(_('Can not create 2 valid gift-cards with a same code!'))

    _sql_constraints = [
        ('unique_gift_card_code', 'UNIQUE(code,state)', 'The gift card code must be unique.'),
        ('check_amount', 'CHECK(initial_amount >= 0)', 'The initial amount must be positive.')
    ]

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template Giftcard',
            'template': '/advanced_pos/static/xlsx/template_import_giftcard.xlsx'
        }]

    @api.onchange('expired_date')
    def _onchange_expired_date(self):
        if self.expired_date:
            if self.expired_date > fields.Date.today():
                self.state = 'valid'
            else:
                self.state = 'expired'

    def update_status(self):
        for rec in self:
            if rec.expired_date:
                if rec.expired_date > fields.Date.today():
                    rec.state = 'valid'
                else:
                    rec.state = 'expired'
