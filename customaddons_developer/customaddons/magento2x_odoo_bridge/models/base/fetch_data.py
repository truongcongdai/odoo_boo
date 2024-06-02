# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, api, _
import logging
_logger = logging.getLogger(__name__)
MageDateTimeFomat = '%Y-%m-%d %H:%M:%S'

class MultiChannelSale(models.Model):
    _inherit = 'multi.channel.sale'

    @api.model
    def _fetch_magento2x_product_attributes(self, sdk, attribute_code = None,
        attribute_set_id = None, wk_params=None,**kwargs):
        # a = self.env['product.attribute'].search([])
        params = {
            "searchCriteria[filter_groups][0][filters][0][field]": "is_global",
            "searchCriteria[filter_groups][0][filters][0][value]": 1,
            "searchCriteria[filter_groups][0][filters][0][condition_type]": 'eq',
            "searchCriteria[filter_groups][1][filters][0][field]": "is_user_defined",
            "searchCriteria[filter_groups][1][filters][0][value]": 1,
            "searchCriteria[filter_groups][1][filters][0][condition_type]": 'eq',
            "searchCriteria[filter_groups][2][filters][0][field]": "frontend_input",
            "searchCriteria[filter_groups][2][filters][0][value]": "select",
            "searchCriteria[filter_groups][2][filters][0][condition_type]": 'eq',
            "searchCriteria[pageSize]": 300
        }
        if wk_params:
            params.update(wk_params)
        return sdk.get_attributes(attribute_code = attribute_code, params = params)

    @api.model
    def _fetch_magento2x_order_data(self, sdk, **kwargs):
        params, filter_group = None, 0
        operation_params = self._fetch_magento2x_params(filter_group = filter_group, **kwargs)
        if len(operation_params):
            params = operation_params
        if sdk.debug:
            _logger.debug('===++++%r======\n %r'%(params,kwargs))
        return sdk.get_orders(params=params)
    
    @api.model
    def fetch_magento2x_customers_data(self,sdk,**kwargs):
        operation_params = self._fetch_magento2x_params(filter_group=0,**kwargs)
        if len(operation_params):
            params = operation_params
        if sdk.debug:
            _logger.debug('===++++%r======\n %r'%(params, kwargs))
        return sdk.get_customers(params=params)

    @api.model
    def _fetch_magento2x_params(self,filter_group = 0,**kwargs):
        params = dict()
        params.update(self.get_search_criteria(filter_group,**kwargs))
        if  kwargs.get('page_size'):
            params["searchCriteria[page_size]"]=kwargs.get('page_size')
        if  kwargs.get('current_page'):
            params["searchCriteria[current_page]"]=kwargs.get('current_page')
        if kwargs.get('fields'):
            params["fields"]=(kwargs.get('fields'))
        return params

    @api.model
    def _fetch_magento2x_product_data(self,sdk,**kwargs):
        message, results, params, total_count, filter_group ='', dict(), {}, 0, 0
        if kwargs.get('type_id'):
            params = {
               "searchCriteria[filter_groups][%s][filters][0][field]"%filter_group: 'type_id',
               "searchCriteria[filter_groups][%s][filters][0][value]"%filter_group:  kwargs.get('type_id'),
               "searchCriteria[filter_groups][%s][filters][0][condition_type]"%filter_group: kwargs.get('condition_type','eq'),
            }
            filter_group+=1
        operation_params = self._fetch_magento2x_params(filter_group = filter_group,**kwargs)
        if len(operation_params):
            params.update(operation_params)
        res = sdk.get_products(params=params)
        message+=res.get('message')
        data=res.get('data')
        if data and data.get('items'):
            total_count = data.get('total_count', 0) or data.get('items', {}).get('total_count', 0)
            for item in data.get('items'):results[item.get('id')]=item
        return dict(
            data=data,
            message=message,
            total_count=total_count
        )
        
    @staticmethod
    def get_search_criteria(filter_group, **kwargs):
        param1 = param2 = field = None
        param = dict()
        parameq = paramin = None
        if kwargs.get('filter_on') == "date_range":
            param1 = kwargs.get('start_date')
            param2 = kwargs.get('end_date')
            field = "created_at" if kwargs.get('operation') == "import" \
                else "updated_at"
            if param1:
                param1 = param1.strftime(MageDateTimeFomat)
            if param2:
                param2 = param2.strftime(MageDateTimeFomat)
        elif kwargs.get('filter_on') == "id_range":
            param1 = kwargs.get('start_id')
            param2 = kwargs.get('end_id')
            field =  "entity_id"
        elif kwargs.get('filter_on') == "category_id":
            parameq = kwargs.get('category_id')
            field = 'category_id'
        elif kwargs.get('filter_on') == "customer_id":
            parameq = kwargs.get('customer_email')
            field = "customer_email"
        elif kwargs.get('filter_on') == "on_id": #specifically for runtime creation process
            parameq = kwargs.get('id')
            field = "entity_id"
        elif kwargs.get('order_state'):
            field = 'status'
            parameq=kwargs.get('order_state')
        if param1 and param2:
            param = {
                "searchCriteria[filter_groups][%s][filters][0][field]"%filter_group:field,
                "searchCriteria[filter_groups][%s][filters][0][condition_type]"%filter_group:'from',
                "searchCriteria[filter_groups][%s][filters][0][value]"%filter_group:param1,
            }
            filter_group += 1
            param.update({
                "searchCriteria[filter_groups][%s][filters][0][field]"%filter_group:field,
                "searchCriteria[filter_groups][%s][filters][0][condition_type]"%filter_group:'to',
                "searchCriteria[filter_groups][%s][filters][0][value]"%filter_group:param2
            })
        elif param1:
            param = {
                "searchCriteria[filter_groups][%s][filters][0][field]"%filter_group: field,
                "searchCriteria[filter_groups][%s][filters][0][value]"%filter_group: param1,
                "searchCriteria[filter_groups][%s][filters][0][condition_type]"%filter_group: 'gt',
            }
        elif param2:
            param = {
                "searchCriteria[filter_groups][%s][filters][0][field]"%filter_group: field,
                "searchCriteria[filter_groups][%s][filters][0][value]"%filter_group: param2,
                "searchCriteria[filter_groups][%s][filters][0][condition_type]"%filter_group: 'lt',
            }
        elif parameq:
            param = {
                "searchCriteria[filter_groups][%s][filters][0][field]"%filter_group: field,
                "searchCriteria[filter_groups][%s][filters][0][value]"%filter_group: parameq,
                "searchCriteria[filter_groups][%s][filters][0][condition_type]"%filter_group: 'eq',
            }
        elif paramin:
            param = {
                "searchCriteria[filter_groups][%s][filters][0][field]"%filter_group: field,
                "searchCriteria[filter_groups][%s][filters][0][value]"%filter_group: paramin,
                "searchCriteria[filter_groups][%s][filters][0][condition_type]"%filter_group: 'in',
            }
        else:
            return {}
        return param
