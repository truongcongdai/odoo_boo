from odoo import http
from odoo.http import content_disposition, request
# from odoo.addons.web.controllers.main import _serialize_exception
import base64
import json
from odoo.tools import html_escape
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class EXCELReportController(http.Controller):
    class Binary(http.Controller):
        @http.route('/web/binary/download_document', type='http', auth="public")
        def download_document(self, model, field, id, filename=None, **kw):
            """ Download link for files stored as binary fields.
            :param str model: name of the model to fetch the binary from
            :param str field: binary field
            :param str id: id of the record from which to fetch the binary
            :param str filename: field holding the file's name, if any
            :returns: :class:`werkzeug.wrappers.Response`
            """
            # Model = request.registry[model]
            # cr, uid, context = request.cr, request.uid, request.context
            fields = [field]
            uid = request.session.uid
            model_obj = request.env[model].with_user(uid)
            res = model_obj.browse(int(id)).read(fields)[0]
            filecontent = base64.b64decode(res.get(field) or '')
            if not filecontent:
                return request.not_found()
            else:
                if not filename:
                    filename = '%s_%s' % (model.replace('.', '_'), id)
            return request.make_response(filecontent,
                                         [('Content-Type', 'application/vnd.ms-excel'),
                                          ('Content-Disposition', content_disposition(filename))])

        @http.route('/web/binary/download_xlsx', type='http', auth='user', methods=['POST'], csrf=False)
        def download_report_xlsx(self, model, options, output_format, token, report_name, **kw):
            uid = request.session.uid
            report_obj = request.env[model].with_user(uid)
            options = json.loads(options)
            try:
                if output_format == 'xlsx':
                    response = request.make_response(
                        None,
                        headers=[
                            ('Content-Type', 'application/vnd.ms-excel'),
                            ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                        ]
                    )
                    report_obj.get_xlsx_report(options, response)
                response.set_cookie('fileToken', token)
                return response
            except Exception as e:
                error = {
                    'code': 200,
                    'message': 'Odoo Server Error',
                    'data': str(e)
                }
                return request.make_response(html_escape(json.dumps(error)))


