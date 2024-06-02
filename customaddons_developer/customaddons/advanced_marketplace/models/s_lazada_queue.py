from odoo import fields, models, api


class SLazadaQueue(models.Model):
    _name = 's.lazada.queue'
    _description = 'Lazada Queue'

    dbname = fields.Char()
    level = fields.Char()
    message = fields.Char()
    return_created = fields.Boolean(default=False, string="Đã tạo lại đơn")
    order_status = fields.Char()
    s_lazada_id_order = fields.Char(string="Id Lazada")
    data = fields.Char()

    def cron_sale_order_lazada_error(self):
        queue_ids = self.env['s.lazada.queue'].sudo().search([])
        if len(queue_ids) > 0:
            for queue in queue_ids:
                order_error = self.env['s.sale.order.lazada.error'].sudo().search([('s_lazada_id_order', '=', queue.s_lazada_id_order), ('level', '=', queue.level), ('message', '=', queue.message)], limit=1)
                if len(order_error) == 0:
                    order = self.env['sale.order'].sudo().search([('lazada_order_id', '=', queue.s_lazada_id_order), ('marketplace_lazada_order_status', '=', queue.order_status)], limit=1)
                    if len(order) == 0:
                        self.env['s.sale.order.lazada.error'].sudo().create({
                            'dbname': queue.dbname,
                            'level': queue.level,
                            'message': queue.message,
                            's_lazada_id_order': queue.s_lazada_id_order,
                            'order_status': queue.order_status,
                            'data': queue.data
                        })
                queue.unlink()
