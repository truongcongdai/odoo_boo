# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#import base64
#from collections import defaultdict, OrderedDict
#from decorator import decorator
#from operator import attrgetter
#import importlib
#import io
import logging
#import os
#import pkg_resources
#import shutil
#import tempfile
#import threading
#import zipfile

#import requests
#import werkzeug.urls

#from docutils import nodes
#from docutils.core import publish_string
#from docutils.transforms import Transform, writer_aux

#from docutils.writers.html4css1 import Writer
#import lxml.html
#import psycopg2

#import odoo
from odoo import api, fields, models, modules, tools, _
#from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
#from odoo.exceptions import AccessDenied, UserError
#from odoo.osv import expression
#from odoo.tools.parse_version import parse_version
#from odoo.tools.misc import topological_sort
#from odoo.http import request
from odoo.addons.base.models.ir_module import assert_log_admin_access

_logger = logging.getLogger(__name__)

#def assert_log_admin_access(method):
#    """Decorator checking that the calling user is an administrator, and logging the call.
#
#   Raises an AccessDenied error if the user does not have administrator privileges, according
#   to `user._is_admin()`.
#    """
#    def check_and_log(method, self, *args, **kwargs):
#        user = self.env.user
#        origin = request.httprequest.remote_addr if request else 'n/a'
#        log_data = (method.__name__, self.sudo().mapped('display_name'), user.login, user.id, origin)
#        if not self.env.is_admin():
#            _logger.warning('DENY access to module.%s on %s to user %s ID #%s via %s', *log_data)
#            raise AccessDenied()
#        _logger.info('ALLOW access to module.%s on %s to user %s #%s via %s', *log_data)
#        return method(self, *args, **kwargs)
#    return decorator(check_and_log, method)


class Module(models.Model):
    _inherit = "ir.module.module"

    # update the list of available packages

    @assert_log_admin_access
    @api.model
    def update_list_setu_rfm_analysis(self):
        mod_name = 'setu_rfm_analysis_extended'
        mod = self.env['ir.module.module'].sudo().search(
            [('name', '=', mod_name)],
            limit=1)
        res = [0, 0]
        default_version = modules.adapt_version('1.0')
        # mod = known_mods_names.get(mod_name)
        terp = self.sudo().get_module_info(mod_name)
        values = self.sudo().get_values_from_terp(terp)
        skip = False
        if not mod:
            mod_path = modules.get_module_path(mod_name)
            if not mod_path or not terp:
                skip = True
                pass
            else:
                state = "uninstalled" if terp.get('installable', True) else "uninstallable"
                mod = self.sudo().create(dict(name=mod_name, state=state, **values))
                res[1] += 1

        if not skip:
            _logger.info("===========2=============")
            mod._update_dependencies(terp.get('depends', []), terp.get('auto_install'))
            _logger.info("===========3=============")
            mod._update_exclusions(terp.get('excludes', []))
            _logger.info("===========4=============")
            mod._update_category(terp.get('category', 'Uncategorized'))
            _logger.info("===========5=============")
            _logger.info("===========Final=============")
        return res
