from datetime import timedelta, datetime
import inspect
import io
import base64
from random import randint
from barcode import EAN13
from barcode.writer import ImageWriter
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    logistic_barcode = fields.Char('Barcode')
    body_barcode = fields.Char(string='Body Barcode',
                               default=lambda self: self.env['ir.sequence'].next_by_code('logistic.picking.barcode'))
    s_picking_out_id = fields.Integer(string='id phiếu xuất')
    # body_barcode = fields.Char(string='Body Barcode')

    # _sql_constraints = [
    #     ('logistic_barcode_uniq', 'unique (logistic_barcode)', 'Barcode là duy nhất!')
    # ]

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     context = self._context
    #     res = super(StockPicking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     if res.get('toolbar', False) and res.get('toolbar').get('print', False):
    #         if view_type == 'form':
    #             transfer = self.env[context.get('active_model')].search([('id', '=',context.get('active_id'))])
    #             if transfer:
    #                 if transfer.picking_out_ids:
    #                     reports = res.get('toolbar').get('print')
    #                     for report in reports:
    #                         if report.get('name', False) and report.get('name') == '#Phiếu xuất':
    #                             res['toolbar']['print'].remove(report)
    #     return res

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        if vals.get('stock_package_ids') != None and vals.get('transfer_in_id') != None and vals.get(
                'picking_type_id') != None and vals.get('location_id') != None and vals.get(
                'location_dest_id') != None and vals.get('delivery_priority_type') != None and vals.get(
                'deadline') != None and vals.get('confirm_user_id') != None and vals.get('move_ids_without_package') and vals.get(
                'state') != None and vals.get('immediate_transfer') != None:
            if res.transfer_in_id:
                res.s_picking_out_id = self.env.context.get('id_phieu_xuat')
        return res

    def button_validate(self):
        if self.transfer_out_id:
            #Add context to self
            new_context = dict(self.env.context)
            new_context['id_phieu_xuat'] = self.id
            self = self.with_context(new_context)
        res = super(StockPicking, self).button_validate()
        if self.transfer_in_id:
            if self.s_picking_out_id:
                transfer_out_id = self.transfer_in_id.picking_out_ids.filtered(lambda l: l.id == self.s_picking_out_id)
                if transfer_out_id and transfer_out_id.date_done:
                    calculate_timedelta = (self.date_done - transfer_out_id.date_done)
                    days = calculate_timedelta.days
                    hours, remainder = divmod(calculate_timedelta.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    hours += days * 24
                    self.transfer_in_id.s_total_time_transfer = int(hours) + minutes / 60
        return res

    def random_with_N_digits(self, n):
        range_start = 10 ** (n - 1)
        range_end = (10 ** n) - 1
        return randint(range_start, range_end)

    def logistic_print_picking(self):
        tong_le, tong_chan, tong, phan_bu = 0, 0, 0, 0
        for rec in self:
            if rec.transfer_out_id or rec.transfer_in_id:
                # picking_in_id = rec.transfer_out_id.filtered(lambda r: r.picking_in_ids.s_picking_out_id == rec.id)
                # if picking_in_id:
                search_body_barcode = self.sudo().search([('body_barcode', '=', rec.body_barcode)])
                if rec.state != 'done':
                    raise ValidationError(_('Chỉ có thể in phiếu khi phiếu đã hoàn thành!'))
                else:
                    if not rec.body_barcode or len(search_body_barcode) > 1:
                        rec.body_barcode = self.env['ir.sequence'].next_by_code('logistic.picking.barcode')
                    if rec.body_barcode:
                        barcode = rec.body_barcode
                        for i in range(0, len(barcode)):
                            if i % 2 == 0:
                                tong_le += int(barcode[i])
                            else:
                                tong_chan += int(barcode[i])
                        tong = tong_le + tong_chan * 3
                        so_du = tong % 10
                        if so_du != 0:
                            phan_bu = 10 - so_du
                        rec.logistic_barcode = barcode + str(phan_bu)
                    if rec.transfer_type == 'out':
                        picking_in_id = rec.transfer_out_id.picking_in_ids.filtered(lambda r: r.s_picking_out_id == rec.id)
                        if picking_in_id:
                            return self.env.ref('advanced_logistic.action_report_print_phieu_xuat').report_action(self)
                        else:
                            raise ValidationError(_('Không thể in phiếu này vì đã cũ!'))
                    elif rec.transfer_type == 'in':
                        raise ValidationError(_('Không thể in phiếu nhập!'))

            else:
                raise ValidationError(_('Chỉ có thể in phiếu điều chuyển!'))

    def create_s_logistic_tracking(self):
        query_tracking = self._cr.execute("""
            SELECT id FROM s_logistic_tracking WHERE s_transfer_out_id = %s LIMIT 1
        """, (self.id,))
        result_query_tracking = [item[0] for item in self._cr.fetchall()]
        if len(result_query_tracking):
            s_logistic_tracking_id = self.env['s.logistic.tracking'].sudo().browse(result_query_tracking[0])
            if s_logistic_tracking_id:
                if not s_logistic_tracking_id.s_complete_date and s_logistic_tracking_id.s_date_in:
                    if s_logistic_tracking_id.s_transfer_out_id.state != 'done':
                        raise ValidationError(_('Vui lòng hoàn thành phiếu điều chuyển trước khi quét Barcode!'))
                    if s_logistic_tracking_id.s_state == 'received':
                        s_logistic_tracking_id.sudo().write({
                            's_complete_date': datetime.now(),
                        })
                    return s_logistic_tracking_id.id
        else:
            s_internal_transfer_id = False
            if self.transfer_out_id:
                s_internal_transfer_id = self.transfer_out_id
            tracking_id = self._cr.execute("""
                SELECT id FROM s_logistic_tracking
            """)
            result = [item[0] for item in self._cr.fetchall()]
            if len(result):
                new_id = max(result) + 1
                ###insert to table s_logistic_tracking
                self._cr.execute("""
                    INSERT INTO s_logistic_tracking (id, s_internal_transfer_id, s_transfer_out_id)
                    VALUES (%s, %s, %s);
                """, (new_id, s_internal_transfer_id.id, self.id,))
                self.env.cr.commit()
                s_logistic_tracking_id = self.env['s.logistic.tracking'].sudo().browse(new_id)
                if s_logistic_tracking_id:
                    s_logistic_tracking_id.sudo().write({
                        's_internal_transfer_id': s_internal_transfer_id,
                        's_transfer_out_id': self.id,
                        's_location_out_id': self.location_id.id if self.location_id else False,
                        's_location_transfer_in_id': s_internal_transfer_id.location_in_id.id if s_internal_transfer_id else False,
                        's_transfer_quantity': self.total_quantity_done,
                        's_date_in': datetime.now(),
                        's_receiver': self.receiver_id.id if self.receiver_id else False,
                        's_location_in_id': self.location_dest_id.id if self.location_dest_id else False,
                    })
                    return s_logistic_tracking_id.id
