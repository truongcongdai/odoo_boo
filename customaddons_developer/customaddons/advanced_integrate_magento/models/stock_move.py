from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_product_free = fields.Boolean(string='Là line sản phẩm được tặng', default=False)
    s_m2_reserved_quantity = fields.Integer(
        string='M2 Reserved Quantity',
        required=False)
    is_push_m2_reserved_quantity = fields.Boolean(
        string='Đã push reserved lên M2',
        default=False, copy=False)
    s_pushed_m2_reserved_state = fields.Char(string='Trạng thái push reserved lên M2', copy=False)
    s_disable_push_m2_reserved_quantity = fields.Boolean(string='Không push reserved lên M2', default=False, copy=False)

    def write(self, vals):
        if vals.get('state'):
            for rec in self:
                if rec.sudo().picking_id:
                    picking = rec.picking_id
                    if not picking.magento_do_id and not picking.is_boo_do_return:
                        # state chuyen sang assigned giu ton kho
                        if vals.get('state') == 'assigned':
                            # Truong hop state san sang push reserved len cho M2
                            if not rec.s_pushed_m2_reserved_state:
                                rec.s_m2_reserved_quantity = - rec.reserved_availability
                                rec.is_push_m2_reserved_quantity = False
                            else:
                                # da push reserved len cho M2, state != assigned, can push len lai cho M2
                                if rec.s_pushed_m2_reserved_state != 'assigned':
                                    rec.s_m2_reserved_quantity = - rec.reserved_availability
                                    rec.is_push_m2_reserved_quantity = False
                                else:
                                    # Da push len M2 trang thai san sang, khong can push lai
                                    rec.s_m2_reserved_quantity = - rec.reserved_availability
                                    rec.is_push_m2_reserved_quantity = True
                        # Truong hop state san sang da push reserved len cho M2, state='done' can push len cho M2 tru reserved
                        else:
                            if rec.s_pushed_m2_reserved_state and rec.s_pushed_m2_reserved_state == 'assigned':
                                rec.s_m2_reserved_quantity = abs(rec.s_m2_reserved_quantity)
                                rec.is_push_m2_reserved_quantity = False
                            else:
                                rec.s_m2_reserved_quantity = 0
                                rec.is_push_m2_reserved_quantity = False
                        # Truong hop M2 call API update reserved quantity, disable push reserved len cho M2, can write = False lai de push len cho M2
                        if rec.s_disable_push_m2_reserved_quantity:
                            rec.s_disable_push_m2_reserved_quantity = False
        return super(StockMove, self).write(vals)
