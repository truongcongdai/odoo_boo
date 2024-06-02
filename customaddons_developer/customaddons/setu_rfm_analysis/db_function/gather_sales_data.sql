DROP FUNCTION if exists public.gather_sales_data(integer[], date, date);
CREATE OR REPLACE FUNCTION public.gather_sales_data(
IN company_ids integer[],
IN start_date date,
IN end_date date)
RETURNS void AS
$BODY$

BEGIN

Drop Table if exists sales_data;
CREATE TEMPORARY TABLE sales_data(
so_id integer,
pos_id integer,
team_id integer,
company_id integer,
partner_id integer,
date_order date,
amount_total_per_line numeric,
tax_amount numeric
);

Insert into sales_data
Select
    so.id as so_id,
    null::integer as pos_id,
    so.team_id,
    so.company_id,
    case when rp.parent_id is null then so.partner_id else rp.parent_id end as partner_id,
    so.date_order::date,
    sum(case when source.usage = 'internal'
        then (sml.qty_done * sol.price_unit) /CASE COALESCE(so.currency_rate, 0::numeric) WHEN 0 THEN 1.0 ELSE so.currency_rate END
    else (-1 *sml.qty_done * sol.price_unit) /CASE COALESCE(so.currency_rate, 0::numeric) WHEN 0 THEN 1.0 ELSE so.currency_rate END
    end) as amount_total_per_line,

    sum(case when tax.price_include != 'true' then
        case when source.usage = 'internal' then
            (sml.qty_done * sol.price_unit) /CASE COALESCE(so.currency_rate, 0::numeric) WHEN 0 THEN 1.0ELSE so.currency_rate END
            else (-1 *sml.qty_done * sol.price_unit) /CASE COALESCE(so.currency_rate, 0::numeric) WHEN 0 THEN 1.0 ELSE so.currency_rate
         END

        end else 0 end * (tax.amount /100)) as tax_amount
From
    stock_move move
    Inner Join stock_move_line sml on sml.move_id = move.id
    Inner Join sale_order_line sol on sol.id = move.sale_line_id
    left join account_tax_sale_order_line_rel tax_rel on sale_order_line_id = sol.id
    left join account_tax tax on tax.id = account_tax_id
    Inner join sale_order so on so.id = sol.order_id
    Inner Join stock_location source on source.id = move.location_id
    Inner Join stock_location dest on dest.id = move.location_dest_id
    Left Join stock_warehouse source_warehouse ON source.parent_path::text ~~ concat('%/', source_warehouse.view_location_id, '/%')
    Left Join stock_warehouse dest_warehouse ON dest.parent_path::text ~~ concat('%/', dest_warehouse.view_location_id, '/%')
    Inner join res_partner rp on rp.id = so.partner_id
    Inner join res_company rc on rc.id = so.company_id
where
     1 = case when start_date is null
     then case when DATE_PART('day', now()::timestamp - so.date_order::timestamp)::integer <= rc.take_sales_from_x_days::integer then 1 else 0 end
     else case when so.date_order >= start_date then 1 else 0 end
     end

     and so.date_order::date <= end_date

     and 1 = case when array_length(company_ids,1) >= 1 then
     case when so.company_id = ANY(company_ids) then 1 else 0 end
     else 1 end

     and move.state = 'done'
group by so.id,so.team_id,so.company_id,so.partner_id, rp.parent_id,so.date_order;

END;
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
