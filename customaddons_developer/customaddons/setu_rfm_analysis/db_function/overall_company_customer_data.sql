DROP FUNCTION if exists public.overall_company_customer_data(integer);
CREATE OR REPLACE FUNCTION public.overall_company_customer_data(IN active_company_id integer)
RETURNS TABLE(
total_customers bigint
) AS
$BODY$
 BEGIN
 Return Query
SELECT
    count(ip.*) as total_customers
 from
    ir_property ip
 where
    coalesce(substring(ip.value_reference FROM 18)::int,0) != 0 and
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
				) and
    ip.company_id = active_company_id;
END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
