# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################

from odoo import models, api, _
from datetime import datetime

class MultiChannelSale(models.Model):
	_inherit = 'multi.channel.sale'

	def cron_import_or_update(self,import_date, update_date, model):
		if import_date or update_date:
			obj = self.env['import.operation'].create({'channel_id':self.id})
			kw =  {'filter_on':"date_range",'end_date':datetime.now(),'cron':True}
		if import_date:
			kw['start_date'] = import_date
			kw['operation'] = obj.operation
			obj.import_with_filter(object=model,**kw)
		if update_date:
			kw['start_date'] = update_date
			obj.operation = 'update'
			kw['operation'] = obj.operation
			obj.import_with_filter(object=model,**kw)
			
	def magento2x_import_order_cron(self):
		self.cron_import_or_update(self.import_order_date,self.update_order_date,"sale.order")

	def magento2x_import_product_cron(self):
		self.cron_import_or_update(self.import_product_date,self.update_product_date,"product.template")

	def magento2x_import_partner_cron(self):
		self.cron_import_or_update(self.import_customer_date,self.update_customer_date,"res.partner")

	def magento2x_import_category_cron(self):
		obj = self.env['import.operation'].create({'channel_id':self.id})
		obj.import_with_filter(object="product.category")


	def if_cron_then_update_date(self, kwargs, model):
		def update_date(import_date_field,update_date_field):
			vals = dict()
			if kwargs.get('operation') == "import":
				vals = {import_date_field:datetime.now()}
			if kwargs.get('operation') == "update":
				vals = {update_date_field:datetime.now()}
			self.write(vals)

		if kwargs.get('cron',False):
			if model == "import.templates":
				update_date(
					'import_product_date',
					'update_product_date',
				)
			elif model == "import.partners":
				update_date(
					'import_customer_date',
					'update_customer_date',
				)
			elif model == "import.orders":
				update_date(
					'import_order_date',
					'update_order_date',
				)