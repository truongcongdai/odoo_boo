# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
import re
from odoo import api, fields, models,_
import logging
_logger = logging.getLogger(__name__)

Visibility = [
    ('1', 'Not Visible Individually'),
    ('2', 'Catalog'),
    ('3', 'Catalog'),
    ('4', 'Catalog, Search'),
]
Type = [
    ('simple','Simple Product'),
    ('downloadable','Downloadable Product'),
    ('grouped','Grouped Product'),
    ('virtual','Virtual Product'),
    ('bundle','Bundle Product'),
]
ShortDescription=[
    ('same','Same As Product Description'),
    ('custom','Custom')
]


class MultiChannelSale(models.Model):
    _inherit = "multi.channel.sale"

    def get_core_feature_compatible_channels(self):
        return ['magento2x']
        
    def test_magento2x_connection(self):
        for obj in self:
            state = 'error'
            message = ''
            res =obj.get_magento2x_sdk()
            sdk = res.get('sdk')
            if not (sdk and sdk.oauth_token):
                message+='<br/>%s'%(res.get('message'))
                message+='<br/>Oauth Token not received.'
            else:
                configs_res = sdk.get_store_configs()
                message+=configs_res.get('message','')
                configs =configs_res.get('data')
                if configs and len(configs):

                    magento2x_store_config = dict(map(lambda con:(con.get('code'),con),configs)).get(obj.store_code)
                    if not magento2x_store_config:
                        message += '<br/>Store Code %s not in found over magento server.'%(obj.store_code)
                    else:


                        self.store_config = magento2x_store_config
                        state='validate'
                        message += '<br/> Credentials successfully validated.'
            obj.state= state


            if state!='validate':
                message+='<br/> Error While Credentials  validation.'
        return self.display_message(message)

    default_product_set_id = fields.Many2one(
        comodel_name='magento.attributes.set',
        string='Default Attribute Set',
        help='ID of the product attribute set'
    )
    store_code = fields.Char(
        string='Store View Code',
        default='default',
    )
    store_config = fields.Text(
        string='Store Config'
    )

    @api.constrains('is_child_store','default_store_id')
    def check_url(self):
        if self.channel=='magento2x' and \
            self.is_child_store and \
                self.default_store_id :
	        if self.default_store_id.url != self.url:
	                raise Warning("""The Base URI should be same as parent for child store also.""")

    @api.model
    def create(self, vals):
        base_uri = vals.get('url')
        if base_uri:
            vals['url'] = re.sub('/index.php', '',base_uri.strip(' ').strip('/'))

        return super(MultiChannelSale,self).create(vals)

    def write(self, vals):
        base_uri = vals.get('url')
        if base_uri:
            vals['url'] = re.sub('/index.php', '', base_uri.strip(' ').strip('/'))
        return super(MultiChannelSale,self).write(vals)

    def update_magento2x(self, record, get_remote_id, **kwargs):
        # get_remote_id(record)
        # return False,False
        model_name = record._name
        channel_id = self
        debug = channel_id.debug == 'enable'
        res = channel_id.get_magento2x_sdk()
        sdk = res.get('sdk')
        result = False,False
        if not (sdk and sdk.oauth_token):
            return result
        store_id = get_remote_id(record) # update
        if store_id:
            if model_name == 'product.category':
                result = self.env['export.categories'].magento2x_post_categories_bulk_data(sdk,channel_id,record,"update")
            elif model_name == 'product.template':
                res = self.env['export.templates'].with_context(base_operation='update').magento2x_post_products_data(sdk,record,channel_id)
                if res.get('update_ids'):
                    result = True,True
                if debug:
                    _logger.debug('============RESULT UPDATE++++++++++%r+++',res)
        return result

    @api.model
    def _magento2x_get_product_images_vals(self,sdk,channel_id,media,product_id=None):
        vals = dict()
        base_media_url =self.get_magento2x_store_config(channel_id,'base_media_url')
        for data in media:  
            image_url = '{base_media_url}/catalog/product/{file}'.format(base_media_url=base_media_url,file=data.get('file'))
            if image_url:
                image = self.read_website_image_url(image_url)
                from PIL import Image
                from io import BytesIO
                from base64 import b64decode
                if image:
                    size = Image.open(BytesIO(b64decode(image))).size
                    if size > (1920, 1080):
                        # vals['message'] = "For Product"+ str(product_id) +"Image size is too big to store, recieved image "+str(size)+ "\n"
                        vals['message'] = "For Product: {product_id} , \
                        Skipping image : {file} , \
                        size ({size}) is too large to store.".format(product_id=str(product_id)
                        ,file=data.get('file'),
                        size=str(size)
                        )
                    else:
                        vals.update(
                            image=image,
                            image_url=image_url
                        )
            break
        return vals
