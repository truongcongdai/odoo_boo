import json
import logging
import time
_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request, _logger
from odoo.osv.expression import AND
import psycopg2, psycopg2.extensions
from odoo.addons.advanced_integrate_magento.tools.api_wrapper import validate_integrate_token, _create_log
from odoo.addons.advanced_integrate_magento.tools.common import invalid_response, valid_response
import decimal


def get_location_code_or_complete_name(location):
    """
    To get code or complete name of stock.location(,)
    @params:
        - location: single record of stock location
    @return: string
    @errors:
        - ValidationError if input param is not an instance of stock.location(,)
        - Singleton Error.
    """
    if getattr(location, '_name', '') != 'stock.location':
        raise ValidationError(
            'SERVER ERROR: Only serves Stock Location object! Please contact Odoo admin if you see this!'
        )
    location.ensure_one()
    return location.s_code if location.s_code else location.complete_name


def _build_domain_limit_offset(params, is_date_range=True):
    system_limit = int(request.env['ir.config_parameter'].get_param('integrate.maximum_api_record_fetching', 500))
    domain, limit, offset = [], system_limit, 0
    try:
        if params.get('time_start', '') and is_date_range:
            if len(params['time_start'].rstrip()) > 10:
                if datetime.strptime(params['time_start'], '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        params['time_start'], '%d/%m/%Y %H:%M').minute is not None:
                    time_start = datetime.strptime(params['time_start'], '%d/%m/%Y %H:%M') - timedelta(hours=7)
                    if time_start:
                        domain = AND([domain, [('write_date', '>=', time_start)]])
            else:
                domain = AND([domain, [
                    ('write_date', '>=', datetime.strptime(params['time_start'] + ' 00:00', '%d/%m/%Y %H:%M') - timedelta(hours=7))]])
        if params.get('time_end', '') and is_date_range:
            if len(params['time_end'].rstrip()) > 10:
                if datetime.strptime(params['time_end'], '%d/%m/%Y %H:%M').hour is not None and datetime.strptime(
                        params['time_end'], '%d/%m/%Y %H:%M').minute is not None:
                    time_end = datetime.strptime(params['time_end'], '%d/%m/%Y %H:%M') - timedelta(hours=7)
                    if time_end:
                        domain = AND([domain, [('write_date', '<=', time_end)]])
            else:
                domain = AND(
                    [domain,
                     [('write_date', '<=', datetime.strptime(params['time_end'] + ' 23:59', '%d/%m/%Y %H:%M') - timedelta(hours=7))]])
        if params.get('limit') and int(params.get('limit')) < system_limit:
            limit = int(params['limit'])
        else:
            limit = system_limit
        if params.get('offset', ''):
            offset = int(params['offset'])
    except Exception as e:
        _create_log(
            name='build_domain_limit_offset_fail',
            message=f'prams="{params}"\nerrors="{e}"',
            func='_build_domain_limit_offset'
        )
        raise ValidationError(e.args)
    return domain, limit, offset


def _build_domain_limit_offset_stock(params):
    system_limit = int(request.env['ir.config_parameter'].get_param('integrate.maximum_api_record_fetching', 500))
    domain, limit, offset = [], system_limit, 0
    try:
        if params.get('limit', ''):
            limit = int(params['limit'])
        if params.get('offset', ''):
            offset = int(params['offset'])
        # if limit > system_limit:
        #     raise ValidationError(f'limit should not more than {system_limit} records once!')
    except Exception as e:
        _create_log(
            name='build_domain_limit_offset_fail',
            message=f'prams="{params}"\nerrors="{e}"',
            func='_build_domain_limit_offset'
        )
        raise ValidationError(e.args)
    return domain, limit, offset


def build_data_product_attribute(attributes, type):
    if attributes.get('type') == 'color':
        if type == 'create':
            check_attribute = request.env['product.attribute'].sudo().search([('type', '=', 'color')], limit=1)
        else:
            # search attribute co cung bravo_id de update
            check_attribute = request.env['product.attribute'].sudo().search([('bravo_id', '=', attributes.get('id'))],
                                                                             limit=1)
            # neu type cua thuoc tinh khac color va size thi se update. Neu la color va size se bao loi
            if check_attribute and check_attribute['type'] != 'color' and check_attribute['type'] != 'size':
                check_attribute.update({'type': attributes.get('type')})
    elif attributes.get('type') == 'size':
        if type == 'create':
            check_attribute = request.env['product.attribute'].sudo().search([('type', '=', 'size')], limit=1)
        else:
            # search attribute co cung bravo_id de update
            check_attribute = request.env['product.attribute'].sudo().search([('bravo_id', '=', attributes.get('id'))],
                                                                             limit=1)
            # neu type cua thuoc tinh khac color va size thi se update. Neu la color va size se bao loi
            if check_attribute and check_attribute['type'] != 'color' and check_attribute['type'] != 'size':
                check_attribute.update({'type': attributes.get('type')})
    else:
        if type == 'create':
            check_attribute = request.env['product.attribute'].sudo().search([('bravo_id', '=', attributes.get('id'))],
                                                                             limit=1)
        else:
            check_attribute = request.env['product.attribute'].sudo().search([('bravo_id', '=', attributes.get('id'))],
                                                                             limit=1)
            if attributes.get('type') != 'color' and attributes.get('type') != 'size':
                check_attribute.update({'type': attributes.get('type')})
    if type == 'create':
        # check xem khi tao moi id co bi trung bravo_id khong
        check_attribute_id = request.env['product.attribute'].sudo().search([('bravo_id', '=', attributes.get('id'))],
                                                                            limit=1)
        if check_attribute_id['bravo_id'] == attributes.get('id'):
            raise ValidationError("Bản ghi đã có sẵn!")
    return check_attribute


def grooming_product_attribute_data(attributes, type):
    if attributes:
        check_attribute = build_data_product_attribute(attributes, type)
        if check_attribute:
            bravo_value_ids = attributes.get('value_ids')
            if len(bravo_value_ids):
                for attrs in bravo_value_ids:
                    check_attribute_value = check_attribute.value_ids.filtered(
                        lambda rec: rec.code == attrs.get('code'))
                    if attrs.get('code') and attrs.get('name') and attrs.get('code') != '' and attrs.get('name') != '':
                        if len(check_attribute_value) > 0:
                            check_attribute_value.write({
                                'name': attrs.get('name'),
                            })
                        else:
                            check_attribute.write({
                                'name': attributes.get('name'),
                            })
                            check_attribute.value_ids = [(0, 0, {
                                'name': attrs.get('name'),
                                'code': attrs.get('code')
                            })]
                    else:
                        raise ValidationError("Giá trị không được để trống!")
                if type == 'create':
                    check_attribute['bravo_id'] = attributes.get('id')
            return check_attribute, 'update'
        elif not check_attribute:
            data = {
                "name": attributes['name'],
                "type": attributes['type'],
                "value_ids": [(0, 0, {'name': attribute['name'], 'code': attribute['code']}) for attribute in
                              attributes['value_ids']],
                'bravo_id': attributes.get('id'),
                # 'status_product_attribute': True
            }
            product_attribute_id = request.env['product.attribute'].create(data)
            return product_attribute_id, 'create'


def grooming_product_category_data(category, type):
    data = {
        "name": category.get('name', False),
    }
    if category.get('bravo_parent_category_id'):
        parent_category_id = request.env['product.category'].sudo().search(
            [('bravo_id', '=', category.get('bravo_parent_category_id'))], limit=1)
        if parent_category_id:
            data['parent_id'] = parent_category_id.id
        else:
            data['parent_id'] = None
    else:
        data['parent_id'] = None
    if type == 'create':
        data['bravo_id'] = category.get('id')
    return data


def get_product_attribute_value_id(attribute_id, attribute_value_code):
    product_attribute_value = request.env['product.attribute.value'].sudo().search(
        [('code', '=', attribute_value_code), ('attribute_id', '=', attribute_id.id)], limit=1)
    if product_attribute_value:
        return product_attribute_value.id
    return False


def get_attribute_values(attributes, product_template_id):
    if len(attributes) > 0:
        attribute_value_ids = []
        attribute_line_ids = []
        for attr in attributes:
            product_attribute_ids = False
            # tim attrs co san api bravo
            if attr.get('attribute_id'):
                product_attribute_ids = request.env['product.attribute'].sudo().search(
                    [('bravo_id', '=', attr['attribute_id'])], limit=1)
            elif attr.get('attribute_origin_id'):
                product_attribute_ids = request.env['product.attribute'].sudo().browse(attr.get('attribute_origin_id'))
            if len(product_attribute_ids) > 0:
                # lay value trong attr
                attribute_value = attr.get('value')
                if attribute_value:
                    attribute_line = check_new_attribute_line(product_attribute_ids, product_template_id,
                                                              attribute_value.get('code'))

                    attribute_value_ids.append(attribute_line['product_template_attribute_value'].id)
                    attribute_line_ids.append(attribute_line['product_template_attribute_line'].id)
            else:
                raise ValidationError("Thuộc tính bravo_id: %s không tồn tại" % attr.get('attribute_id'))

        return {
            'product_template_attribute_value_ids': [attribute_value_ids],
            'product_template_variant_value_ids': [attribute_line_ids],
        }
        # return {
        #     'product_template_attribute_value_ids': [(6, 0, attribute_value_ids)],
        #     'product_template_variant_value_ids': [(6, 0, attribute_line_ids)],
        # }


def get_product_category(category_id):
    product_categ_id = request.env['product.category'].sudo().search(
        [('bravo_id', '=', category_id)],
        limit=1)
    if product_categ_id:
        return product_categ_id.id
    return False


def update_product_template_attribute_line(attribute_id, product_template_id, attribute_value):
    product_attribute_line = request.env['product.template.attribute.line']
    product_attribute_value_id = get_product_attribute_value_id(attribute_id, attribute_value)
    exists = product_attribute_line.search(
        [('product_tmpl_id', '=', product_template_id.id), ('attribute_id', '=', attribute_id.id)])
    if exists:
        pal_id = exists[0]
    else:
        pal_id = product_attribute_line.sudo().create(
            {
                'product_tmpl_id': product_template_id.id,
                'attribute_id': attribute_id.id,
                'value_ids': [(4, product_attribute_value_id)]
            }
        )
    value_ids = pal_id.value_ids.ids
    if product_attribute_value_id not in value_ids:
        pal_id.sudo().write({'value_ids': [(4, product_attribute_value_id)]})
    return pal_id


def update_product_template_attribute_value(attribute_id, product_template_id, attribute_value):
    product_attribute_value_id = get_product_attribute_value_id(attribute_id, attribute_value)
    exists = request.env['product.template.attribute.value'].search(
        [
            ('product_tmpl_id', '=', product_template_id.id),
            ('product_attribute_value_id', '=', product_attribute_value_id)
        ]
    )
    if exists:
        return exists
    else:
        pal_id = request.env['product.template.attribute.value'].sudo().create(
            {
                'product_tmpl_id': product_template_id.id,
                'product_attribute_value_id': product_attribute_value_id,
            }
        )
        return pal_id


def check_new_attribute_line(attribute_id, product_template_id, attribute_value):
    # product template attribute line
    product_template_attribute_line = update_product_template_attribute_line(attribute_id, product_template_id,
                                                                             attribute_value)
    # product template attribute value
    product_template_attribute_value = update_product_template_attribute_value(attribute_id, product_template_id,
                                                                               attribute_value)
    return {
        'product_template_attribute_line': product_template_attribute_line,
        'product_template_attribute_value': product_template_attribute_value
    }


def get_product_template(data, type):
    if data.get('parent_code'):
        # product_template_variant = request.env['product.template'].sudo().search(
        #     [('ma_san_pham', '=', data.get('parent_code'))],
        #     limit=1)
        parent_product_id = request.env['product.template'].sudo().search(
            [('ma_san_pham', '=', data.get('parent_code'))],
            limit=1)
        data['product_tmpl_id'] = False

        if type == 'create':
            # if product_template_variant:
            #     variant_product_id = product_template_variant.product_variant_ids
            #     if len(variant_product_id) > 0:
            #         for variant_product in variant_product_id:
            #             variant_product_child = variant_product.default_code
            #             for rec in data['variants']:
            #                 if rec['sku'] == variant_product_child:
            #                     raise ValidationError("Sản phẩm đã tồn tại")
            #     return product_template_variant
            if parent_product_id:
                raise ValidationError("Sản phẩm đã tồn tại!")
            else:
                vals = build_data_product_template(data, 'create')
                product_template_id = request.env['product.template'].sudo().create(vals)
                field_pos = product_template_id._fields['available_in_pos']
                if field_pos:
                    product_template_id.sudo().write({
                        'available_in_pos': True
                    })
                return product_template_id
        elif type == 'update':
            if parent_product_id:
                if data['ma_san_pham']:
                    data.update({
                        'parent_code': data['ma_san_pham']
                    })
                    data.pop('ma_san_pham')
                if parent_product_id.sync_push_magento:
                    parent_product_id.sudo().write({
                        'sync_push_magento': False
                    })
                # if parent_product_id.check_sync_product:
                #     parent_product_id.sudo().write({
                #         'check_sync_product': False
                #     })
                vals = build_data_product_template(data, 'update')
                field_pos = parent_product_id._fields['available_in_pos']
                if field_pos:
                    vals.update({
                        'available_in_pos': True
                    })
                return {'parent_product_id': parent_product_id, 'vals': vals}
            else:
                raise ValidationError("Sản phẩm không tồn tại")
    else:
        raise ValidationError("Không có parent_code trong param")


# build data create, update product template
def build_data_product_template(data, type):
    old_vals = {
        # "bravo_system_id": data.get('id'), //tao xong product variant moi cap nhat bravo_system_id
        "name": data.get('name'),
        # "list_price": data.get('lst_price'),
        # "standard_price": data.get('standard_price'),
        "detailed_type": data.get('detailed_type'),
        # "ma_san_pham": data.get('parent_code'),
        # "default_code": data.get('sku'),
        "categ_id": data.get('categ_id'),
    }
    if data.get('categ_id'):
        categ_id = get_product_category(int(data.get('categ_id')))
        if not categ_id:
            raise ValidationError('Không tìm thấy giá trị categ_id = %s !' % data.get('categ_id'))
        old_vals['categ_id'] = categ_id

    new_vals = {
        # 'sync_push_magento': True,
        'sale_ok': True,
    }
    if type == 'create':
        for key, val in old_vals.items():
            key = key
            if key in ['name', 'detailed_type', 'categ_id'] and len(str(val)) > 0 and val:
                new_vals.update(old_vals)
        if new_vals:
            return new_vals
        else:
            raise ValidationError('Bắt buộc phải có')
    elif type == 'update':
        for key, val in old_vals.items():
            if val:
                new_vals[key] = val
        return new_vals


def get_data_product_info(product_info_vals):
    data = {}
    if product_info_vals.get('season'):
        data_product_info_dict = product_info_vals['season'].get('code')
        data_product_info = request.env['s.product.season'].sudo().search(
            [('code', '=', data_product_info_dict)], limit=1)
        if data_product_info:
            data['season'] = data_product_info.id
        elif data_product_info_dict and len(data_product_info) < 1:
            data['season'] = request.env['s.product.season'].sudo().create(product_info_vals.get('season')).id
    if product_info_vals.get('chung_loai'):
        data_product_info_dict = product_info_vals['chung_loai'].get('code')
        data_product_info = request.env['s.product.species'].sudo().search(
            [('code', '=', data_product_info_dict)], limit=1)
        if data_product_info:
            data['chung_loai'] = data_product_info.id
        elif data_product_info_dict and len(data_product_info) < 1:
            data['chung_loai'] = request.env['s.product.species'].sudo().create(product_info_vals.get('chung_loai')).id
    if product_info_vals.get('thuong_hieu'):
        data_product_info_dict = product_info_vals['thuong_hieu'].get('name')
        data_product_info = request.env['s.product.brand'].sudo().search(
            [('name', '=', data_product_info_dict)], limit=1)
        if data_product_info:
            data['thuong_hieu'] = data_product_info.id
        else:
            data['thuong_hieu'] = False
    #     elif data_product_info_dict and len(data_product_info) < 1:
    #         data['thuong_hieu'] = request.env['s.product.brand'].sudo().create(product_info_vals.get('thuong_hieu')).id
    if product_info_vals.get('bo_suu_tap'):
        data_product_info_dict = product_info_vals['bo_suu_tap'].get('code')
        data_product_info = request.env['s.product.collection'].sudo().search(
            [('code', '=', data_product_info_dict)], limit=1)
        if data_product_info:
            data['bo_suu_tap'] = data_product_info.id
        elif data_product_info_dict and len(data_product_info) < 1:
            data['bo_suu_tap'] = request.env['s.product.collection'].sudo().create(
                product_info_vals.get('bo_suu_tap')).id
    if product_info_vals.get('chat_lieu'):
        data_product_info_dict = product_info_vals['chat_lieu'].get('code')
        data_product_info = request.env['s.product.material'].sudo().search(
            [('code', '=', data_product_info_dict)], limit=1)
        if data_product_info:
            data['chat_lieu'] = data_product_info.id
        elif data_product_info_dict and len(data_product_info) < 1:
            data['chat_lieu'] = request.env['s.product.material'].sudo().create(product_info_vals.get('chat_lieu')).id
    if product_info_vals.get('dong_hang'):
        data_product_info_dict = product_info_vals['dong_hang'].get('name')
        data_product_info = request.env['dong.hang'].sudo().search(
            [('name', '=', data_product_info_dict)], limit=1)
        if data_product_info:
            data['dong_hang'] = data_product_info.id
        else:
            data['dong_hang'] = False
        # elif data_product_info_dict and len(data_product_info) < 1:
        #     data['dong_hang'] = request.env['dong.hang'].sudo().create(product_info_vals.get('dong_hang')).id
    if data:
        return data
    return False


def grooming_product_data(product_template_id, product, type):
    # tao san pham
    data = {
        "bravo_system_child_id": product.get('id'),
        "lst_price": product.get('lst_price'),
        # "standard_price": product.get('standard_price'),
        "default_code": product.get('sku'),
        # "parent_code": product.get('parent_code'),
        "detailed_type": product.get('detailed_type'),
        "ma_cu": product.get('old_code'),
        # "item_code": product.get('item_code'),
        "ma_san_pham": product.get('parent_code'),
        "uom_id": product.get('uom_code'),
        "ma_vat_tu": product.get('product_code', None),
        # "is_product_green": product.get('is_product_green'),
        # "bo_suu_tap": product.get('collection'),
        "gioi_tinh": product.get('gender'),
        "barcode": product.get('barcode'),
    }
    #convert lst_price to float
    if data['lst_price'] or data['lst_price'] == 0:
        list_price_float = False
        list_price = data['lst_price']
        if list_price and isinstance(list_price, int):
            list_price_float = list_price
        elif list_price and isinstance(list_price, str):
            if '.' in list_price:
                list_price_float = float(list_price.replace('.', ''))
            elif ',' in list_price:
                list_price_float = float(list_price.replace(',', ''))
            else:
                list_price_float = float(list_price)
        if list_price_float and list_price_float >= 0:
            data.update({
                'lst_price': list_price_float
            })
        else:
            data.update({
                'lst_price': 0
            })
    if not data['bravo_system_child_id'] or data['bravo_system_child_id'] < 0:
        raise ValidationError('Giá trị id = %s không hợp lệ!' % data['bravo_system_child_id'])
    product_info_vals = {
        "season": product.get('season'),
        # "chung_loai": product.get('species'),
        "thuong_hieu": product.get('brand_name'),
        "dong_hang": product.get('product_line'),
        "chat_lieu": product.get('chat_lieu'),
        "bo_suu_tap": product.get('collection'),
        "chung_loai": product.get('species'),
    }
    # get info
    data_product_info = get_data_product_info(product_info_vals)
    if data_product_info:
        data.update(data_product_info)

    # get brand mapping
    if product.get('brand_name'):
        bravo_old_code = False
        bravo_brand_name = False
        bravo_product_line = False
        if product.get('product_line')['name']:
            bravo_product_line = product.get('product_line')['name']
        if product.get('old_code'):
            bravo_old_code = product.get('old_code')[0]
        if product.get('brand_name')['name']:
            bravo_brand_name = product.get('brand_name')['name']
        mapping_product_line_none = request.env['s.product.brand.bravo.mapping'].sudo().search([
            ('s_bravo_brand', '=',  bravo_brand_name),
            ('s_bravo_lines', '=', False),
            ('s_first_character', '=', bravo_old_code),
        ], limit=1)
        # Nếu mapping brand trên odoo có dòng hàng để trống
        if mapping_product_line_none:
            odoo_brand = mapping_product_line_none.s_odoo_brand
            if odoo_brand:
                data.update({
                    'thuong_hieu': odoo_brand.id
                })
        else:
            mapping_bravo_brand = request.env['s.product.brand.bravo.mapping'].sudo().search([
                ('s_bravo_brand', '=',  bravo_brand_name),
                ('s_bravo_lines', '=', bravo_product_line),
                ('s_first_character', '=', bravo_old_code),
            ], limit=1)
            if mapping_bravo_brand:
                odoo_brand = mapping_bravo_brand.s_odoo_brand
                if odoo_brand:
                    data.update({
                        'thuong_hieu': odoo_brand.id
                    })

    # don vi san pham
    product_uom_categ_unit_id = request.env.ref('uom.product_uom_categ_unit').id
    if product_uom_categ_unit_id:
        data['uom_id'] = product_uom_categ_unit_id
        data['uom_po_id'] = product_uom_categ_unit_id
    # get Category bravo
    if product.get('categ_id'):
        categ_id = get_product_category(int(product.get('categ_id')))
        if not categ_id:
            raise ValidationError('Không tìm thấy giá trị categ_id = %s !' % product.get('categ_id'))
        data['categ_id'] = categ_id
    # categ_origin_id categ odoo
    if product.get('categ_origin_id'):
        data['categ_id'] = product.get('categ_origin_id')
    # get san pham cha
    data['product_tmpl_id'] = False
    data['product_tmpl_id'] = product_template_id.id
    # get attributes
    if product.get('attributes'):
        # dict_attributes = get_attribute_values(product.get('attributes'), product_template_id)
        # if dict_attributes:
        #     if len(product_template_id.product_variant_ids) > 0:
        #         for variant in product_template_id.product_variant_ids:
        #             if len(variant.product_template_variant_value_ids.ids) > 0:
        #                 current_attributes = dict_attributes['product_template_attribute_value_ids'][0]
        #                 product_template_variant_value = variant.product_template_attribute_value_ids.ids
        #                 current_attributes.sort()
        #                 product_template_variant_value.sort()
        #                 if current_attributes == product_template_variant_value:
        #                     variant.sudo().write(data)
        #                 # else:
        #                 #     variant.sudo().write(data)
        #             else:
        #                 variant.sudo().write(data)
        # data.update(dict_attributes)
        request.env['product.template'].check_uniq_ma_san_pham(data['ma_san_pham'], product_template_id.id)
        dict_attributes = get_attribute_values(product.get('attributes'), product_template_id)
        if type == 'create':
            if dict_attributes:
                # write ma_san_pham sau khi tạo xong sản phẩm cha và set attribute
                if product.get('parent_code'):
                    product_template_id.sudo().write({
                        'ma_san_pham': product.get('parent_code')
                    })
                if len(product_template_id.product_variant_ids) > 0:
                    for variant in product_template_id.product_variant_ids:
                        if variant.bravo_system_child_id and variant.bravo_system_child_id == product.get('id'):
                            raise ValidationError('Giá trị id = %s trùng lặp!' % product.get('id'))
                        if len(variant.product_template_variant_value_ids.ids) > 0:
                            current_attributes = dict_attributes['product_template_attribute_value_ids'][0]
                            product_template_variant_value = variant.product_template_attribute_value_ids.ids
                            current_attributes.sort()
                            product_template_variant_value.sort()
                            if current_attributes == product_template_variant_value:
                                variant.sudo().write(data)
                        else:
                            variant.sudo().write(data)
            data.update(dict_attributes)
        if type == 'update':
            variant_value = product_template_id.product_variant_ids
            if len(variant_value) > 0:
                variants_attribute = []
                product_attribute = []
                for rec in product.get('attributes'):
                    value_code = rec['value'].get('code')
                    if value_code:
                        variants_attribute.append(value_code)
                for variant in variant_value:
                    product_attribute_value = variant.product_template_attribute_value_ids.product_attribute_value_id
                    for product in product_attribute_value:
                        product_value = product.code
                        if product_value:
                            product_attribute.append(product_value)
                    product_attribute.sort()
                    variants_attribute.sort()
                    if product_attribute == variants_attribute:
                        if variant.default_code and variant.barcode:
                            data.pop('default_code')
                            data.pop('barcode')
                            variant.sudo().write(data)
                        else:
                            variant.sudo().write(data)
                        break
                    else:
                        product_attribute = []
                # if product_attribute == []:
                #     data_response = {
                #         'sku': data.get('default_code')
                #     }
                #     raise ValidationError('Không tìm thấy giá trị %s' % data_response)
            else:
                raise ValidationError('Giá trị id = %s không hợp lệ!' % product.get('id'))
    return data


class APIControllers(http.Controller):

    @validate_integrate_token
    @http.route('/create-attributes', methods=['POST'], auth='public', type='json', csrf=False)
    def create_product_attributes(self):
        try:
            body = request.jsonrequest
            if body['attributes']:
                attributes = body['attributes']
                if (attributes['id'] and attributes['id'] > 0) and attributes['name'] != '' and attributes[
                    'type'] != '':
                    data = grooming_product_attribute_data(attributes, 'create')
                    if data[1] == 'update':
                        return valid_response(head='create_product_attributes',
                                              message=data[0].read(['name', 'type', 'value_ids']),
                                              status=200)
                    if data[1] == 'create':
                        return valid_response(head='create_product_attributes',
                                              message=data[0].read(['name', 'type', 'value_ids']),
                                              status=200)
                    raise ValidationError("Bản ghi đã có sẵn!")
                else:
                    raise ValidationError("Giá trị id không hợp lệ!") if (
                            not attributes['id'] or attributes['id'] <= 0) else \
                        ValidationError("Giá trị không được để trống!")
        except Exception as e:
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/update-attributes/<int:bravo_id>', methods=['POST'], auth='public', type='json', csrf=False)
    def update_product_attributes(self, bravo_id):
        try:
            body = request.jsonrequest
            attributes = body.get('attributes')
            if attributes and (bravo_id and bravo_id > 0) and attributes['name'] != '' and attributes['type'] != '':
                product_attribute = request.env['product.attribute'].sudo().search(
                    [('bravo_id', '=', bravo_id)], limit=1)
                attributes.update({
                    'id': bravo_id
                })
                if product_attribute and product_attribute.value_ids:
                    data = grooming_product_attribute_data(attributes, 'update')
                    if data[1] == 'update':
                        return valid_response(head='create_product_attributes',
                                              message=data[0].read(['name', 'type', 'value_ids']),
                                              status=200)
                raise ValidationError("Bản ghi chưa có sẵn!")
            else:
                raise ValidationError("Giá trị id không hợp lệ!") if (bravo_id <= 0) else ValidationError(
                    "Giá trị không được để trống!")
        except Exception as e:
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/create-product-category', methods=['POST'], auth='public', type='json', csrf=False)
    def create_product_category(self):
        try:
            body = request.jsonrequest
            if body['category']:
                category = body['category']
                if category['id'] and category['id'] > 0 and category['name'] != '':
                    data = grooming_product_category_data(category, 'create')
                    product_category = request.env['product.category'].sudo().search(
                        [('bravo_id', '=', category.get('id'))], limit=1)
                    if not product_category:
                        product_category_id = request.env['product.category'].create(data)
                        return valid_response(head='create_product_attributes',
                                              message=product_category_id.sudo().read(['parent_id', 'name']),
                                              status=200)
                    raise ValidationError("Bản ghi đã có sẵn!")
                else:
                    raise ValidationError("Giá trị id không hợp lệ!") if (
                            not category['id'] or category['id'] <= 0) else ValidationError(
                        "Giá trị không được để trống!")
        except Exception as e:
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/update-product-category/<int:bravo_id>', methods=['POST'], auth='public', type='json', csrf=False)
    def update_product_category(self, bravo_id):
        try:
            body = request.jsonrequest
            if body['category']:
                category = body['category']
                if bravo_id and bravo_id > 0 and category['name'] != '':
                    data = grooming_product_category_data(category, 'update')
                    product_category = request.env['product.category'].sudo().search(
                        [('bravo_id', '=', bravo_id)], limit=1)
                    if product_category:
                        product_category_id = product_category.sudo().write(data)
                        return valid_response(head='create_product_attributes',
                                              message=product_category.sudo().read(['parent_id', 'name']),
                                              status=200)
                    raise ValidationError("Bản ghi chưa có sẵn!")
                else:
                    raise ValidationError("Giá trị id không hợp lệ!") if (bravo_id <= 0) else ValidationError(
                        "Giá trị không được để trống!")
        except Exception as e:
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/create-product', methods=['POST'], auth='public', type='json', csrf=False)
    def create_product(self):
        try:
            limit_record_create = True
            start_time = time.time()
            parameter = request.env.ref('advanced_integrate_bravo.record_time_limit_create_product')
            number_limit = request.env.ref('advanced_integrate_bravo.parameter_limit_create_update_product')
            record_time = parameter.write_date
            date_now = datetime.now()
            if int(number_limit.value) > 0:
                if record_time.date() == date_now.date():
                    if record_time.hour == date_now.hour and record_time.minute == date_now.minute:
                        if record_time.second < date_now.second <= 59 and int(parameter.value) < int(number_limit.value):
                            limit_record_create = False
                    else:
                        parameter.sudo().write({
                            'value': 0
                        })
                        limit_record_create = False
                else:
                    limit_record_create = False
            else:
                limit_record_create = False
            if limit_record_create == False:
                    body = request.jsonrequest
                    data = body['product']
                    response = []
                    if data:
                        # lay san pham cha
                        product_template_id = get_product_template(data, 'create')
                        if product_template_id:
                            if data['variants']:
                                for variant in data['variants']:
                                    # update variant
                                    data_variant = grooming_product_data(product_template_id, variant, 'create')
                                    response.append(data_variant)
                            # Write product_template sau khi create xong mới cho sync sang M2
                            product_template_id.sudo().write({
                                'bravo_system_id': data.get('id'),
                                'sync_push_magento': True,
                                # 'check_sync_product': False
                            })
                            # product_variant = request.env['product.product'].sudo().create(data)
                            request.env['ir.logging'].sudo().create({
                                'name': 'api-create-product-bravo',
                                'type': 'server',
                                'dbname': 'boo',
                                'level': 'INFO',
                                'path': 'url',
                                'message': str(body),
                                'func': 'create_product',
                                'line': '0',
                            })
                            check_time = time.time() - start_time
                            parameter.sudo().write({
                                'value': int(parameter.value) + 1
                            })
                            print(check_time)
                            return valid_response(head='create_product',
                                                  message=response,
                                                  status=200)
        except Exception as e:
            _logger.error(e.args)
            request.env['ir.logging'].sudo().create({
                'name': 'api-create-product-bravo',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(body),
                'func': 'create_product',
                'line': '0',
            })
            return invalid_response(head='param_input_error', message=e.args)

    @validate_integrate_token
    @http.route('/update-product/<bravo_product_id>', methods=['POST'], auth='public', type='json', csrf=False)
    def update_product(self, bravo_product_id):
        try:
            limit_record_update = True
            start_time = time.time()
            parameter = request.env.ref('advanced_integrate_bravo.record_time_limit_update_product')
            number_limit = request.env.ref('advanced_integrate_bravo.parameter_limit_create_update_product')
            record_time = parameter.write_date
            date_now = datetime.now()
            if int(number_limit.value) > 0:
                if record_time.date() == date_now.date():
                    if record_time.hour == date_now.hour and record_time.minute == date_now.minute:
                        if record_time.second < date_now.second <= 59 and int(parameter.value) < int(number_limit.value):
                            limit_record_update = False
                    else:
                        parameter.sudo().write({
                            'value': 0
                        })
                        limit_record_update = False
                else:
                    limit_record_update = False
            else:
                limit_record_update = False
            if limit_record_update == False:
                body = request.jsonrequest
                data = body['product']
                response = []
                if data and bravo_product_id:
                    data.update({
                        'ma_san_pham': data.get('parent_code'),
                        'parent_code': bravo_product_id
                    })
                    parent_product_id = get_product_template(data, 'update')
                    if parent_product_id:
                        if data['variants']:
                            for variant in data['variants']:
                                # update variant
                                data = grooming_product_data(parent_product_id['parent_product_id'], variant, 'update')
                                response.append(data)
                    # parent_product_id['vals'].update({
                    #     'sync_push_magento': True,
                    # })
                    # Write product_template sau khi update xong mới cho sync sang M2
                    parent_product_id['parent_product_id'].sudo().write(parent_product_id['vals'])
                    parent_product_id['parent_product_id'].sudo().write({
                        'sync_push_magento': True,
                        # 'check_sync_product': False
                    })
                    request.env['ir.logging'].sudo().create({
                        'name': 'api-update-product-bravo',
                        'type': 'server',
                        'dbname': 'boo',
                        'level': 'INFO',
                        'path': 'url',
                        'message': str(body) if body else None,
                        'func': 'update_product',
                        'line': '0',
                    })
                    check_time = time.time() - start_time
                    parameter.sudo().write({
                        'value': int(parameter.value) + 1
                    })
                    print(check_time)
                    return valid_response(head='update_product',
                                          message=response,
                                          status=200)
                else:
                    raise ValidationError("Giá trị id = %s không hợp lệ!" % bravo_product_id)
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'api-update-product-bravo',
                'type': 'server',
                'dbname': 'boo',
                'level': 'ERROR',
                'path': 'url',
                'message': str(e) + '\n' + str(body),
                'func': 'update_product',
                'line': '0',
            })
            return invalid_response(head='param_input_error', message=e.args)
        except psycopg2.Error as e:
            return e

    @staticmethod
    def format_invoice_details(invoice_lines, format_style='bravo'):
        res = []
        for inv in invoice_lines:
            res.append({
                'id': inv.id,
                'invoice_date': inv.move_id.invoice_date,
                'invoice_name': inv.move_id.name,
                'location_id': inv.sale_line_ids.order_id.warehouse_id.mapped('name'),
                'product_name': inv.product_id.ma_vat_tu,
                'product_size': inv.product_id.kich_thuoc.name,
                'product_barcode': inv.product_id.barcode,
                'quantity': inv.quantity,
                'product_standard_price': inv.product_id.lst_price,
                'price_unit': inv.price_unit,
                'discount': inv.discount,
                'price_subtotal': inv.price_subtotal,
            })
        return res

    @validate_integrate_token
    @http.route('/invoice-details/<invoice_type>', methods=['GET'], auth='public', type='json', csrf=False)
    def get_invoice_details(self, invoice_type, *args, **kwargs):
        try:
            if invoice_type not in ('out_invoice', 'out_refund'):
                raise ValidationError(
                    'Only support 2 types of invoice detail query type: ' +
                    '`out_invoice` & `out_refund`, got `%s`' % invoice_type
                )
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            invoice_detail_base_domain = [
                ('move_id.move_type', '=', invoice_type),
                ('exclude_from_invoice_tab', '=', False)  # only select invoice lines without Journal Items tab
            ]
            domain = AND([domain, invoice_detail_base_domain])
            fetch_records = request.env['account.move.line'].search(domain, limit=limit, offset=offset)
            return self.format_invoice_details(fetch_records)
        except Exception as e:
            return invalid_response(head='fail_query_params', message=e.args)

    @staticmethod
    def format_stock_details(stock_picks, format_style='bravo'):
        res = []
        for pick in stock_picks:
            for move in pick.move_ids_without_package:
                res.append({
                    'date_done': pick.date_done.strftime('%Y-%m-%d'),
                    'id': move.id,
                    'name': pick.name,
                    'location_id': get_location_code_or_complete_name(pick.location_id),
                    'location_dest_id': get_location_code_or_complete_name(pick.location_dest_id),
                    'product_name': move.product_id.name,
                    'product_size': move.product_id.kich_thuoc.name,
                    'product_barcode': move.product_id.barcode,
                    'quantity_done': move.quantity_done,
                })
        return res

    @validate_integrate_token
    @http.route('/stock-details/<internal_direction>', methods=['GET'], auth='public', type='json', csrf=False)
    def get_stock_details(self, internal_direction, *args, **kwargs):
        try:
            if internal_direction not in ('internal-out', 'internal-in'):
                raise ValidationError(
                    'Only support 2 types of invoice detail query type: ' +
                    '`internal-out` & `internal-in`, got `%s`' % internal_direction
                )
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            stock_detail_base_domain = [
                ('picking_type_id.code', '=', 'internal'),
                ('state', '=', 'done')
            ]
            if internal_direction == 'internal-out':
                stock_detail_base_domain.append(('location_dest_id.s_is_transit_location', '=', True))
            elif internal_direction == 'internal-in':
                stock_detail_base_domain.append(('location_id.s_is_transit_location', '=', True))
            domain = AND([domain, stock_detail_base_domain])
            fetch_records = request.env['stock.picking'].search(domain, limit=limit, offset=offset)
            return self.format_stock_details(fetch_records)
        except Exception as e:
            return invalid_response(head='fail_query_params', message=e.args)

    @staticmethod
    def _format_online_sale_stock_details(stock_picks, format_style='bravo'):
        res = []
        for pick in stock_picks:
            for move in pick.move_ids_without_package:
                res.append({
                    'date_done': pick.date_done.strftime('%Y-%m-%d'),
                    'id': move.id,
                    'sale_name': pick.sale_id.name,
                    'location_id': get_location_code_or_complete_name(pick.location_id),
                    'location_dest_id': get_location_code_or_complete_name(pick.location_dest_id),
                    'product_name': move.product_id.name,
                    'product_size': move.product_id.kich_thuoc.name,
                    'product_barcode': move.product_id.barcode,
                    'quantity_done': move.quantity_done,
                })
        return res

    @validate_integrate_token
    @http.route('/online-sale-stock-details', method=['GET'], auth='public', type='json', csrf=False)
    def get_online_sale_stock_details(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            online_sale_stock_detail_base_domain = [
                ('picking_type_id.code', '=', 'outgoing'),
                ('state', '=', 'done'),
                ('sale_id.is_magento_order', '=', True)
            ]
            domain = AND([domain, online_sale_stock_detail_base_domain])
            fetch_records = request.env['stock.picking'].search(domain, limit=limit, offset=offset)
            return self._format_online_sale_stock_details(fetch_records)
        except Exception as e:
            return invalid_response(head='fail_query_params', message=e.args)

    @staticmethod
    def _format_outgoing_stock_details(stock_picks, format_style='bravo'):
        res = []
        for move in stock_picks.move_ids_without_package:
            res.append({
                'id': move.id,
                'date_done': move.picking_id.date_done.strftime('%Y-%m-%d'),
                'name': move.picking_id.name,
                'location_id': get_location_code_or_complete_name(move.picking_id.location_id),
                'note': move.picking_id.note,
                'product_name': move.product_id.name,
                'product_size': move.product_id.kich_thuoc.name,
                'product_barcode': move.product_id.barcode,
                'quantity_done': move.quantity_done,
            })
        return res

    @validate_integrate_token
    @http.route('/outgoing-stock-details', methods=['GET'], auth='public', type='json', csrf=False)
    def get_outgoing_stock_details(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            out_going_stock_detail_base_domain = [
                ('picking_type_id.code', '=', 'outgoing'),
                ('state', '=', 'done')
            ]
            domain = AND([domain, out_going_stock_detail_base_domain])
            fetch_records = request.env['stock.picking'].search(domain, limit=limit, offset=offset)
            return self._format_outgoing_stock_details(fetch_records)
        except Exception as e:
            return invalid_response(head='fail_query_params', message=e.args)

    @staticmethod
    def _format_adjustment_stock_details(stock_moves, format_style='bravo'):
        res = []
        for move in stock_moves:
            move_data = {
                'id': move.id,
                'date_done': move.create_date,
                'location': '',
                'product_name': move.product_id.name,
                'product_size': move.product_id.kich_thuoc.name,
                'product_barcode': move.product_id.barcode,
                'inventory_quantity': False,
                'quantity': move.inventory_adjustment_quantity,
                'inventory_diff_quantity': False
            }
            if move.location_id.usage == 'inventory':
                move_data['location'] = get_location_code_or_complete_name(move.location_dest_id)
                move_data['inventory_diff_quantity'] = move.quantity_done
                move_data['inventory_quantity'] = move.inventory_adjustment_quantity - move.quantity_done
            elif move.location_dest_id.usage == 'inventory':
                move_data['location'] = get_location_code_or_complete_name(move.location_id)
                move_data['inventory_diff_quantity'] = -move.quantity_done
                move_data['inventory_quantity'] = move.inventory_adjustment_quantity + move.quantity_done
            res.append(move_data)
        return res

    @validate_integrate_token
    @http.route('/adjustment-stock-details', method=['GET'], auth='public', type='json', csrf=False)
    def get_adjustment_stock_details(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            inventory_adjustment_locations = request.env['stock.location'].search(
                [('s_is_inventory_adjustment_location', '=', True)]
            )
            adjustment_stock_detail_base_domain = [
                ('state', '=', 'done'),
                '|',
                ('location_id', 'in', inventory_adjustment_locations.ids),
                ('location_dest_id', 'in', inventory_adjustment_locations.ids),
            ]
            domain = AND([domain, adjustment_stock_detail_base_domain])
            fetch_records = request.env['stock.move'].search(domain, limit=limit, offset=offset)
            return self._format_adjustment_stock_details(fetch_records)
        except Exception as e:
            return invalid_response(head='fail_query_params', message=e.args)

    @staticmethod
    def _format_online_success_sale_stock_account_details(sale_order_lines, style='bravo'):
        res = []
        for move in sale_order_lines.move_ids:
            line = move.sale_line_id
            invoice_date = ''
            related_invoice_invoice_date = line.invoice_lines.move_id.filtered(lambda am: am.invoice_date)
            if related_invoice_invoice_date:
                invoice_date = max(related_invoice_invoice_date.mapped('invoice_date')).isoformat()
            res.append({
                'id': line.id,
                'invoice_date': invoice_date,
                'sale_name': line.order_id.name,
                'location_id': get_location_code_or_complete_name(move.location_id),
                'location_dest_id': get_location_code_or_complete_name(move.location_dest_id),
                'product_name': line.product_id.name,
                'product_size': line.product_id.kich_thuoc.name,
                'product_barcode': line.product_id.barcode,
                'quantity_done': move.quantity_done,
                'product_cost': line.product_id.standard_price,
                'so_line_price': line.price_unit,
                'so_line_discount': line.boo_total_discount,
                'so_line_price_subtotal': line.price_subtotal,
            })
        return res

    @staticmethod
    def _base_online_success_sale_domain(flow):
        assert flow in ('success', 'return_success')
        if flow == 'return_success':
            return [
                ('state', 'in', ['sale', 'done']),
                ('is_return_order', '=', True),
                ('return_order_id.is_magento_order', '=', True)
            ]
        return [
            ('state', 'in', ['sale', 'done']),
            ('is_magento_order', '=', True),
            ('return_order_ids', '=', False)
        ]

    @validate_integrate_token
    @http.route('/online-success-sale-stock-account-details/<flow>', method=['GET'], auth='public', type='json',
                csrf=False)
    def get_online_success_sale_stock_account_details(self, flow, *args, **kwargs):
        try:
            if flow not in ('success', 'return_success'):
                raise ValidationError(f'Only support 2 types of flow: `success` & `return_success`. Got `{flow}`')
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            online_success_sale_base_domain = self._base_online_success_sale_domain(flow)
            domain = AND([domain, online_success_sale_base_domain])
            fetch_records = request.env['sale.order'].search(domain, limit=limit, offset=offset)
            return self._format_online_success_sale_stock_account_details(fetch_records.order_line)
        except Exception as e:
            return invalid_response(head='fail_query_params', message=e.args)

    @staticmethod
    def _format_online_fail_return_sale_stock_details(records, format_style='bravo'):
        res = []
        for move in records.move_ids_without_package.filtered(lambda sm: sm.origin_returned_move_id):
            line = move.sale_line_id
            invoice_date = ''
            related_invoice_invoice_date = line.invoice_lines.move_id.filtered(lambda am: am.invoice_date)
            if related_invoice_invoice_date:
                invoice_date = max(related_invoice_invoice_date.mapped('invoice_date')).isoformat()
            res.append({
                'id': move.id,
                'invoice_date': invoice_date,
                'sale_name': move.sale_line_id.order_id.name,
                'old_location_id': get_location_code_or_complete_name(move.origin_returned_move_id.location_id),
                'location_id': get_location_code_or_complete_name(move.location_id),
                'location_dest_id': get_location_code_or_complete_name(move.location_dest_id),
                'product_name': move.product_id.name,
                'product_size': move.product_id.kich_thuoc.name,
                'product_barcode': move.product_id.barcode,
                'quantity_done': move.quantity_done,
            })
        return res

    @validate_integrate_token
    @http.route('/online-fail-return-sale-stock-details', method=['GET'], auth='public', type='json', csrf=False)
    def get_online_fail_return_sale_stock_details(self, *args, **kwargs):
        try:
            domain, limit, offset = _build_domain_limit_offset(kwargs)
            online_fail_return_sale_base_domain = [
                ('group_id.sale_id.is_magento_order', '=', True),
                ('state', '=', 'done')
            ]
            domain = AND([domain, online_fail_return_sale_base_domain])
            fetch_records = request.env['stock.picking'].search(domain, limit=limit, offset=offset)
            return self._format_online_fail_return_sale_stock_details(fetch_records)
        except Exception as e:
            return invalid_response(head='fail_query_params', message=e.args)

    def _create_transer_in(self, picking, partner):
        # product = request.env['product.template'].sudo().search([('id', '=', product_id)])
        try:
            if not isinstance(picking, dict):
                raise ValidationError("Sai định dạng dữ liệu: %r" % picking)

            if 'date_done' in picking and picking['date_done']:
                date_done = datetime.strptime(picking['date_done'], '%Y-%m-%d') - timedelta(hours=7)
            else:
                raise ValidationError("Thiếu thông tin ngày hoàn thành %r" % picking)

            if 'name' in picking and picking['name']:
                bravo_name = picking['name']
            else:
                raise ValidationError("Thiếu thông tin tên phiếu %r" % picking)

            if 'product_detail' in picking and picking['product_detail']:
                product_detail = picking['product_detail']
                if not isinstance(product_detail, list):
                    raise ValidationError("Sai định dạng danh sách sản phẩm %r" % product_detail)
            else:
                raise ValidationError("Thiếu thông tin danh sách sản phẩm %r" % picking)

            if 'warehouse_code' in picking and picking['warehouse_code']:
                warehouse_code = picking['warehouse_code']
            else:
                raise ValidationError("Thiếu thông tin mã kho hàng %r" % picking)

            if 'location_id' in picking and picking['location_id']:
                if isinstance(picking['location_id'], int) and picking['location_id'] > 0:
                    location_id = picking['location_id']
                else:
                    raise ValidationError("Sai định dạng id địa điểm nguồn location_id = %r" % picking['location_id'])
            else:
                location_id = False

            if len(product_detail) > 0:
                for product in product_detail:
                    if isinstance(product, dict) and 'sku' in product and 'quantity_done' in product \
                            and isinstance(product['sku'], str) and isinstance(product['quantity_done'], int):
                        continue
                    else:
                        raise ValidationError("Sai định dạng dữ liệu sản phẩm: %r" % product)
            else:
                raise ValidationError("Danh sách sản phẩm không được để trống %r" % picking)

            if warehouse_code:
                warehouse_id = request.env['stock.warehouse'].sudo().search(
                    [('code', '=', warehouse_code)], limit=1)
                if warehouse_id:
                    if not warehouse_id.in_type_id:
                        raise ValidationError("Kho chưa cấu hình loại giao nhận %r" % warehouse_id.code)
                    if not warehouse_id.lot_stock_id:
                        raise ValidationError("Kho chưa cấu hình địa điểm kho %r" % warehouse_id.code)
                    move_ids_without_package = []
                    if location_id:
                        location = request.env['stock.location'].sudo().search([('id', '=', location_id)])
                        if not location:
                            raise ValidationError("Không tìm thấy địa điểm nguồn location_id =  %r" % location_id)
                        elif location.usage == "view":
                            raise ValidationError(
                                "Loại địa điểm nguồn không hợp lệ (Loại địa điểm = xem) location_id = %r" % location.id)

                        for rec in product_detail:
                            product = request.env['product.product'].sudo().search([('default_code', '=', rec['sku'])])
                            if product:
                                if product.detailed_type not in ['consu', 'product']:
                                    raise ValidationError(
                                        "Tồn tại sản phẩm không phải là loại lưu kho SKU = %r" % rec['sku'])
                                move_ids_without_package.append((0, 0, {
                                    'name': product.name,
                                    'product_id': product.id,
                                    'product_uom_qty': rec['quantity_done'],
                                    'product_uom': product.uom_id.id,
                                    'quantity_done': rec['quantity_done'],
                                    'location_id': location.id,
                                    'location_dest_id': warehouse_id.lot_stock_id.id,
                                    'description_picking': rec['description'] if 'description' in rec and rec[
                                        'description'] else "",
                                    'state': 'draft',
                                }))
                            else:
                                raise ValidationError("Không tồn tại sản phẩm với id = %r" % rec['sku'])

                    else:
                        # location = warehouse_id.in_type_id.default_location_src_id
                        # if not location:
                        #     raise ValidationError(
                        #         "Kho chưa có điểm đi mặc định, vui lòng cấu hình lại hoặc nhập điểm đi hợp lệ Mã kho: %r" % warehouse_id.code)
                        #
                        # elif location.usage == "view":
                        #     raise ValidationError(
                        #         "Kho có loại địa điểm nguồn mặc định không hợp lệ (Loại địa điểm = xem) Mã kho %r" % warehouse_code)
                        location = False
                        if partner and partner == 'BRAVO':
                            partner_data = request.env.ref('advanced_integrate_bravo.s_res_partner_bravo')
                            if partner_data:
                                location = partner_data.property_stock_supplier
                        else:
                            raise ValidationError(
                                "Invalid partner: %r" % partner)
                        for rec in product_detail:
                            product = request.env['product.product'].sudo().search([('default_code', '=', rec['sku'])])
                            if product:
                                if product.detailed_type not in ['consu', 'product']:
                                    raise ValidationError(
                                        "Tồn tại sản phẩm không phải là loại lưu kho SKU = %r" % rec['sku'])
                                move_ids_without_package.append((0, 0, {
                                    'name': product.name,
                                    'product_id': product.id,
                                    'product_uom_qty': rec['quantity_done'],
                                    'product_uom': product.uom_id.id,
                                    'quantity_done': rec['quantity_done'],
                                    'location_id': location.id,
                                    'location_dest_id': warehouse_id.lot_stock_id.id,
                                    'description_picking': rec['description'] if 'description' in rec and rec[
                                        'description'] else "",
                                    'state': 'draft',
                                }))
                            else:
                                raise ValidationError("Không tồn tại sản phẩm với sku = %r" % rec['sku'])

                    data_valid = {
                        'picking_type_id': warehouse_id.in_type_id.id,
                        'location_dest_id': warehouse_id.lot_stock_id.id,
                        'location_id': location.id,
                        'move_ids_without_package': move_ids_without_package,
                        'date_done': date_done,
                        'bravo_name': bravo_name,
                        'partner_id': partner_data.id,
                    }
                    return data_valid
                else:
                    raise ValidationError("Không tìm thấy thông tin kho hàng với mã kho = %r" % warehouse_code)
        except Exception as e:
            return invalid_response(head='param_input_error', message=e.args)

    # @validate_integrate_token
    # @http.route('/update-product-inventory', methods=['POST'], auth='public', type='json', csrf=False)
    # def update_product_inventory(self):
    #     try:
    #         body = request.jsonrequest
    #         if 'data' not in body:
    #             raise ValidationError("Chưa có dữ liệu data")
    #         if not isinstance(body['data'], list):
    #             raise ValidationError("Sai định dạng dữ liệu, data phải là 1 list")
    #         if len(body['data']) < 0:
    #             raise ValidationError("Dữ liệu không được để trống")
    #         picking_done = []
    #         partner = body['partner']
    #         for picking in body['data']:
    #             picking_data = self._create_transer_in(picking, partner)
    #             if 'status_code' in picking_data:
    #                 raise ValidationError(picking_data["error_msg"])
    #             else:
    #                 picking_done.append(picking_data)
    #
    #         message = []
    #         if len(picking_done) == len(body['data']):
    #             for data in picking_done:
    #                 picking_id = request.env['stock.picking'].sudo().create(data)
    #                 picking_id.action_confirm()
    #                 picking_id.button_validate()
    #                 picking_id.update({
    #                     'state': 'done',
    #                     'date_done': data['date_done']
    #                 })
    #                 message.append(picking_id.name)
    #             request.env['ir.logging'].sudo().create({
    #                 'name': 'api_update_product_inventory_info',
    #                 'type': 'server',
    #                 'dbname': 'boo',
    #                 'level': 'INFO',
    #                 'path': 'url',
    #                 'message': str(body),
    #                 'func': 'update_product_inventory',
    #                 'line': '0',
    #             })
    #             return valid_response(head='update_product_inventory', message=message,
    #                                   status=200)
    #     except Exception as e:
    #         # request.env['ir.logging'].sudo().create({
    #         #     'type': 'server',
    #         #     'name': 'api_update_product_inventory_error',
    #         #     'path': 'path',
    #         #     'line': 'line',
    #         #     'func': 'func',
    #         #     'message': str(e.args)
    #         # })
    #         request.env['ir.logging'].sudo().create({
    #             'name': 'api_update_product_inventory_error',
    #             'type': 'server',
    #             'dbname': 'boo',
    #             'level': 'ERROR',
    #             'path': 'url',
    #             'message': str(e) + '\n' + str(body),
    #             'func': 'update_product_inventory',
    #             'line': '0',
    #         })
    #         return invalid_response(head='param_input_error', message=e.args)
