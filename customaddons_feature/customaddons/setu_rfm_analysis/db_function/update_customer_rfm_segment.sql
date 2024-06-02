DROP FUNCTION if exists public.update_customer_rfm_segment(integer[],date, date, character varying, character varying);

CREATE OR REPLACE FUNCTION public.update_customer_rfm_segment(
    company_ids integer[],
    start_date date,
    end_date date,
    calculation_type character varying,
    segment_type character varying)
RETURNS void AS
$BODY$
    BEGIN
        IF calculation_type = 'static' THEN
            PERFORM get_rfm_analysis_data_static(company_ids,start_date, end_date, segment_type)T;
        ELSE
            PERFORM get_rfm_analysis_data_dynamic(company_ids,start_date, end_date, segment_type)T;
        END IF;



        PERFORM set_rfm_segment_values_company(company_ids, end_date,calculation_type) T;
        IF segment_type = 'sales_team' THEN
            PERFORM set_rfm_segment_values_team(company_ids, end_date,calculation_type) T;
        END IF;


    update setu_rfm_segment set calculated_on = (select now()::date);

    END;
    $BODY$
LANGUAGE plpgsql VOLATILE
COST 100;