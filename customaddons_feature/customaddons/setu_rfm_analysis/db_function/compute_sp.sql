DROP FUNCTION if exists public.compute_rfm_sp(integer,integer,integer []);
CREATE OR REPLACE FUNCTION public.compute_rfm_sp(IN active_company_id integer, current_team_id integer, segment_ids integer[])
RETURNS TABLE(
segment_id integer,
revenue_ratio double precision,
sales_ratio double precision,
partner_ratio double precision,
team_revenue_ratio double precision,
team_sales_ratio double precision,
--pos_revenue_ratio numeric,
--pos_ratio numeric,
--team_pos_revenue_ratio numeric,
--team_pos_ratio numeric,
partners double precision,
company_wise_sales double precision,
sales_team_wise_sales double precision,
company_wise_revenue double precision,
sales_team_wise_revenue double precision
--company_wise_pos bigint,
--sales_team_wise_pos bigint,
--company_wise_revenue_pos numeric,
--sales_team_wise_revenue_pos numeric
) AS
$BODY$

 DECLARE

    total_customers_company double precision := (Select total_customers from overall_company_customer_data(active_company_id))::double precision;
    --total_customers_sales_team bigint := (Select total_customers from overall_team_customer_data(current_team_id))::bigint;

    total_revenue_company double precision := (Select total_revenue from overall_company_data(active_company_id))::double precision;
    total_orders_company double precision := (Select total_orders from overall_company_data(active_company_id))::double precision;
    total_revenue_sales_team double precision := (Select total_revenue from overall_team_data(current_team_id))::double precision;
    total_orders_sales_team bigint := (Select total_orders from overall_team_data(current_team_id))::bigint;

--    total_pos_revenue_company numeric := (Select total_revenue from overall_company_data_pos(active_company_id))::numeric;
--    total_pos_orders_company numeric := (Select total_orders from overall_company_data_pos(active_company_id))::numeric;
--
--    total_pos_revenue_sales_team numeric := (Select total_revenue from overall_team_data_pos(current_team_id))::numeric;
--    total_pos_orders_sales_team bigint := (Select total_orders from overall_team_data_pos(current_team_id))::bigint;

 BEGIN
 Return Query
 Select
	data.id as segment_id,

	CASE WHEN total_revenue_company > 0 THEN
	    round((100*max(data.company_wise_revenue)::float/total_revenue_company))::double precision
	ELSE 0::double precision END
	as revenue_ratio,

	CASE WHEN total_orders_company > 0 THEN
	round((100*max(data.company_wise_sales)::float/total_orders_company))::double precision
	ELSE 0::double precision END
	as sales_ratio,

	CASE WHEN total_customers_company > 0 THEN
	round((100*max(data.partners)::float/total_customers_company))::double precision
	ELSE 0::double precision END
	as partner_ratio,

	CASE WHEN total_revenue_sales_team > 0 THEN
	    round((100*max(data.sales_team_wise_revenue)::float/total_revenue_sales_team))::double precision
	ELSE 0::double precision END
	as team_revenue_ratio,

	CASE WHEN total_orders_sales_team > 0 THEN
	   round((100 * max(data.sales_team_wise_sales)::float/total_orders_sales_team))::double precision
	ELSE 0::double precision END
	as team_sales_ratio,

--	CASE WHEN total_pos_revenue_company > 0 THEN
--	    (100*max(data.company_wise_pos_revenue)/total_pos_revenue_company)::numeric
--	ELSE 0 END
--	as revenue_ratio_pos,
--
--	CASE WHEN total_pos_orders_company > 0 THEN
--	(100*max(data.company_wise_pos)/total_pos_orders_company)::numeric
--	ELSE 0 END
--	as ratio_pos,
--
--	CASE WHEN total_pos_revenue_sales_team > 0 THEN
--	    (100*max(data.sales_team_wise_pos_revenue)/total_pos_revenue_sales_team)::numeric
--	ELSE 0 END
--	as team_revenue_ratio_pos,
--
--	CASE WHEN total_pos_orders_sales_team > 0 THEN
--	(100*max(data.sales_team_wise_pos)/total_pos_orders_sales_team)::numeric
--	ELSE 0 END
--	as team_ratio_pos,

	max(data.partners)::double precision as partners,

	max(data.company_wise_sales)::double precision as company_wise_sales,
	max(data.sales_team_wise_sales)::double precision as sales_team_wise_sales,
	max(data.company_wise_revenue)::double precision as company_wise_revenue,
	max(data.sales_team_wise_revenue)::double precision as sales_team_wise_revenue

