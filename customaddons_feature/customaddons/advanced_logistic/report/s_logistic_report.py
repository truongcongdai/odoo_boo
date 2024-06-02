from odoo import api, fields, models, tools


class SLogisticReport(models.Model):
    _name = 's.logistic.report'
    _auto = False
    _rec_name = 'id'
    _order = 'id desc'

    id = fields.Integer("", readonly=True)
    s_transfer_quantity = fields.Integer(string='Số lượng')
    s_delivery_time = fields.Float(string='Thời gian giao nhận')
    s_total_time = fields.Integer(string='Tổng thời gian', store=True)
    s_state = fields.Selection([('received', 'Đã nhận hàng'), ('delivered', 'Đã giao hàng thành công')], string='Trạng thái')
    s_code = fields.Char('Mã phiếu điều chuyển')
    s_internal_transfer_id = fields.Many2one('s.logistic.tracking', string='Phiếu xuất')

    def _select(self):
        return """ 
            SELECT
                MIN(l.id) AS id,
                COUNT(*) AS s_transfer_quantity,
                l.s_code as s_code,
                CASE WHEN l.s_delivery_time > 0 THEN l.s_delivery_time ELSE 0.0 END as s_delivery_time,
                l.s_state as s_state,
                CASE WHEN l.s_total_time > 0 THEN l.s_total_time ELSE 0.0 END as s_total_time,
                l.id as s_internal_transfer_id

        """

    def _from(self):
        return """
            FROM s_logistic_tracking as l
        """

    def _group_by(self):
        return """
            GROUP BY
                l.s_code,
                l.s_transfer_quantity,
                l.s_delivery_time,
                l.s_state,
                l.s_total_time,
                l.id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._group_by())
                         )

