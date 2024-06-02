from odoo import tools
from odoo import api, fields, models


class RFMYearlyAnalysisBySegment(models.Model):
    _name = "rfm.yearly.analysis.by.segment"
    _description = "RFM Yearly Analysis By Segment"
    _auto = False
    _order = 'calculation_year desc'

    calculation_year = fields.Text("Calculation Year", help="Display which year is selected for RFM calculation")
    segment_id = fields.Many2one("setu.rfm.segment", "RFM Segment")
    total_customers = fields.Integer("Total Customers")
    ratio = fields.Float("Customer Ratio")
    company_id = fields.Many2one('res.company')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        _qry = """
            Select min(segment_id) as id,* from get_yearly_rfm_analysis_by_segment()
            group by calculation_year,segment_id,company_id,total_customers,ratio
        """

        return _qry

    def init(self):
        # self._table = rfm_yearly_analysis_by_segment
        sp_query = self.sp_get_yearly_rfm_analysis_by_segment()
        self.env.cr.execute(sp_query)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    def sp_get_yearly_rfm_analysis_by_segment(self):
        sp_type = 'get_rfm_analysis_data_static'
        if self.env.user.has_group('setu_rfm_analysis.group_dynamic_rules'):
            sp_type = 'get_rfm_analysis_data_dynamic'
        query = """
        drop view if exists rfm_yearly_analysis_by_segment;
        DROP FUNCTION if exists public.get_yearly_rfm_analysis_by_segment();

CREATE OR REPLACE FUNCTION public.get_yearly_rfm_analysis_by_segment()
  RETURNS TABLE(calculation_year text, segment_id integer,company_id integer, total_customers bigint, ratio numeric) AS
$BODY$
    DECLARE
            beginning_year Integer := (Select EXTRACT(YEAR FROM Min(date_order)::TIMESTAMP) from sale_order)::Integer;
            ending_year Integer := (Select EXTRACT(YEAR FROM Max(date_order)::TIMESTAMP) from sale_order)::Integer;
        a Integer := beginning_year;

    BEGIN
        Drop Table if exists rfm_analysis_temp_table;
        CREATE TEMPORARY TABLE rfm_analysis_temp_table(
            calculation_year text,
            company_id integer, 
            customer_id integer,
            segment_id integer
        );

        while a <= ending_year loop
            PERFORM %s('{}', (a ||'-01-01')::date, (a ||'-12-01')::date, 'company') D;
            Insert into rfm_analysis_temp_table
            Select a::text,
                D.company_id, D.customer_id, D.rfm_segment_id
            from rfm_analysis D where row_num = 1;
            a := a + 1;
        end loop;

        RETURN QUERY
        with all_data as (
            Select T.calculation_year, T.segment_id,T.company_id, count(T.customer_id) as total_customers from rfm_analysis_temp_table T
            group by T.calculation_year, T.segment_id, T.company_id
        ),
        total_customer as (
            Select d.calculation_year,d.company_id, sum(d.total_customers) as tc from all_data as d
            group by d.calculation_year, d.company_id
        )
        select ad.*,
        Round((ad.total_customers / (case when total_cust.tc >=1 then total_cust.tc else 1 end)) * 100, 2)
        from all_data ad inner join total_customer total_cust on total_cust.calculation_year = ad.calculation_year and total_cust.company_id = ad.company_id;

    END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;""" % (sp_type)
        return query

class RFMYearlyAnalysisBySegmentTeam(models.Model):
    _name = "rfm.yearly.analysis.by.segment.team"
    _description = "RFM Yearly Analysis By Segment By Sales Team"
    _auto = False
    _order = 'calculation_year desc'

    calculation_year = fields.Text("Calculation Year", help="Display which year is selected for RFM calculation")
    segment_id = fields.Many2one("setu.rfm.segment", "RFM Segment")
    total_customers = fields.Integer("Total Customers")
    ratio = fields.Float("Customer Ratio")
    team_id = fields.Many2one('crm.team')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        _qry = """
            Select min(segment_id) as id,* from get_yearly_rfm_analysis_by_segment_team()
            group by calculation_year,segment_id,team_id,total_customers,ratio
        """

        return _qry

    def init(self):
        # self._table = rfm_yearly_analysis_by_segment
        sp_query = self.sp_get_yearly_rfm_analysis_by_segment()
        self.env.cr.execute(sp_query)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    def sp_get_yearly_rfm_analysis_by_segment(self):
        sp_type = 'get_rfm_analysis_data_static'
        if self.env.user.has_group('setu_rfm_analysis.group_dynamic_rules'):
            sp_type = 'get_rfm_analysis_data_dynamic'
        query = """
        drop view if exists rfm_yearly_analysis_by_segment_team;
        DROP FUNCTION if exists public.get_yearly_rfm_analysis_by_segment_team();

CREATE OR REPLACE FUNCTION public.get_yearly_rfm_analysis_by_segment_team()
  RETURNS TABLE(calculation_year text, segment_id integer,team_id integer, total_customers bigint, ratio numeric) AS
$BODY$
    DECLARE
            beginning_year Integer := (Select EXTRACT(YEAR FROM Min(date_order)::TIMESTAMP) from sale_order)::Integer;
            ending_year Integer := (Select EXTRACT(YEAR FROM Max(date_order)::TIMESTAMP) from sale_order)::Integer;
        a Integer := beginning_year;

    BEGIN
        Drop Table if exists rfm_analysis_temp_table;
        CREATE TEMPORARY TABLE rfm_analysis_temp_table(
            calculation_year text,
            team_id integer, 
            customer_id integer,
            segment_id integer
        );

        while a <= ending_year loop
            PERFORM %s('{}', (a ||'-01-01')::date, (a ||'-12-01')::date, 'sales_team') D;
            Insert into rfm_analysis_temp_table
            Select a::text,
                D.team_id, D.customer_id, D.rfm_segment_id
            from rfm_analysis_team D where row_num = 1;
            a := a + 1;
        end loop;

        RETURN QUERY
        with all_data as (
            Select T.calculation_year, T.segment_id,T.team_id, count(T.customer_id) as total_customers from rfm_analysis_temp_table T
            group by T.calculation_year, T.segment_id, T.team_id
        ),
        total_customer as (
            Select d.calculation_year,d.team_id, sum(d.total_customers) as tc from all_data as d
            group by d.calculation_year, d.team_id
        )
        select ad.*,
        Round((ad.total_customers / (case when total_cust.tc >=1 then total_cust.tc else 1 end)) * 100, 2)
        from all_data ad inner join total_customer total_cust on total_cust.calculation_year = ad.calculation_year and total_cust.team_id = ad.team_id;

    END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;""" % (sp_type)
        return query
