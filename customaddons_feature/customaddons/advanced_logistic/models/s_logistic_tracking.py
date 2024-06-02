from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class SLogisticApp(models.Model):
    _name = 's.logistic.tracking'
    _rec_name = 's_transfer_out_id'

    s_internal_transfer_id = fields.Many2one('s.internal.transfer', string='Điều chuyển')
    s_transfer_out_id = fields.Many2one('stock.picking', string='Mã phiếu xuất')
    s_transfer_in_id = fields.Many2one('stock.picking', string='Mã phiếu Nhập')
    s_location_out_id = fields.Many2one('stock.location', string='Kho xuất hàng')
    s_location_in_id = fields.Many2one('stock.location', string='Kho nhập hàng')
    s_location_transfer_in_id = fields.Many2one('stock.location', string='Kho nhập hàng')
    s_transfer_quantity = fields.Integer(string='Số lượng')
    s_date_out = fields.Datetime(string='Ngày xuất', related='s_transfer_out_id.date_done')
    s_date_in = fields.Datetime(string='Ngày nhận hàng', readonly=True)
    s_complete_date = fields.Datetime(string='Ngày hoàn thành', readonly=True)
    s_receiver = fields.Many2one('hr.employee', string='Người nhận')
    s_sla = fields.Char('SLA(hh:mm)', compute='_compute_sla_time', store=True,
                        help='Tổng thời gian tính từ lúc hoàn thành phiếu xuất đến khi scan barcode lần 2 (hh:mm)')
    s_state = fields.Selection([('received', 'Đã nhận hàng'), ('delivered', 'Đã giao hàng thành công')],
                               string='Trạng thái')
    s_delivery_time = fields.Float(string='Thời gian giao nhận', compute='_compute_delivery_time', store=True,
                                     help='Chênh lệch thời gian giữa 2 lần scan barcode')
    s_code = fields.Char(string='Mã điều chuyển', related='s_internal_transfer_id.code', store=True)
    s_total_time = fields.Float(string='Tổng thời gian', related='s_internal_transfer_id.s_total_time_transfer',
                                  store=True)

    @api.depends('s_complete_date')
    def _compute_delivery_time(self):
        for rec in self:
            rec.s_delivery_time = 0
            if rec.s_date_in and rec.s_complete_date:
                calculate_timedelta = (rec.s_complete_date - rec.s_date_in)
                days = calculate_timedelta.days
                hours, remainder = divmod(calculate_timedelta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                hours += days * 24
                rec.s_delivery_time = int(hours) + minutes/60

    @api.depends('s_complete_date', 's_date_out')
    def _compute_sla_time(self):
        for rec in self:
            if rec.s_date_out and rec.s_complete_date:
                calculate_timedelta = (rec.s_complete_date - rec.s_date_out)
                days = calculate_timedelta.days
                hours, remainder = divmod(calculate_timedelta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                hours += days * 24
                rec.s_sla = str(hours) + ':' + str(minutes)

    def action_apply_s_logistic_tracking(self):
        view = self.env.ref('advanced_logistic.logistic_infor_receiver_type_form_view')
        for rec in self:
            if rec.s_date_in and not rec.s_complete_date and rec.s_state != 'received':
                rec.sudo().write({
                    's_state': 'received'
                })
            if rec.s_date_in and rec.s_complete_date and rec.s_state != 'delivered':
                return {
                    'name': _('Người Nhận Hàng'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'logistic.mass.action.infor.receiver',
                    'views': [(view.id, 'form')],
                    'target': 'new',
                    'context': {'defaults_s_logistic_ids': self.id}
                }


        # for rec in self:
        #     if not rec.s_receiver and rec.s_state == 'received':
        #         raise ValidationError('Vui lòng nhập người nhận hàng!')

    def action_logistics_view(self):
        return {
            'name': 'Logistics Tracking',
            'view_mode': 'kanban',
            'res_model': 's.logistic.tracking',
            'type': 'ir.actions.act_window',
            'target': 'current',
            # 'context': {'create': False, 'edit': False, 'delete': False},
        }
