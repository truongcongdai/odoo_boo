from odoo import fields, models, api, _
import json
from datetime import timedelta


class AdvancedGiftCard(models.Model):
    _inherit = 'ir.logging'

    def _compute_undo_pos_order_logging(self):
        for r in self:
            if r.name == 'pos_order_create_from_ui' and r.type == 'server' and r.message:
                order = json.loads(r.message)
                lines = []
                if order['data']['lines']:
                    for line in order['data']['lines']:
                        line_value = {
                            'qty': line[-1].get('qty'),
                            'price_unit': line[-1].get('price_unit'),
                            'price_subtotal': line[-1].get('price_subtotal'),
                            'price_subtotal_incl': line[-1].get('price_subtotal_incl'),
                            'discount': line[-1].get('discount'),
                            'product_id': line[-1].get('product_id'),
                            'tax_ids': line[-1].get('tax_ids'),
                            'full_product_name': line[-1].get('full_product_name'),
                            'price_extra': line[-1].get('price_extra'),
                            'mau_sac': line[-1].get('mau_sac'),
                            'kich_thuoc': line[-1].get('kich_thuoc'),
                            'default_code': line[-1].get('default_code'),
                            'pack_lot_ids': line[-1].get('pack_lot_ids'),
                        }
                        lines.append([0, 0, line_value])

                self.env['s.lost.bill'].sudo().create({
                    'name': order['data']['name'],
                    'amount_paid': order['data']['amount_paid'],
                    'amount_total': order['data']['amount_total'],
                    'amount_tax': order['data']['amount_tax'],
                    'amount_return': order['data']['amount_return'],
                    'creation_date': (fields.datetime.now() + timedelta(hours=7)).strftime(
                        "%Y-%m-%d %H:%M"),
                    'sale_person_id': order['data']['sale_person_id'],
                    'partner_id': order['data']['partner_id'],
                    'employee_id': order['data']['employee_id'],
                    'pos_session_id': order['data']['pos_session_id'],
                    'pricelist_id': order['data']['pricelist_id'],
                    'lines': lines,
                    'statement_ids': order['data']['statement_ids'],
                    'state': 'order_da_ton_tai',
                })