--	max(data.company_wise_pos) as company_wise_pos,
--    max(data.sales_team_wise_pos) as sales_team_wise_pos,
--    max(data.company_wise_pos_revenue) as company_wise_pos_revenue,
--    max(data.sales_team_wise_pos_revenue) as sales_team_wise_pos_revenue
from
(
	select
		srs.id,
		count(ps.partner_id) as partners,
		0 as company_wise_sales,
		0 as sales_team_wise_sales,
		0 as company_wise_revenue,
		0 as sales_team_wise_revenue
--		0 as company_wise_pos,
--		0 as sales_team_wise_pos,
--		0 as company_wise_pos_revenue,
--		0 as sales_team_wise_pos_revenue


	from
	setu_rfm_segment srs
	left join partner_segments ps on srs.id = ps.segment_id
	where srs.is_template = false and srs.id = any(segment_ids)
	group by srs.id

	UNION ALL

	select
		srs.id,
		(
			SELECT
				count(*)
			FROM
				 ir_property ip
			WHERE
				ip.fields_id =
				(
				SELECT
					imf.id
				FROM
					ir_model_fields imf
				WHERE
					name = 'rfm_segment_id'
					AND model_id =
					(
						SELECT
							m.id
						FROM
							ir_model m
						WHERE
							m.model = 'res.partner'
					)
				)
				and
				ip.company_id = active_company_id
				and SUBSTRING (ip.value_reference FROM 18)::int = srs.id
		)
		as partners,
		0 as company_wise_sales,
		0 as sales_team_wise_sales,
		0 as company_wise_revenue,
		0 as sales_team_wise_revenue
--		0 as company_wise_pos,
--		0 as sales_team_wise_pos,
--		0 as company_wise_pos_revenue,
--		0 as sales_team_wise_pos_revenue
	from
		setu_rfm_segment srs
	WHERE
		srs.is_template = true and srs.id = any(segment_ids)
	group by
		srs.id

	UNION ALL

	select
		srs.id,
		0 as partners,
		count(so.id) as company_wise_sales,
		0 as sales_team_wise_sales,
		coalesce(sum(so.amount_total),0) as company_wise_revenue,
		0 as sales_team_wise_revenue
--		0 as company_wise_pos,
--		0 as sales_team_wise_pos,
--		0 as company_wise_pos_revenue,
--		0 as sales_team_wise_pos_revenue
	from
	setu_rfm_segment srs
	left join sale_order so on so.rfm_segment_id = srs.id and so.company_id = active_company_id
	--left join sale_order so2 on so2.rfm_team_segment_id = srs.id
	where srs.id = any(segment_ids)
	group by srs.id

	UNION ALL

	select
		srs.id,
		0 as partners,
		0 as company_wise_sales,
		count(so2.id) as sales_team_wise_sales,
		0 as company_wise_revenue,
		coalesce(sum(so2.amount_total),0) as sales_team_wise_revenue
--		0 as company_wise_pos,
--		0 as sales_team_wise_pos,
--		0 as company_wise_pos_revenue,
--		0 as sales_team_wise_pos_revenue
	from
	setu_rfm_segment srs
	--left join sale_order so on so.rfm_segment_id = srs.id and so.company_id = active_company_id
	left join sale_order so2 on so2.rfm_team_segment_id = srs.id
	where srs.id = any(segment_ids)
	group by srs.id

--	UNION ALL
--
--	select
--		srs.id,
--		0 as partners,
--		0 as company_wise_sales,
--		0 as sales_team_wise_sales,
--		0 as company_wise_revenue,
--		0 as sales_team_wise_revenue,
--		count(c.*) as company_wise_pos,
--		count(s.*) as sales_team_wise_pos,
--		sum(c.amount_total) as company_wise_pos_revenue,
--		sum(s.amount_total) as sales_team_wise_pos_revenue
--	from
--	setu_rfm_segment srs
--	left join pos_order c on c.segment_id = srs.id and c.company_id = active_company_id
--	left join pos_order s on s.rfm_segment_id = srs.id
--	where srs.id = any(segment_ids)
--	group by srs.id
)data
group by data.id;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
