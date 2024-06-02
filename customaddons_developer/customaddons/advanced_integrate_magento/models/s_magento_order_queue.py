import json
import ast
from datetime import date, timedelta, datetime
from odoo.exceptions import ValidationError, _logger
from odoo import fields, models, api
from odoo.tests import Form


class SM2OrderQueue(models.Model):
    _name = 's.magento.order.queue'

    s_m2_order_data = fields.Char('Order Data')
    s_odoo_order_id = fields.Char(string='Id odoo của đơn hàng m2')

    def cronjob_update_order_m2(self):
        m2_order_queue_ids = self.search([], limit=100)
        # check model order error xem co loi chua, co roi thi xoa
        if len(m2_order_queue_ids) > 0:
            for rec in m2_order_queue_ids:
                # check order error exist
                s_m2_order_data = json.loads(rec.s_m2_order_data)
                if s_m2_order_data:
                    m2_order_id = self.env['sale.order'].sudo().browse(int(rec.s_odoo_order_id))
                    if m2_order_id:
                        m2_order_id.write(s_m2_order_data)
                    else:
                        self.env['ir.logging'].sudo().create({
                            'name': '_cronjob_update_order_m2',
                            'type': 'server',
                            'dbname': 'boo',
                            'level': 'INFO',
                            'path': 'url',
                            'message': 'order data:' + str(s_m2_order_data) + ' id order odoo: ' + rec.s_odoo_order_id,
                            'func': '_cronjob_update_order_m2',
                            'line': '0',
                        })
                rec.unlink()
