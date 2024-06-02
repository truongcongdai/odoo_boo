import requests
from urllib.parse import urljoin
from odoo import _, api, fields, models
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import _create_log


ALLOW_BOO_RELATED_MODEL_NAME = (
    's.product.size',
    's.product.season',
    'dong.hang',
    's.product.collection',
    's.product.color',
    's.product.brand'
)
BRAVO_GET_TOKEN_ENDPOINT = ''
BRAVO_GET_PRODUCT_ENDPOINT = ''


class ResCompany(models.Model):
    _inherit = ['res.company']

    @api.model
    def _force_create_boo_product_related_model_record(self, data, key, model_name):
        """
        All of Boo's product related models was created exactly alike with 2 fields:
            - code: fields.Char, required
            - name: fields.Char
        --> To search and create will be exactly alike: searching for the same code,
        if not have, then create.
        To avoid creating several copy methods, this was created.
        @params:
            - List<Dict>   data: returned data from Bravo
            - string        key: key to searching in data
            - string model_name: name of the Boo product related model
        """
        assert model_name in ALLOW_BOO_RELATED_MODEL_NAME
        code_data = []
        for product_data in data:
            if product_data.get(key):
                code_data.append(product_data[key])
        model_obj = self.env[model_name]
        model_records = model_obj.search([('code', 'in', code_data)])
        to_create = []
        for code in code_data:
            record = model_records.filtered(lambda rec: rec.code == code)
            if record:
                continue
            to_create.append({
                'name': code.upper(),
                'code': code
            })
        if to_create:
            model_obj.create(to_create)

    @api.model
    def _force_create_hierarchy_product_category(self, data):
        """
        - Creating hierarchy product categories following Bravo data.
        Search for name, if not have, create.
        --> At the end of creating process, all records are match.

        - Then add parent_id to the child records. This step could raise a circular
        hierarchy error.
        """
        categories, to_create = [], []
        product_categ_obj = self.env['product.category']
        for i in data:
            if i.get('categ_id'):
                categories.append(i['categ_id'])
            if i.get('sub_categ_id'):
                categories.append(i['sub_categ_id'])
        all_categories = product_categ_obj.search([('name', 'in', categories)])
        for i in data:
            if i.get('categ_id') and not all_categories.filtered(lambda pc: pc.name == i['categ_id']):
                to_create.append({'name': i['categ_id']})
            if i.get('sub_categ_id') and not all_categories.filtered(lambda pc: pc.name == i['sub_categ_id']):
                to_create.append({'name': i['sub_categ_id']})
        if to_create:
            creating_categories = product_categ_obj.create(to_create)
            all_categories |= creating_categories
        for i in data:
            if i.get('categ_id') and i.get('sub_categ_id'):
                parent = all_categories.filtered(lambda pc: pc.name == i['categ_id'])
                child = all_categories.filtered(lambda pc: pc.name == i['sub_categ_id'])
                child.write({'parent_id': parent.id})

    @api.model
    def _force_create_all_product_related_model_record(self, data):
        self._force_create_boo_product_related_model_record(data, key='size', model_name='s.product.size')
        self._force_create_boo_product_related_model_record(data, key='season', model_name='s.product.season')
        self._force_create_boo_product_related_model_record(data, key='product_line', model_name='dong.hang')
        self._force_create_boo_product_related_model_record(data, key='collection', model_name='s.product.collection')
        self._force_create_boo_product_related_model_record(data, key='color', model_name='s.product.color')
        self._force_create_boo_product_related_model_record(data, key='brand_name', model_name='s.product.brand')
        self._force_create_hierarchy_product_category(data)

    @api.model
    def _grooming_product_create_data(self, product_data):
        kich_thuoc = self.env['s.product.size'].search([('code', '=', product_data['size'])], limit=1)
        season = self.env['s.product.season'].search([('code', '=', product_data['season'])], limit=1)
        dong_hang = self.env['dong.hang'].search([('code', '=', product_data['product_line'])], limit=1)
        bo_suu_tap = self.env['s.product.collection'].search([('code', '=', product_data['collection'])], limit=1)
        mau_sac = self.env['s.product.color'].search([('code', '=', product_data['color'])], limit=1)
        thuong_hieu = self.env['s.product.brand'].search([('code', '=', product_data['brand_name'])], limit=1)
        res = {
            'bravo_system_id': product_data['id'],
            'ma_san_pham': product_data['item_code'],
            'sku': product_data['sku'],
            'name': product_data['name'],
            'list_price': product_data['list_price'],
            'is_product_green': product_data['product_green'],
            'gioi_tinh': self._get_product_gender_id(product_data['gender']),
            'detailed_type': self._get_correct_detailed_type(product_data['detailed_type']),
            'kich_thuoc': kich_thuoc and kich_thuoc.id or False,
            'season': season and season.id or False,
            'dong_hang': dong_hang and dong_hang.id or False,
            'bo_suu_tap': bo_suu_tap and bo_suu_tap.id or False,
            'mau_sac': mau_sac and mau_sac.id or False,
            'thuong_hieu': thuong_hieu and thuong_hieu.id or False,
            'categ_id': self._get_product_category_id(product_data),
            'ma_vat_tu': product_data['material_code'],
            'item_code': product_data['standard_price'],
            'sync_push_magento': True
        }
        return res

    @api.model
    def _get_product_gender_id(self, gender):
        product_gender_data = self.env.ref('advanced_integrate_bravo.s_product_gender_female')
        product_gender_data |= self.env.ref('advanced_integrate_bravo.s_product_gender_male')
        product_gender_data |= self.env.ref('advanced_integrate_bravo.s_product_gender_other')
        return product_gender_data.filtered(lambda pg: pg.code == gender).id

    @api.model
    def _get_correct_detailed_type(self, detailed_type):
        allowed_detailed_type_selections = self.env.ref('product.field_product_template__detailed_type'
                                                        ).selection_ids.mapped('value')
        res = 'consu'
        if detailed_type in allowed_detailed_type_selections:
            res = detailed_type
        return res

    @api.model
    def _get_product_category_id(self, product_data):
        category_name = product_data['categ_id']
        if product_data.get('sub_categ_id'):
            category_name = product_data['sub_categ_id']
        category = self.env['product.category'].search([('name', '=', category_name)], limit=1)
        return category.id

    @api.model
    def _get_bravo_token(self, url, username, password):
        url = urljoin(url, BRAVO_GET_TOKEN_ENDPOINT)
        post_data = {
            'username': username,
            'password': password
        }
        headers = {'Content-Type': 'application/json'}
        token = requests.post(url, headers=headers, json=post_data)
        return token

    @api.model
    def _get_bravo_products(self, url, token):
        url = urljoin(url, BRAVO_GET_PRODUCT_ENDPOINT)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        data = requests.get(url, headers=headers, json={})  # as long as data is list of dict, everything works fine!
        assert isinstance(data, list)
        self._force_create_all_product_related_model_record(data)
        product_obj = self.env['product.template']
        create_product_vals_list = []
        bravo_ids = [i['id'] for i in data]
        bravo_products = product_obj.search([('bravo_system_id', 'in', bravo_ids)])
        for product_data in data:
            assert isinstance(product_data, dict)
            product_data_odoo_format = self._grooming_product_create_data(product_data)
            bravo_product = bravo_products.filtered(lambda pt: pt.bravo_system_id == product_data['id'])
            if bravo_product:
                bravo_product.write(product_data_odoo_format)
                continue
            create_product_vals_list.append(product_data_odoo_format)
        product_obj.create(create_product_vals_list)

    @api.model
    def _cron_sync_products(self):
        bravo_url = self.env['ir.config_parameter'].get_param('bravo.url')
        bravo_username = self.env['ir.config_parameter'].get_param('bravo.username')
        bravo_password = self.env['ir.config_parameter'].get_param('bravo.password')
        if not all([bravo_url, bravo_username, bravo_password]):
            return
        try:
            self.env.cr.commit()
            token = self._get_bravo_token(bravo_url, bravo_username, bravo_password)
            if token:
                self._get_bravo_products(bravo_url, token)
        except Exception as e:
            self.env.cr.rollback()
            _create_log(
                name='Cron synchronize product failures', message=e.args, func='_cron_sync_products'
            )
