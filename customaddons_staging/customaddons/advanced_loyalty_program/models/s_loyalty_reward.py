from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SAdvancedLoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    reward_type = fields.Selection(selection_add=[('point', 'Quy đổi điểm')], ondelete={'point': 'set default'})
    s_reward_exchange_point = fields.Integer(string='Điểm quy đổi', default=1,
                                             help='Điền tỷ lệ điểm quy đổi thành tiền để chiết khấu trên đơn hàng')
    s_reward_exchange_monetary = fields.Integer(string='Tiền quy đổi', default=1)
    s_exchange_product = fields.Many2one(comodel_name='product.product', string='Sản phẩm quy đổi',
                                         help='Chọn sản phẩm quy đổi điểm tương ứng để thể hiện trên đơn hàng')
    s_exchange_maximum = fields.Integer(string='Quy đổi tối đa', default=1)
    s_type_exchange = fields.Selection([('number', 'Điểm/đơn hàng'), ('percent', '% Điểm/đơn hàng')],
                                       string='Loại quy đổi', default='number',
                                       help='Chọn số điểm hoặc % điểm quy đổi tối đa trên đơn hàng')

    @api.constrains('s_exchange_maximum')
    def _constrains_s_exchange_maximum(self):
        for rec in self:
            if rec.reward_type == 'point':
                if rec.s_type_exchange == 'percent':
                    if rec.s_exchange_maximum > 100:
                        raise ValidationError('Điểm trên đơn hàng thiết lập giá trị quá 100%')
                    if rec.s_exchange_maximum == 0:
                        raise ValidationError('Chưa thiết lập quy đổi tối đa')
                else:
                    if rec.s_exchange_maximum < rec.s_reward_exchange_point:
                        raise ValidationError('Quy đổi tối đa không được nhỏ hơn điểm quy đổi')
                    if rec.s_exchange_maximum == 0:
                        raise ValidationError('Phần thưởng %s chưa thiết lập điểm quy đổi tối đa' % rec.name)

    @api.onchange('s_reward_exchange_monetary')
    def _onchange_s_reward_exchange_monetary(self):
        for rec in self:
            if rec.reward_type == 'point':
                if rec.s_reward_exchange_monetary <= 0:
                    raise ValidationError('Phần thưởng %s chưa thiết lập tiền quy đổi' % rec.name)

    @api.onchange('s_reward_exchange_point')
    def _onchange_s_reward_exchange_point(self):
        for rec in self:
            if rec.reward_type == 'point':
                if rec.s_reward_exchange_point <= 0:
                    raise ValidationError('Phần thưởng %s chưa thiết lập tiền quy đổi' % rec.name)

    @api.onchange('discount_percentage')
    def _onchange_discount_percentage(self):
        for rec in self:
            if rec.reward_type == 'discount' and rec.discount_type == 'percentage':
                if rec.discount_percentage > 100:
                    raise ValidationError('Áp dụng chiết khấu % không được phép điền giá trị quá 100%')

    @api.onchange('s_type_exchange')
    def _onchange_s_type_exchange(self):
        for rec in self:
            rec.s_exchange_maximum = 1
