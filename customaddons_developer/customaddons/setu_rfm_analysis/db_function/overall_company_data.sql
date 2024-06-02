DROP FUNCTION if exists public.overall_company_data(integer);
CREATE OR REPLACE FUNCTION public.overall_company_data(IN active_company_id integer)
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
    sale_order where rfm_segment_id is not null and
    company_id = active_company_id;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
