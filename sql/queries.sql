-- SQLite
select * from portfolio_state;
select * from portfolio_info;
select * from positions;

--delete from portfolio_info
--where date = '2024-04-26';

delete from portfolio_state
where portfolio_script_run_id = '6b6f1fa3-028c-43d9-b1d3-a0010d24b214';

delete from portfolio_info
where portfolio_script_run_id = '6b6f1fa3-028c-43d9-b1d3-a0010d24b214';


