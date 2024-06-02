from odoo import fields, models, api


class SAccountBankStatement(models.Model):
    _name = 's.account.bank.statement'

    name = fields.Char()
    payment_method_id = fields.Many2one('pos.payment.method', string='Phương thức thanh toán', required=True)
    payment_note = fields.Char(string="Ghi chú thanh toán")
    amount = fields.Float('Tổng tiền thanh toán')
    payment_status = fields.Char('Trạng thái thanh toán')
    ticket = fields.Char('Payment Receipt Info')
    card_type = fields.Char('Type of card used')
    cardholder_name = fields.Char('Cardholder Name')
    transaction_id = fields.Char('Payment Transaction ID')

    s_account_bank_statement_id = fields.Many2one('s.lost.bill')


class SLostBill(models.Model):
    _name = 's.lost.bill'
    _description = 'Lost Bill'

    name = fields.Char('Đơn hàng')
    amount_paid = fields.Float('Thanh toán')
    amount_total = fields.Integer('Thành tiền')
    amount_tax = fields.Integer('Tổng thuế')
    amount_return = fields.Integer('Tiền trả lại')
    creation_date = fields.Char('Ngày tạo')

    sale_person_id = fields.Many2one('hr.employee', string='Nhân viên bán hàng')
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    employee_id = fields.Many2one('hr.employee', string='Thu ngân')
    pos_session_id = fields.Many2one('pos.session', string='Phiên')
    pricelist_id = fields.Many2one('product.pricelist', string='Bảng giá')
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string='Vị trí tài chính',
    )
    to_invoice = fields.Boolean()
    to_ship = fields.Boolean()
    is_tipped = fields.Boolean()
    tip_amount = fields.Float()
    loyalty_points = fields.Float()
    lines = fields.One2many('s.lost.bill.pos.order.line', 'logging_lost_bill_pos_order_id', string='Order Lines', readonly=True, copy=True)
    statement_ids = fields.One2many('s.account.bank.statement', 's_account_bank_statement_id', string='Cash Statements', readonly=True)
    state = fields.Selection([
        ('order_da_tao', 'Đơn hàng đã tạo'),
        ('order_loi', 'Đơn hàng lỗi'),
        ('order_da_ton_tai', 'Đơn hàng đã tồn tại'),
        ('order_can_kiem_tra_lai', 'Đơn hàng cần kiểm tra lại')
    ], string='Tình trạng đơn hàng', default='order_loi')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(SLostBill, self).fields_get(allfields, attributes)
        hide_list = ['partner_id']
        user = self.env.user
        user_group_has_access = [user.has_group('advanced_sale.s_boo_group_administration'),
                                 user.has_group('advanced_sale.s_boo_group_area_manager'),
                                 user.has_group('advanced_sale.s_boo_group_ecom')]
        user_group_thu_ngan = user.has_group('advanced_sale.s_boo_group_thu_ngan')
        if user_group_thu_ngan and not any(user_group_has_access):
            for field in hide_list:
                if res.get(field):
                    res[field]['exportable'] = False
        return res
