-- SQLite
select * from portfolio_state;
select * from portfolio_info;
select * from positions;

--delete from portfolio_info
--where date = '2024-04-26';

delete from portfolio_state
where portfolio_script_run_id IN ('73de3c32-3b6a-4705-8d82-14a65f8c6ab0')
            ;

delete from portfolio_info
where portfolio_script_run_id IN ('73de3c32-3b6a-4705-8d82-14a65f8c6ab0');

delete from positions
where portfolio_script_run_id IN ('73de3c32-3b6a-4705-8d82-14a65f8c6ab0');


