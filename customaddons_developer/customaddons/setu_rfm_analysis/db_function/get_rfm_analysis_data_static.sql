DROP FUNCTION if exists public.get_rfm_analysis_data_static(integer[],date, date, character varying);

CREATE OR REPLACE FUNCTION public.get_rfm_analysis_data_static(
IN company_ids integer[],
IN start_date date,
IN end_date date,
IN segment_type character varying)
RETURNS TABLE(company_id integer, customer_id integer,sale_ids integer[], total_orders integer, total_order_value numeric, days_from_last_purchase integer, recency integer, frequency integer, monetization integer, score character varying, score_id integer, segment_id integer) AS
$BODY$
    BEGIN
        Drop Table if exists rfm_analysis;
        CREATE TEMPORARY TABLE rfm_analysis(
            company_id integer,  customer_id integer, sale_ids integer[], pos_ids integer[],
            total_orders integer, total_order_value numeric, days_from_last_purchase integer,
            recency integer, frequency integer, monetization integer, score character varying,
            rfm_score_id integer, rfm_segment_id integer,row_num bigint);

        Drop Table if exists rfm_analysis_team;
        CREATE TEMPORARY TABLE rfm_analysis_team(
            team_id integer,  customer_id integer, sale_ids integer[], pos_ids integer[],
            total_orders integer, total_order_value numeric, days_from_last_purchase integer,
            recency integer, frequency integer, monetization integer, score character varying,
            rfm_score_id integer, rfm_segment_id integer,row_num bigint);

        PERFORM get_sales_data_for_rfm(company_ids,start_date,end_date,segment_type);
        --Return Query
        with all_data as (
            Select
            row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.days_from_last_purchase) as recency_id,
            row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.total_orders desc) as frequency_id,
            row_number() over(partition by rtt.company_id order by rtt.company_id, rtt.total_order_value desc) as monetization_id,
            *
            from rfm_transaction_table rtt
        ),
        customer_count as (
            Select rtt.company_id, count(rtt.customer_id) as total_customers from rfm_transaction_table rtt
            group by rtt.company_id
        )

        Insert into rfm_analysis
        Select D.*, (D.recency::char || D.frequency::char || D.monetization::char)::character varying as score,
            rsc.id as score_id,
            rsc.rfm_segment_id,1::bigint
        from
        (
            Select
                ad.company_id,
                ad.customer_id,
                ad.sale_ids,
                ad.pos_ids,
                ad.total_orders,
                coalesce(ad.total_order_value,0) as total_order_value,
                ad.days_from_last_purchase,
                case
                    when ((recency_id * 100.0) / total_customers) < 26 then 1
                    when ((recency_id * 100.0) / total_customers) >= 26 and ((recency_id * 100.0) / total_customers) < 51 then 2
                    when ((recency_id * 100.0) / total_customers) >= 51 and ((recency_id * 100.0) / total_customers) < 76 then 3
                    when ((recency_id * 100.0) / total_customers) >= 76 then 4
                end as recency,
                case
                    when ((frequency_id * 100.0) / total_customers) < 26 then 1
                    when ((frequency_id * 100.0) / total_customers) >= 26 and ((frequency_id * 100.0) / total_customers) < 51 then 2
                    when ((frequency_id * 100.0) / total_customers) >= 51 and ((frequency_id * 100.0) / total_customers) < 76 then 3
                    when ((frequency_id * 100.0) / total_customers) >= 76 then 4
                end as frequency,
                case
                    when ((monetization_id * 100.0) / total_customers) < 26 then 1
                    when ((monetization_id * 100.0) / total_customers) >= 26 and ((monetization_id * 100.0) / total_customers) < 51 then 2
                    when ((monetization_id * 100.0) / total_customers) >= 51 and ((monetization_id * 100.0) / total_customers) < 76 then 3
                    when ((monetization_id * 100.0) / total_customers) >= 76 then 4
                end as monetization
            From
                all_data ad
                    Inner Join customer_count cc on cc.company_id = ad.company_id
        )D
            Inner Join setu_rfm_score rsc on rsc.name = (D.recency::char || D.frequency::char || D.monetization::char)::character varying;

        IF segment_type = 'sales_team' THEN

            with all_data as (
                Select
                row_number() over(partition by rtt.team_id order by rtt.team_id, rtt.days_from_last_purchase) as recency_id,
                row_number() over(partition by rtt.team_id order by rtt.team_id, rtt.total_orders desc) as frequency_id,
                row_number() over(partition by rtt.team_id order by rtt.team_id, rtt.total_order_value desc) as monetization_id,
                *
                from rfm_transaction_table_team rtt
            ),
            customer_count as (
                Select rtt.team_id, count(rtt.customer_id) as total_customers from rfm_transaction_table_team rtt
                group by rtt.team_id
            )

            Insert into rfm_analysis_team
            Select D.*, (D.recency::char || D.frequency::char || D.monetization::char)::character varying as score,
                rsc.id as score_id,
                srst.id, 1::bigint
            from
            (
                Select
                    ad.team_id,
                    ad.customer_id,
                    ad.sale_ids,
                    ad.pos_ids,
                    ad.total_orders,
                    coalesce(ad.total_order_value,0) as total_order_value,
                    ad.days_from_last_purchase,
                    case
                        when ((recency_id * 100.0) / total_customers) < 26 then 1
                        when ((recency_id * 100.0) / total_customers) >= 26 and ((recency_id * 100.0) / total_customers) < 51 then 2
                        when ((recency_id * 100.0) / total_customers) >= 51 and ((recency_id * 100.0) / total_customers) < 76 then 3
                        when ((recency_id * 100.0) / total_customers) >= 76 then 4
                    end as recency,
                    case
                        when ((frequency_id * 100.0) / total_customers) < 26 then 1
                        when ((frequency_id * 100.0) / total_customers) >= 26 and ((frequency_id * 100.0) / total_customers) < 51 then 2
                        when ((frequency_id * 100.0) / total_customers) >= 51 and ((frequency_id * 100.0) / total_customers) < 76 then 3
                        when ((frequency_id * 100.0) / total_customers) >= 76 then 4
                    end as frequency,
                    case
                        when ((monetization_id * 100.0) / total_customers) < 26 then 1
                        when ((monetization_id * 100.0) / total_customers) >= 26 and ((monetization_id * 100.0) / total_customers) < 51 then 2
                        when ((monetization_id * 100.0) / total_customers) >= 51 and ((monetization_id * 100.0) / total_customers) < 76 then 3
                        when ((monetization_id * 100.0) / total_customers) >= 76 then 4
                    end as monetization
                From
                    all_data ad
                        Inner Join customer_count cc on cc.team_id = ad.team_id
            )D
                Inner Join setu_rfm_score rsc on rsc.name = (D.recency::char || D.frequency::char || D.monetization::char)::character varying
                Inner Join setu_rfm_segment srst on srst.parent_id = rsc.rfm_segment_id and srst.crm_team_id = D.team_id;
        END IF;


    END;
    $BODY$
LANGUAGE plpgsql VOLATILE
COST 100
ROWS 1000;
