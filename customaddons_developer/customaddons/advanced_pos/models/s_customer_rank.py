import time

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from urllib.parse import urljoin
from json import dumps
import json
import logging

_logger = logging.getLogger(__name__)


class SCustomerRankInherit(models.Model):
    _name = 's.customer.rank'
    check_sync_magento = fields.Boolean(string='Đã sync M2')
    rank = fields.Char(string='Rank', required=True)
    total_amount = fields.Float(string='Tổng điểm', required=True)

    def _get_customer_rank_detail_magento_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url,
                       f'/rest/{magento_odoo_bridge.store_code}/V1/magenest/odooIntegration/rank')

    def _cron_sync_customer_rank_detail_magento(self):
        try:
            sdk = self.env.ref('magento2x_odoo_bridge.magento2x_channel').get_magento2x_sdk()['sdk']
            url = self._get_customer_rank_detail_magento_url()
            customer_rank = self.search([('check_sync_magento', '=', False)])
            if customer_rank:
                for r in customer_rank:
                    data = {
                        'customer_rank': r.rank,
                        'total_amount': r.total_amount
                    }
                    resp = sdk._post_data(url=url, data=data)
                    r.write({'check_sync_magento': True})
        except Exception as e:
            _logger.error(e.args)

    def magento_delete_customer_group(self):
        self.ensure_one()
        try:
            sdk = self.env.ref('magento2x_odoo_bridge.magento2x_channel').get_magento2x_sdk()['sdk']
            url = self._get_magento_delete_customer_group_url()
            data = json.dumps({
                "customerGroupCode": self.read()[0].get('rank')
            })
            resp = sdk._post_data(url=url, data=data)
            if resp.get('message'):
                _logger.error(resp.get('message'))
                # raise ValidationError(resp.get('message'))
        except Exception as e:
            _logger.error(e.args)
            # raise ValidationError(e.args)

    def _get_magento_delete_customer_group_url(self):
        magento_odoo_bridge = self.env.ref('magento2x_odoo_bridge.magento2x_channel')
        return urljoin(magento_odoo_bridge.url,
                       f'/rest/{magento_odoo_bridge.store_code}/V1/magenest/odooIntegration/deleteRank')

    def unlink(self):
        for r in self:
            r.magento_delete_customer_group()
        return super(SCustomerRankInherit, self).unlink()
