DROP FUNCTION if exists public.set_rfm_segment_values_company(integer[], date, character varying);

CREATE OR REPLACE FUNCTION public.set_rfm_segment_values_company(
    company_ids integer[],
    end_date date,
    calculation_type character varying)
RETURNS void AS
$BODY$
    BEGIN
        update sale_order set rfm_segment_id = null where rfm_segment_id is not null;
        update sale_order so set rfm_segment_id = sale_segment.rfm_segment_id from
        (
            select
                unnest(sale_ids) as id,
                rfm_segment_id
            from
                rfm_analysis
        )sale_segment
        where sale_segment.id = so.id;
        IF (select state from ir_module_module where name = 'setu_rfm_analysis_extended') = 'installed' THEN
            update pos_order set rfm_segment_id = null where rfm_segment_id is not null;
            update pos_order p set rfm_segment_id = pos_segment.rfm_segment_id from
            (
                select
                    unnest(pos_ids) as p_id,
                    rfm_segment_id
                from
                    rfm_analysis
            )pos_segment
            where pos_segment.p_id = p.id;
        END IF;

    update ir_property as ip
       set
         value_reference = null
       where
         ip.name in ('rfm_segment_id','rfm_score_id') and
         ip.fields_id in (select id from ir_model_fields where name in ('rfm_segment_id','rfm_score_id') and model = 'res.partner');

    insert into ir_property(fields_id,type,name,res_id,company_id)
    (
    select
            (select id from ir_model_fields where name = 'rfm_segment_id' and model = 'res.partner')as field,
            'many2one' as type,'rfm_segment_id' as name,
            concat('res.partner,',id)as res,
            company_id
         from
            (
                select
                    id,
                    company_id
                from
                    (
                     select
                     id, unnest((select array_agg(distinct id) from res_company where id = any(company_ids))) as company_id
                     from
                     res_partner
                    )as pc
             where
                (id,company_id) not in
                (select
                    substring(res_id,13)::integer,company_id
                 from
                    ir_property
                 where
                    name = 'rfm_segment_id' and
                    company_id = any(company_ids) and
                    fields_id = (select id from ir_model_fields where name = 'rfm_segment_id' and model = 'res.partner')
                                )

            )as IP
    );
    update ir_property as ip
       set
         value_reference = pr.rfm_segment_id
       from
       (
            select
                partner_id,
                company_id,
                concat('setu.rfm.segment,',rfm_segment_id)as rfm_segment_id
            from
                (select
                    customer_id as partner_id,
                    company_id,
                    rfm_segment_id
                from rfm_analysis
                where company_id = any(company_ids)
                )cw_data
       )as pr
         where
         ip.company_id = pr.company_id and
         ip.res_id = concat('res.partner,',pr.partner_id) and
         ip.name = 'rfm_segment_id' and
         ip.fields_id = (select id from ir_model_fields where name = 'rfm_segment_id' and model = 'res.partner');



    IF calculation_type = 'static' THEN
        insert into ir_property(fields_id,type,name,res_id,company_id)
        (
        select
                (select id from ir_model_fields where name = 'rfm_score_id' and model = 'res.partner')as field,
                'many2one' as type,'rfm_score_id' as name,
                concat('res.partner,',id)as res,
                company_id
             from
                (
                    select
                        id,
                        company_id
                    from
                        (
                         select
                         id, unnest((select array_agg(distinct id) from res_company where id = any(company_ids))) as company_id
                         from
                         res_partner
                        )as pc
                 where
                    (id,company_id) not in
                    (select
                        substring(res_id,13)::integer,company_id
                     from
                        ir_property
                     where
                        name = 'rfm_score_id' and
                        company_id = any(company_ids) and
                        fields_id = (select id from ir_model_fields where name = 'rfm_score_id' and model = 'res.partner')
                                    )

                )as IP
        );

        update ir_property as ip
           set
             value_reference = pr.rfm_score_id
           from
           (
                select
                    partner_id,
                    company_id,
                    concat('setu.rfm.score,',rfm_score_id)as rfm_score_id
                from
                    (select
                        customer_id as partner_id,
                        company_id,
                        rfm_score_id
                    from rfm_analysis
                    where company_id = any(company_ids)
                    )cw_data
           )as pr
             where
             ip.company_id = pr.company_id and
             ip.res_id = concat('res.partner,',pr.partner_id) and
             ip.name = 'rfm_score_id' and
             ip.fields_id = (select id from ir_model_fields where name = 'rfm_score_id' and model = 'res.partner');
    END IF;

    insert into rfm_partner_history(partner_id,company_id,current_segment,previous_segment,date_changed)
        select
            ps.partner_id,
            ps.company_id,
            ps.segment_id,
            (select
                ps2.current_segment
             from
                rfm_partner_history ps2
             where

                ps2.partner_id = ps.partner_id
                and ps2.company_id = ps.company_id
                order by ps2.date_changed desc
             limit 1
            ) as previous_segment,
            (select now()::timestamp without time zone) as date_changed
        from
            (select
                    customer_id as partner_id,
                    company_id,
                    rfm_segment_id as segment_id
                from rfm_analysis
                where company_id = any(company_ids) and row_num = 1) ps
        where
            ps.company_id = any(company_ids) and
            ps.segment_id !=  coalesce((select
                ps2.current_segment
             from
                rfm_partner_history ps2
             where

                ps2.partner_id = ps.partner_id
                and ps2.company_id = ps.company_id
             order by ps2.date_changed desc
             limit 1
            ),0);

    END;
    $BODY$
LANGUAGE plpgsql VOLATILE
COST 100;