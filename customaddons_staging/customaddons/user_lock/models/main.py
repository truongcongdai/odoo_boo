import werkzeug
from odoo.addons.web.controllers.main import Home

from odoo import http
from odoo.http import request


# Odoo Web web Controllers
class HomeController(Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        try:
            if request.session.uid:
                if 'debug=' in request.httprequest.full_path:
                    debug_position = request.httprequest.full_path.index('debug=')
                    if request.httprequest.full_path[debug_position + 6] != '#':
                        if not request.env.ref('base.group_system').id in request.env['res.users'].sudo().browse(
                                request.session.uid).groups_id.ids:
                            return werkzeug.utils.redirect('/web?debug=', 303)
        except Exception as ex:
            a = 0
        return super(HomeController, self).web_client(kw)
