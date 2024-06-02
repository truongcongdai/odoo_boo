from odoo import fields, models, tools


class MailThreadInherit(models.AbstractModel):
    _inherit = 'mail.thread'

    @tools.ormcache('self.env.uid', 'self.env.su')
    def _get_tracked_fields(self):
        res = super(MailThreadInherit, self)._get_tracked_fields()
        if self._name == 'res.partner':
            res.update({
                'name', 'phone', 'email', 'mobile', 'date_not_buy', 'membership_code', 'gender',
                'birthday', 'customer_ranked', 'is_new_customer', 'check_sync_customer_rank',
                'is_connected_vani', 'vani_connect_from', 'month', 'day', 'company_type', 'street', 'ward_id', 'district_id',
                'state_id', 'country_id', 'title', 'category_id', 'lang', 'website', 'function', 'vat', 'parent_id'
            })
        return res