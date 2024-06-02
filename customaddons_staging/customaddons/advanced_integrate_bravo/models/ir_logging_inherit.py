from odoo import fields, models, api
import json


class IrLoggingInherit(models.Model):
    _inherit = 'ir.logging'

    def _check_pos_order_data_sync_bravo(self):
        for rec in self:
            list_order = []
            total = 0
            if rec.message:
                load_data = json.loads(rec.message[rec.message.find('{"partner":'):])
                if load_data.get('data'):
                    for order in load_data.get('data'):
                        if order.get('details'):
                            for detail in order.get('details'):
                                total += detail.get('price_subtotal')
                                price_subtotal = detail.get('price_unit') - detail.get('discount')
                                if price_subtotal != detail.get('price_subtotal'):
                                    list_order.append(order.get('parent_id'))
            rec.write({
                'line': str(list_order),
                'level': total
            })

    def _compute_price_subtotal_pos_order(self):
        total = 0
        for rec in self:
            if rec.level.isnumeric():
                total += int(rec.level)
        if total > 0:
            raise Exception('Total POS Order: %s' % total)
