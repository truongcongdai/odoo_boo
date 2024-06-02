DROP FUNCTION if exists public.get_rfm_analysis_data_dynamic(integer[],date, date, character varying);

CREATE OR REPLACE FUNCTION public.get_rfm_analysis_data_dynamic(
IN company_ids integer[],
IN start_date date,
IN end_date date,
IN segment_type character varying)
RETURNS TABLE(
rfm_segment_id integer,
company_id integer,
customer_id integer,
sale_ids integer[],
total_orders integer,
total_order_value numeric,
days_from_last_purchase integer,
atv numeric,
row_num bigint
) AS
$BODY$
    BEGIN
        Drop Table if exists rfm_analysis;
        CREATE TEMPORARY TABLE rfm_analysis(
           rfm_segment_id integer, company_id integer,  customer_id integer, sale_ids integer[],pos_ids integer[],
           total_orders integer, total_order_value numeric, days_from_last_purchase integer,
           atv numeric, row_num bigint);


        PERFORM get_sales_data_for_rfm(company_ids,start_date,end_date,segment_type);
--
--        IF (select nullif(state,'') from ir_module_module where name = 'point_of_sale') = 'installed' THEN
--            PERFORM get_pos_data_for_rfm(company_ids, end_date)T;
--
--        END IF;

        --Return Query
        Insert into rfm_analysis
        Select * from
		(Select
            srs.id,
            STD.company_id,
            STD.customer_id,
            STD.sale_ids,
            STD.pos_ids,
            STD.total_orders,
            STD.total_order_value,
            STD.days_from_last_purchase,
            round(STD.total_order_value/STD.total_orders,2) as average,
            row_number() over(
                PARTITION BY
                STD.customer_id,
                STD.company_id
            ORDER BY
                srs.seq)as row_num
        From
            rfm_transaction_table STD
        inner join rfm_segment_configuration f on f.company_id = STD.company_id
        inner join setu_rfm_segment srs on srs.id = f.segment_id
        where
             STD.total_orders >= f.from_frequency AND
             STD.total_orders <= f.to_frequency AND
             round(STD.total_order_value/STD.total_orders,2) >= f.from_atv AND
             round(STD.total_order_value/STD.total_orders,2) <= f.to_atv AND
             STD.total_order_value >= f.from_amount AND
             STD.total_order_value <= f.to_amount AND
             STD.days_from_last_purchase >= f.from_days AND
             STD.days_from_last_purchase <= f.to_days)STD
			 where
             STD.row_num = 1;

        IF segment_type = 'sales_team' THEN
             Drop Table if exists rfm_analysis_team;
             CREATE TEMPORARY TABLE rfm_analysis_team(
               rfm_segment_id integer, team_id integer,  customer_id integer, sale_ids integer[],pos_ids integer[],
               total_orders integer, total_order_value numeric, days_from_last_purchase integer,
               atv numeric, row_num bigint);
            Insert into rfm_analysis_team
            Select * from
            (Select
                srs.id,
                STD.team_id,
                STD.customer_id,
                STD.sale_ids,
                STD.pos_ids,
                STD.total_orders,
                STD.total_order_value,
                STD.days_from_last_purchase,
                round(STD.total_order_value/STD.total_orders,2) as average,
                row_number() over(
                    PARTITION BY
                    STD.customer_id,
                    STD.team_id
                ORDER BY
                    srs.seq)as row_num
            From
                rfm_transaction_table_team STD
            inner join rfm_segment_team_configuration f on f.team_id = STD.team_id
            inner join setu_rfm_segment srs on srs.id = f.segment_id
            where
                 STD.total_orders >= f.from_frequency AND
                 STD.total_orders <= f.to_frequency AND
                 round(STD.total_order_value/STD.total_orders,2) >= f.from_atv AND
                 round(STD.total_order_value/STD.total_orders,2) <= f.to_atv AND
                 STD.total_order_value >= f.from_amount AND
                 STD.total_order_value <= f.to_amount AND
                 STD.days_from_last_purchase >= f.from_days AND
                 STD.days_from_last_purchase <= f.to_days)STD
                 where
                 STD.row_num = 1;
        END IF;
    END;
    $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
