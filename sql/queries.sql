-- SQLite
select * from portfolio_state;
select * from portfolio_info;
select * from positions;
select * from whole_portfolio_state;
select * from strategy_state;
select * from symbol_state;

--delete from portfolio_info
--where date = '2024-04-26';

delete from portfolio_state
where portfolio_script_run_id IN ('99fe02eb-1722-474c-b7df-8b3c632b55c3',
    '4e580c64-d39d-439c-bba5-6abc6550af59',
    'c6850d85-4707-47c3-bc87-c9d56415bd24',
    '280e3bef-0fec-4c1f-9234-9a33a1d192c4',
    'ae708cfb-f7c3-4265-b040-20d10b800758',
     '8fb8b06d-71d9-4bea-bb28-00ebc7b27284'
            );

delete from portfolio_info
where portfolio_script_run_id IN ('99fe02eb-1722-474c-b7df-8b3c632b55c3',
    '4e580c64-d39d-439c-bba5-6abc6550af59',
    'c6850d85-4707-47c3-bc87-c9d56415bd24',
    '280e3bef-0fec-4c1f-9234-9a33a1d192c4',
    'ae708cfb-f7c3-4265-b040-20d10b800758',
     '8fb8b06d-71d9-4bea-bb28-00ebc7b27284'
            );

delete from positions
where portfolio_script_run_id IN ('99fe02eb-1722-474c-b7df-8b3c632b55c3',
    '4e580c64-d39d-439c-bba5-6abc6550af59',
    'c6850d85-4707-47c3-bc87-c9d56415bd24',
    '280e3bef-0fec-4c1f-9234-9a33a1d192c4',
    'ae708cfb-f7c3-4265-b040-20d10b800758',
     '8fb8b06d-71d9-4bea-bb28-00ebc7b27284'
            );

delete from whole_portfolio_state
where portfolio_script_run_id in (
    '4e580c64-d39d-439c-bba5-6abc6550af59',
    'c6850d85-4707-47c3-bc87-c9d56415bd24',
    '280e3bef-0fec-4c1f-9234-9a33a1d192c4',
    'ae708cfb-f7c3-4265-b040-20d10b800758');

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
--     absolute_return REAL,
--     symbols_with_zero_trades_cnt INT,
--     all_symbols_cnt INT,
--     symbols_to_open_cnt INT,
--     symbols_to_close_cnt INT);

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
--     absolute_return REAL,
--     symbols_with_zero_trades_cnt INT,
--     all_symbols_cnt INT,
--     symbols_to_open_cnt INT,
--     symbols_to_close_cnt INT);

-- insert into portfolio_state
-- select * from portfolio_state_added_cols;

-- select * from portfolio_state;

-- create table whole_portfolio_state (
--     timestamp DATETIME, 
--     date DATE, 
--     portfolio_script_run_id TEXT,
--     equity REAL,
--     last_equity REAL,
--     cash REAL,
--     long_market_value REAL,
--     short_market_value REAL,
--     non_marginable_buying_power REAL,
--     deposits_withdrawals REAL,
--     subportfolios_cnt INT,
--     subportfolios_allocation REAL,
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

-- DROP TABLE IF EXISTS strategy_state;
-- CREATE TABLE strategy_state(
--     timestamp DATETIME, 
--     date DATE, 
--     portfolio_script_run_id TEXT, 
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
--     absolute_return REAL,
--     symbols_with_zero_trades_cnt INT,
--     all_symbols_cnt INT,
--     symbols_to_open_cnt INT,
--     symbols_to_close_cnt INT
--         );

CREATE TABLE symbol_state (
    timestamp DATETIME, 
    date DATE, 
    portfolio_script_run_id TEXT, 
    symbol TEXT,
    is_open TEXT,
    open_trade_PL REAL, 
    open_trade_total_return REAL,
    cost_basis REAL, 
    daily_return REAL,
    last_day_close REAL,
    current_price REAL,
    market_value REAL,
    quantity REAL,
    trade_opened DATE,
    days_opened INT,        
    closed_trades_cnt INT, 
    closed_trades_PL REAL, 
    days_since_last_closed_trade INT,
    win_rate REAL, 
    sharpe_ratio REAL, 
    calmar_ratio REAL,
    sortino_ratio REAL,
    total_return REAL,
    max_drawdown REAL,
    max_drawdown_duration INT,
    absolute_return REAL
    );