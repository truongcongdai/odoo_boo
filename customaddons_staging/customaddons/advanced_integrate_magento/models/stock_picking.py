from json import dumps
import logging
from urllib.parse import urljoin
from odoo import _, api, fields, models
from ..tools.api_wrapper import _create_log
from collections import defaultdict
from odoo.exceptions import ValidationError
import requests
import json

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = ['stock.picking']

    channel_mapping_ids = fields.One2many(
        comodel_name='channel.pick.mappings',
        inverse_name='stock_picking_id',
        string='Mappings'
    )
    shipping_label = fields.Char(
        string='Shipping Label',
        copy=False,
        readonly=True,
        help='This is a technical field. To store shipping label from Magento 2x'
    )
    magento_do_id = fields.Char(
        string='M2 Delivery Order ID',
        copy=False,
        readonly=True,
        help='This is a technical field. To store delivery order id from Magento 2x'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    # shipment_status = fields.Char(
    #     string='Trạng thái giao hàng'
    # )
    shipment_status = fields.Selection([
        ('giao_hang_that_bai', 'Giao hàng thất bại'),
        ('giao_hang_thanh_cong', 'Giao hàng thành công'),
    ], string='Trạng thái giao hàng')
    is_edited_do_m2_return = fields.Boolean('Là DO M2 đổi trả được quyền sửa Địa điểm nguồn', default=False,
                                            compute="_compute_is_edited_do_m2_return")
    is_boo_do_return = fields.Boolean(string='Là phiếu hoàn thành công từ M2', default=False)
    is_return_magento = fields.Boolean(string="Là ẩn button return đơn hàng M2", compute='_compute_is_return_magento',
                                       store=True)

    @api.depends('sale_id')
    def _compute_is_return_magento(self):
        for rec in self:
            rec.is_return_magento = False
            if rec.sale_id:
                if rec.sale_id.is_magento_order:
                    rec.is_return_magento = True

    def _compute_is_edited_do_m2_return(self):
        for r in self:
            r.is_edited_do_m2_return = False
            if r.sale_id.is_return_order == True and r.sale_id.return_order_id:
                if r.sale_id.return_order_id.is_magento_order == True:
                    r.is_edited_do_m2_return = True

    @api.depends('move_type', 'immediate_transfer', 'move_lines.state', 'move_lines.picking_id')
    def _compute_state(self):
        ''' State of a picking depends on the state of its related stock.move
        - Draft: only used for "planned pickings"
        - Waiting: if the picking is not ready to be sent so if
          - (a) no quantity could be reserved at all or if
          - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
        - Waiting another move: if the picking is waiting for another move
        - Ready: if the picking is ready to be sent so if:
          - (a) all quantities are reserved or if
          - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        '''
        picking_moves_state_map = defaultdict(dict)
        picking_move_lines = defaultdict(set)
        for move in self.env['stock.move'].search([('picking_id', 'in', self.ids)]):
            picking_id = move.picking_id
            move_state = move.state
            picking_moves_state_map[picking_id.id].update({
                'any_draft': picking_moves_state_map[picking_id.id].get('any_draft', False) or move_state == 'draft',
                'all_cancel': picking_moves_state_map[picking_id.id].get('all_cancel', True) and move_state == 'cancel',
                'all_cancel_done': picking_moves_state_map[picking_id.id].get('all_cancel_done',
                                                                              True) and move_state in (
                                       'cancel', 'done'),
                'all_done_are_scrapped': picking_moves_state_map[picking_id.id].get('all_done_are_scrapped', True) and (
                    move.scrapped if move_state == 'done' else True),
                'any_cancel_and_not_scrapped': picking_moves_state_map[picking_id.id].get('any_cancel_and_not_scrapped',
                                                                                          False) or (
                                                       move_state == 'cancel' and not move.scrapped),
            })
            picking_move_lines[picking_id.id].add(move.id)
        for picking in self:
            picking_id = (picking.ids and picking.ids[0]) or picking.id
            if not picking_moves_state_map[picking_id]:
                picking.write({
                    'state': 'draft',
                })
            elif picking_moves_state_map[picking_id]['any_draft']:
                picking.write({
                    'state': 'draft',
                })
            elif picking_moves_state_map[picking_id]['all_cancel']:
                picking.write({
                    'state': 'cancel',
                })
            elif picking_moves_state_map[picking_id]['all_cancel_done']:
                if picking_moves_state_map[picking_id]['all_done_are_scrapped'] and picking_moves_state_map[picking_id][
                    'any_cancel_and_not_scrapped']:
                    picking.write({
                        'state': 'cancel',
                    })
                else:
                    picking.write({
                        'state': 'done',
                    })
            else:
                relevant_move_state = self.env['stock.move'].browse(
                    picking_move_lines[picking_id])._get_relevant_state_among_moves()
                if picking.immediate_transfer and relevant_move_state not in ('draft', 'cancel', 'done'):
                    picking.write({
                        'state': 'assigned',
                    })
                elif relevant_move_state == 'partially_available':
                    picking.write({
                        'state': 'assigned',
                    })
                else:
                    picking.write({
                        'state': relevant_move_state,
                    })

    def action_open_shipping_label(self):
        for rec in self:
            url_magento = self.env.ref('magento2x_odoo_bridge.magento2x_channel').url
            if rec.shipping_label and url_magento:
                redirect_url = url_magento + '/giaohangnhanh/webhook/printlabel/orderid/' + rec.shipping_label
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'}
                url_redirect_shipping_label = requests.get(redirect_url, headers=headers)
                result_m2_return = json.loads(url_redirect_shipping_label.content)
                if len(result_m2_return.get('invalid_order')) > 0:
                    stock_picking_error_ids = []
                    for r in result_m2_return.get('invalid_order'):
                        stock_picking_error_id = self.sudo().search([('shipping_label', '=', r)], limit=1)
                        if stock_picking_error_id and stock_picking_error_id.name not in stock_picking_error_ids:
                            stock_picking_error_ids.append(stock_picking_error_id.name)
                    if len(stock_picking_error_ids) > 0:
                        raise ValidationError("DO %s có Shipping Label lỗi" % (stock_picking_error_ids,))
                return {
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': result_m2_return.get('url'),
                }
            else:
                raise ValidationError('Đơn vận chuyển không có shipping label')

    def _get_magento_update_do_status_url(self):
        self.ensure_one()
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url,
                       f'/rest/{magento_odoo_bridge.store_code}/V1/delivery_order/{self.magento_do_id}/updateStatus')

    @api.model
    def _build_magento_update_do_status_data(self, status, api_cancel_do):
        stock_moves = []
        if self.move_ids_without_package:
            for r in self.move_ids_without_package:
                if r.inventory_qty_note and r.product_id:
                    stock_moves.append({
                        'sku': r.product_id.default_code,
                        'qty_note': r.inventory_qty_note,
                    })
        if not api_cancel_do:
            api_cancel_do = False
        return {
            'DOInformation': {
                'status': status,
                'stock_moves': stock_moves,
                'api_cancel_do': api_cancel_do
            }
        }

    @api.model
    def get_m2_sdk(self):
        return self.env.ref('magento2x_odoo_bridge.magento2x_channel').sudo().get_magento2x_sdk()['sdk']

    def write(self, vals):
        magento_do = self.filtered(lambda rec: rec.magento_do_id)
        picking_state_old = False
        if magento_do:
            picking_state_old = self[0].state
        res = super(StockPicking, self).write(vals)
        if picking_state_old and vals.get('state', '') and vals.get('state') != picking_state_old and magento_do:
            # self.env.cr.commit()
            with self.env.cr.savepoint():
                self.env.cr.execute("SELECT id FROM stock_picking WHERE id = %s FOR UPDATE NOWAIT",
                                    (self[0].id,))
            msg = magento_do.magento_push_state(vals.get('state', ''), self._context.get('api_cancel_do'))
            if not msg or msg.get('msg_status') != 200:
                raise ValidationError(msg.get('msg_status'))
            else:
                self.env.cr.commit()
        return res

    # def button_validate(self):
    #     magento_do = self.filtered(lambda rec: rec.magento_do_id)
    #     if self.move_ids_without_package and magento_do:
    #         for r in self.move_ids_without_package:
    #             if r.product_id.detailed_type == 'product':
    #                 if r.product_id.stock_quant_ids:
    #                     stock_quant_id = r.product_id.stock_quant_ids.filtered(
    #                         lambda st: st.location_id.id == magento_do.location_id.id and
    #                                    st.inventory_quantity_set == False)
    #                     if stock_quant_id:
    #                         available_quantity = stock_quant_id.available_quantity
    #                         if r.product_uom_qty > available_quantity:
    #                             raise ValidationError(
    #                                 'Sản phẩm có SKU %s không đủ tồn kho' % (r.product_id.default_code,))
    #                 else:
    #                     raise ValidationError('Sản phẩm có SKU %s không đủ tồn kho' % (r.product_id.default_code,))
    #     return super(StockPicking, self).button_validate()

    def magento_push_state(self, state, api_cancel_do):
        sdk = self.get_m2_sdk()
        data = dumps(self._build_magento_update_do_status_data(state, api_cancel_do))
        for pick in self:
            if not pick.magento_do_id:
                continue
            try:
                url = self._get_magento_update_do_status_url()
                resp = sdk._post_data(url=url, data=data)
                if resp.get('message'):
                    _logger.error(resp.get('message'))
                    return {'msg_status': resp.get('message')}
                    # raise ValidationError(resp.get('message'))
                    # _create_log(
                    #     name=resp['message'],
                    #     message=f'{fields.Datetime.now().isoformat()} POST {url}\n' +
                    #             f'data={data}\n' +
                    #             f'response={resp}\n',
                    #     func='magento_create_source'
                    # )
                else:
                    return {'msg_status': 200}
            except Exception as e:
                _logger.error(e.args)
                # raise ValidationError(e.args)
                # _create_log(name='magento_push_state_error', message=e.args, func='magento_push_state')

    def _compute_checkbox_do_m2_return(self):
        for r in self:
            r.is_boo_do_return = False
            if r.origin:
                magento_do = self.search(
                    ['|', ('name', '=', r.origin.lstrip('Return of ')), ('name', '=', r.origin.lstrip('Trả lại '))])
                if magento_do:
                    if magento_do.magento_do_id and magento_do.shipment_status == 'giao_hang_that_bai':
                        r.is_boo_do_return = True

    # def button_validate(self):
    #     res = super(StockPicking, self).button_validate()
    #     if self.sale_id:
    #         if self.transfer_type == 'in' and self.sale_id.sale_order_status == 'hoan_thanh_1_phan':
    #             s_so_loyalty_points_id = self.env['s.sale.order.loyalty.program'].sudo().search([], limit=1)
    #             move_lines_return = self.move_lines.filtered(lambda l: l.product_uom_qty > 0 and l.product_id.detailed_type == 'product')
    #             if len(move_lines_return) > 0:
    #                 points_return = 0
    #                 for line in move_lines_return:
    #                     points_return += round(line.quantity_done * line.product_id.lst_price * float(s_so_loyalty_points_id.s_points_currency), 6)
    #
    #                 self.partner_id.write({
    #                     'loyalty_points': self.sale_id.partner_id.loyalty_points - points_return
    #                 })
    #                 self.env['s.order.history.points'].sudo().search([('sale_order_id', '=', self.sale_id.id)]).write({
    #                     'diem_cong': points_return
    #                 })
    #     return res