class RfmBackend(http.Controller):

    def get_query_for_rfm_dashboard_graph(self, start_date, end_date, company_str):
        common_query = """
            select 
                distinct(d.name) as name, 
                max(d.count) as count, 
                max(d.year) as year
            from
            (
                Select
                    srs.name,
                    EXTRACT(YEAR FROM so.date_order) as year,
                    sum(so.amount_total) as count
                From
                    sale_order so
                    join setu_rfm_segment srs on srs.id=so.rfm_segment_id 
                where
                    so.state in ('sale','done')
                    and so.date_order between '{0}' and '{1}' {2}
                group by 
                    srs.name, 
                    EXTRACT(YEAR FROM so.date_order)

            Union all

                select 
                    name as name, 
                    0 as count, 
                    0 as year 
                from setu_rfm_segment
                where is_template = 't'
                    )d
            group by d.name
            order by d.name
                    """.format(start_date, end_date, company_str)
        return common_query

    @http.route('/setu_rfm_analysis/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, date_from, date_to, company_id):
        base_date_from = date_from
        base_date_to = date_to
        date_from = datetime.strptime(base_date_from + ' 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT).astimezone(
            pytz.utc) - relativedelta(years=2)
        date_between_base = datetime.strptime(base_date_from + ' 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT).astimezone(
            pytz.utc) - relativedelta(years=1)
        # date_between = datetime.strptime(date_between_base + ' 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT).astimezone(pytz.utc) + relativedelta(years=1)
        date_to = datetime.strptime(base_date_to + ' 23:59:59', DEFAULT_SERVER_DATETIME_FORMAT).astimezone(pytz.utc)
        dashboard_data = []
        company_str = " ,".join(map(str, company_id)) if company_id else ""
        cust_company_str = "and (rp.company_id in (%s) or rp.company_id is null)" % (
            company_str) if company_str else company_str
        rev_company_str = "and (so.company_id in (%s) or so.company_id is null)" % (
            company_str) if company_str else company_str
        lead_company_str = "and (ip.company_id in (%s) or ip.company_id is null)" % (
            company_str) if company_str else company_str
        request.env.cr.execute(
            """
            select 
                distinct(srs.name) as name,
                count(rp.id) as count
            from res_partner rp
                join res_company rc on rc.id in (%s)
                join ir_property ip on 
                    rp.id=split_part(ip.res_id,',',2)::integer and ip.name = 'rfm_segment_id' and ip.company_id = rc.id
                join setu_rfm_segment srs on 
                    srs.id=split_part(ip.value_reference,',',2)::integer
            where rp.id is not null %s
            group by srs.name
            """ % (str(company_id)[1:-1], cust_company_str)
        )
        segment_customer = request.env.cr.dictfetchall()
        if segment_customer:
            dashboard_data.append({
                'chart_type': 'pie',
                'chart_name': 'segment_customer',
                'chart_title': 'Customer By Segment',
                'chart_values': [{'values': segment_customer}]
            })

        request.env.cr.execute(
            """ 
            select 
                distinct(srs.name) as name, 
                count(cl.id) as count 
            from crm_lead cl 
                join res_partner rp on 
                    rp.id=cl.partner_id
                join ir_property ip on 
                    rp.id=split_part(ip.res_id,',',2)::integer 
                    and ip.name = 'rfm_segment_id'
                join setu_rfm_segment srs on 
                    srs.id=split_part(ip.value_reference,',',2)::integer
                left join crm_stage cs on 
                    cs.id=cl.stage_id
            where cs.is_won = 't' %s
            group by srs.name""" % lead_company_str
        )
        segment_lead = request.env.cr.dictfetchall()
        if segment_lead:
            dashboard_data.append({
                'chart_type': 'pie',
                'chart_name': 'segment_lead',
                'chart_title': 'Leads By Segment',
                'chart_values': [{'values': segment_lead}]
            })

        request.env.cr.execute(
            """
            select 
                distinct(srs.name) as name, count(so.id) as count
            from sale_order so left join setu_rfm_segment srs on srs.id=so.rfm_segment_id 
            where so.rfm_segment_id is not null and so.state in ('sale','done')
                and so.date_order between '{0}' and '{1}' {2}
            group by srs.name
                    """.format(date_from, date_to, rev_company_str)
        )
        segment_order = request.env.cr.dictfetchall()
        if segment_order:
            dashboard_data.append({
                'chart_type': 'pie',
                'chart_name': 'segment_order',
                'chart_title': 'Order By Segment',
                'chart_values': [{'values': segment_order}]
            })

        revenue_data_list = []
        year_now = datetime.now().year
        current_year_start_date = datetime.strptime('%s-01-01 00:00:00' % year_now, DEFAULT_SERVER_DATETIME_FORMAT)
        date_today = datetime.strptime(datetime.now().strftime('%Y-%m-%d 23:59:59'), '%Y-%m-%d %H:%M:%S')

        # last_year_start_date = current_year_start_date - relativedelta(years=1)
        # last_year_end_date = datetime.strptime(
        #     (current_year_start_date - timedelta(days=1)).strftime('%Y-%m-%d 23:59:59'), '%Y-%m-%d %H:%M:%S')

        # two_year_back_start_date = last_year_start_date - relativedelta(years=1)
        # two_year_back_end_date = datetime.strptime(
        #     (last_year_start_date - timedelta(days=1)).strftime('%Y-%m-%d 23:59:59'), '%Y-%m-%d %H:%M:%S')
        # graph_query = self.get_query_for_rfm_dashboard_graph(two_year_back_start_date, two_year_back_end_date, rev_company_str)
        # request.env.cr.execute(graph_query)
        segmant_revenue_2_years_back = request.env.cr.dictfetchall()
        # if segmant_revenue_2_years_back:
        #     revenue_data_list.append(
        #         {'key': '%s' % two_year_back_start_date.year, 'values': segmant_revenue_2_years_back})
        # graph_query = self.get_query_for_rfm_dashboard_graph(last_year_start_date, last_year_end_date, rev_company_str)
        # request.env.cr.execute(graph_query)
        # segmant_revenue_previous_year = request.env.cr.dictfetchall()
        # if segmant_revenue_previous_year:
        #     revenue_data_list.append({'key': '%s' % last_year_start_date.year, 'values': segmant_revenue_previous_year})
        graph_query = self.get_query_for_rfm_dashboard_graph(current_year_start_date, date_today, rev_company_str)
        request.env.cr.execute(graph_query)
        segmant_revenue_current_year = request.env.cr.dictfetchall()
        if segmant_revenue_current_year:
            revenue_data_list.append(
                {'key': '%s' % current_year_start_date.year, 'values': segmant_revenue_current_year})

        if revenue_data_list:
            dashboard_data.append({
                'chart_type': 'bar',
                'chart_name': 'segmant_revenue',
                'chart_title': 'Revenue By Segments',
                'chart_values': revenue_data_list
            })
            # segmant_revenue_data = [{ 'key': '%s'%(s.get('segment_name')),'values':[{
            #     'name': '%s'%(s.get('year')),
            #     'count': s.get('total'),
            #     # 'key':'%s'%(s.get('year'))#'%s'%(s.get('segment_name'))
            #         # 'data': [s.get('total')],
            #         # 'fill': 'start',
            #         # 'label': s.get('segment_name'),
            #         # 'borderWidth': 2,
            #     }]} for s in segmant_revenue]
            # # dashboard_data.append({
            # #     'type': 'line',
            # #     'data': {
            # #         'labels': [s.get('segment_name') for s in segmant_revenue],
            # #         'datasets': segmant_revenue_data
            # #     },
            # # })
            #
            # dashboard_data.append({
            #     'chart_type': 'line',
            #     'chart_name': 'segmant_revenue',
            #     'chart_title': 'Revanue By Segments',
            #     'chart_values': segmant_revenue_data
            # })
        #
        # request.env.cr.execute(
        #     """
        #                         select
        #                             date::date as name,
        #                             sum(qty_done) as count
        #                         from stock_move_line sm
        #                             join stock_location sl on sl.id = sm.location_dest_id
        #                         where sm.create_date between %s and %s and sl.usage='customer' and state='done'
        #                         and sm.company_id in %s
        #                         group by date::date
        #                     """, [date_from, date_to, tuple(company_id)]
        # )
        # shipped_qty = request.env.cr.dictfetchall()
        # request.env.cr.execute(
        #     """
        #                                select
        #                            date::date as name,
        #                            sum(qty_done) as count
        #                        from stock_move_line sm
        #                            join stock_location sl on sl.id = sm.location_id
        #                        where sm.create_date between %s and %s and sl.usage='customer' and state='done'
        #                        and sm.company_id in %s
        #                        group by date::date
        #                            """, [date_from, date_to, tuple(company_id)]
        # )
        # returned_qty = request.env.cr.dictfetchall()
        # if shipped_qty or returned_qty:
        #     dashboard_data.append({
        #         'chart_type': 'bar',
        #         'chart_name': 'segmant_revenue',
        #         'chart_title': 'Revanue By Segments',
        #         'chart_values':
        #     })
        return dashboard_data
