DROP FUNCTION if exists public.overall_team_data(integer);
CREATE OR REPLACE FUNCTION public.overall_team_data(IN sales_team_id integer)
RETURNS TABLE(
total_orders bigint,
total_revenue numeric
) AS
$BODY$
 BEGIN
 Return Query
 SELECT
    count(*) as total_orders,
    sum(amount_total) as total_revenue
 from
    sale_order where rfm_team_segment_id is not null and
    team_id = sales_team_id;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
