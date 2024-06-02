DROP FUNCTION if exists public.get_sales_data_for_rfm(integer[],date, date, character varying);
CREATE OR REPLACE FUNCTION public.get_sales_data_for_rfm(
IN company_ids integer[],
IN start_date date,
IN end_date date,
IN segment_type character varying)
RETURNS void AS
$BODY$

BEGIN

IF (select state from ir_module_module where name = 'setu_rfm_analysis_extended') = 'installed' THEN
PERFORM gather_sales_and_pos_data(company_ids,start_date,end_date);
ELSE
PERFORM gather_sales_data(company_ids,start_date,end_date);
END IF;

Drop Table if exists rfm_transaction_table;
CREATE TEMPORARY TABLE rfm_transaction_table(
    company_id integer,  customer_id integer,
    total_orders integer, total_order_value numeric,
    days_from_last_purchase integer,sale_ids integer[], pos_ids integer[]
);

insert into rfm_transaction_table
Select
    foo.company_id,
    foo.partner_id,
    count(foo.so_id) + count(foo.pos_id) as total_orders,
    sum(coalesce(foo.amount_total_per_line, 0) + coalesce(foo.tax_amount, 0)) as total_order_value,
    DATE_PART('day', now()::timestamp - max(foo.date_order)::timestamp) as days_from_last_purchase,
    array_agg(foo.so_id) sale_ids,
    array_agg(foo.pos_id) pos_ids
From sales_data foo
group by foo.partner_id,foo.company_id;

IF segment_type = 'sales_team' THEN
    Drop Table if exists rfm_transaction_table_team;
    CREATE TEMPORARY TABLE rfm_transaction_table_team(
        team_id integer,  customer_id integer,
        total_orders integer, total_order_value numeric,
        days_from_last_purchase integer,sale_ids integer[], pos_ids integer[]
    );
    insert into rfm_transaction_table_team
    Select
        foo.team_id,
        foo.partner_id,
        count(foo.so_id) + count(foo.pos_id) as total_orders,
        sum(coalesce(foo.amount_total_per_line, 0) + coalesce(foo.tax_amount, 0)) as total_order_value,
        DATE_PART('day', now()::timestamp - max(foo.date_order)::timestamp) as days_from_last_purchase,
        array_agg(foo.so_id) sale_ids,
        array_agg(foo.pos_id) pos_ids
    From sales_data foo
    group by foo.partner_id,foo.team_id;
END IF;


END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
