-- SQLite
select * from portfolio_state;
select * from portfolio_info;
select * from positions;

--delete from portfolio_info
--where date = '2024-04-26';

delete from portfolio_state
where portfolio_script_run_id IN ('99fe02eb-1722-474c-b7df-8b3c632b55c3',
    'd0d2ebfa-76dd-45a6-a545-0e319d2d9dc1',
    'bf0ae8d0-86d6-46ee-b3a8-6b1f03715906',
    '501f1907-89c5-41cf-a674-2ed8a7f248e9',
    '204690e2-40da-490b-81c0-921764db6731',
     '8fb8b06d-71d9-4bea-bb28-00ebc7b27284'
            );

delete from portfolio_info
where portfolio_script_run_id IN ('99fe02eb-1722-474c-b7df-8b3c632b55c3',
    '42178984-e181-45bb-8df0-e743700847c6',
    'd0d2ebfa-76dd-45a6-a545-0e319d2d9dc1',
    '501f1907-89c5-41cf-a674-2ed8a7f248e9',
    '204690e2-40da-490b-81c0-921764db6731',
     '8fb8b06d-71d9-4bea-bb28-00ebc7b27284'
            );

delete from positions
where portfolio_script_run_id IN ('99fe02eb-1722-474c-b7df-8b3c632b55c3',
    'c1193016-3754-4194-b34d-3042ffe0e7e6',
    'd0d2ebfa-76dd-45a6-a545-0e319d2d9dc1',
    '501f1907-89c5-41cf-a674-2ed8a7f248e9',
    '204690e2-40da-490b-81c0-921764db6731',
     '8fb8b06d-71d9-4bea-bb28-00ebc7b27284'
            );

-- drop table if exists portfolio_state_added_cols;
-- create table portfolio_state_added_cols
-- (timestamp DATETIME, 
--     date DATE, 
--     portfolio_script_run_id TEXT, 
--     portfolio_name TEXT, 
--     portfolio_size INT, 
--     available_cash REAL, 
--     equity REAL, 
--     open_trades_cnt INT, 
--     open_trades_symbols TEXT, 
--     open_trades_PL REAL, 
--     open_trades_cost_basis_sum REAL, 
--     closed_trades_cnt INT, 
--     closed_trades_PL REAL, 
--     win_rate REAL, 
--     sharpe_ratio REAL, 
--     calmar_ratio REAL,
--     sortino_ratio REAL,
--     total_return REAL,
--     max_drawdown REAL,
--     max_drawdown_duration INT,
--     daily_return REAL,
--     absolute_return REAL);

-- select * from  portfolio_state_added_cols;

-- insert into portfolio_state_added_cols
-- select *, NULL, NULL from portfolio_state;

-- drop table portfolio_state;

-- create table portfolio_state
-- (timestamp DATETIME, 
--     date DATE, 
--     portfolio_script_run_id TEXT, 
--     portfolio_name TEXT, 
--     portfolio_size INT, 
--     available_cash REAL, 
--     equity REAL, 
--     open_trades_cnt INT, 
--     open_trades_symbols TEXT, 
--     open_trades_PL REAL, 
--     open_trades_cost_basis_sum REAL, 
--     closed_trades_cnt INT, 
--     closed_trades_PL REAL, 
--     win_rate REAL, 
--     sharpe_ratio REAL, 
--     calmar_ratio REAL,
--     sortino_ratio REAL,
--     total_return REAL,
--     max_drawdown REAL,
--     max_drawdown_duration INT,
--     daily_return REAL,
--     absolute_return REAL);

-- insert into portfolio_state
-- select * from portfolio_state_added_cols;




