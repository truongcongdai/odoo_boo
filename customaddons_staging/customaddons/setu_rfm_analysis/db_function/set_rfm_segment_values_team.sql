DROP FUNCTION if exists public.set_rfm_segment_values_team(integer[], date, character varying);

CREATE OR REPLACE FUNCTION public.set_rfm_segment_values_team(
    company_ids integer[],
    end_date date,
    calculation_type character varying)
RETURNS void AS
$BODY$
    BEGIN

    delete from partner_segments where company_id = ANY(company_ids) or company_id is null;
    IF calculation_type = 'static' THEN
       insert into partner_segments(partner_id,segment_id,team_id,score_id)
       select customer_id,rfm_segment_id,team_id,rfm_score_id from rfm_analysis_team where row_num = 1 and rfm_segment_id is not null;
    ELSE
       insert into partner_segments(partner_id,segment_id,team_id,score_id)
       select customer_id,rfm_segment_id,team_id,null as score_id from rfm_analysis_team where row_num = 1 and rfm_segment_id is not null;
    END IF;


    update sale_order so set rfm_team_segment_id = null where rfm_team_segment_id is not null;
    update sale_order so set rfm_team_segment_id = orders.rfm_segment_id from
    (
    select unnest(sale_ids)as id,rfm_segment_id from rfm_analysis_team where row_num = 1 and rfm_segment_id is not null
    )orders
    where orders.id = so.id;


    IF (select state from ir_module_module where name = 'setu_rfm_analysis_extended') = 'installed' THEN
        update pos_order p set rfm_team_segment_id = null where rfm_team_segment_id is not null;
        update pos_order p set rfm_team_segment_id = pso.rfm_segment_id from
        (
        select unnest(pos_ids)as id,rfm_segment_id from rfm_analysis_team where row_num = 1 and rfm_segment_id is not null
        )pso
        where pso.id = p.id;
    END IF;


    insert into rfm_partner_team_history(partner_id,team_id,current_segment,previous_segment,date_changed)
    select
        ps.partner_id,
        ps.team_id,
        ps.segment_id,
        (select
            ps2.current_segment
         from
            rfm_partner_team_history ps2
         where

            ps2.partner_id = ps.partner_id
            and ps2.team_id = ps.team_id
            order by ps2.date_changed desc
         limit 1
        ) as previous_segment,
        (select now()::timestamp) as date_changed
    from
        (select
                customer_id as partner_id,
                team_id,
                rfm_segment_id as segment_id
            from rfm_analysis_team
            where row_num = 1) ps
    where
        ps.segment_id !=  coalesce((select
            ps2.current_segment
         from
            rfm_partner_team_history ps2
         where
            ps2.partner_id = ps.partner_id
            and ps2.team_id = ps.team_id
         order by ps2.date_changed desc
         limit 1
        ),0);
    END;
    $BODY$
LANGUAGE plpgsql VOLATILE
COST 100;