import sqlite3
import os

con = sqlite3.connect('../db/calpha.db')

# create portfolio_info table

con.execute("DROP TABLE IF EXISTS portfolio_info;")
con.execute("""CREATE TABLE portfolio_info(
            timestamp DATETIME, 
            date DATE, 
            portfolio_script_run_id TEXT, 
            portfolio_name TEXT, 
            symbol TEXT, 
            strategy TEXT, 
            strategy_params TEXT, 
            stoploss REAL, 
            take_profit REAL, 
            weights_initial TEXT, 
            weights_running TEXT, 
            running_params TEXT, 
            portfolio_size INT, 
            data_preference TEXT);""")

# create porfolio_state table

con.execute("DROP TABLE IF EXISTS portfolio_state;")
con.execute("""CREATE TABLE portfolio_state(
    timestamp DATETIME, 
    date DATE, 
    portfolio_script_run_id TEXT, 
    portfolio_name TEXT, 
    portfolio_size INT, 
    available_cash REAL, 
    equity REAL, 
    open_trades_cnt INT, 
    open_trades_symbols TEXT, 
    open_trades_PL REAL, 
    open_trades_cost_basis_sum REAL, 
    closed_trades_cnt INT, 
    closed_trades_PL REAL, 
    win_rate REAL, 
    sharpe_ratio REAL, 
    calmar_ratio REAL,
    sortino_ratio REAL,
    total_return REAL,
    max_drawdown REAL,
    max_drawdown_duration INT,
    daily_return REAL,
    absolute_return REAL,
    symbols_with_zero_trades_cnt INT,
    all_symbols_cnt INT,
    symbols_to_open_cnt INT,
    symbols_to_close_cnt INT);""")

# create positions table

con.execute("DROP TABLE IF EXISTS positions;")
con.execute("""CREATE TABLE positions(
    timestamp DATETIME, 
    date DATE, 
    portfolio_script_run_id TEXT, 
    portfolio_name TEXT, 
    symbol TEXT, 
    is_open TEXT, 
    weight REAL, 
    position REAL, 
    portfolio_size REAL, 
    base REAL, 
    available_cash REAL, 
    min_available_cash REAL);""")

# whole portfolio state table

con.execute('drop table if exists whole_portfolio_state;')
con.execute("""create table whole_portfolio_state (
    timestamp DATETIME, 
    date DATE, 
    portfolio_script_run_id TEXT,
    equity REAL,
    last_equity REAL,
    cash REAL,
    long_market_value REAL,
    short_market_value REAL,
    non_marginable_buying_power REAL,
    deposits_withdrawals REAL,
    subportfolios_cnt INT,
    subportfolios_allocation REAL,
    open_trades_cnt INT, 
    open_trades_symbols TEXT, 
    open_trades_PL REAL, 
    open_trades_cost_basis_sum REAL, 
    closed_trades_cnt INT, 
    closed_trades_PL REAL, 
    win_rate REAL, 
    sharpe_ratio REAL, 
    calmar_ratio REAL,
    sortino_ratio REAL,
    total_return REAL,
    max_drawdown REAL,
    max_drawdown_duration INT,
    daily_return REAL,
    absolute_return REAL);""")

#TODO 2 nove stlpce - symbols_to_open_cnt, symbols_to_close_cnt

# strategy_state table

con.execute("DROP TABLE IF EXISTS strategy_state;")
con.execute("""CREATE TABLE strategy_state(
    timestamp DATETIME, 
    date DATE, 
    portfolio_script_run_id TEXT, 
    strategy TEXT,
    open_trades_cnt REAL,
    open_trades_symbols TEXT,
    open_trades_PL REAL, 
    open_trades_total_return REAL,
    cost_basis REAL, 
    market_value REAL,
    long_positions_cnt REAL, 
    short_positions_cnt REAL,
    daily_return REAL,
    closed_trades_cnt REAL, 
    closed_trades_PL REAL, 
    closed_winning_trades_cnt REAL,
    win_rate REAL, 
    sharpe_ratio REAL, 
    calmar_ratio REAL,
    sortino_ratio REAL,
    total_return REAL,
    max_drawdown REAL,
    max_drawdown_duration REAL,
    absolute_return REAL,
    symbols_with_zero_trades_cnt REAL,
    symbols_cnt REAL,
    symbols_to_open_cnt REAL,
    symbols_to_close_cnt REAL
    );""")

# symbol table

con.execute("DROP TABLE IF EXISTS symbol_state;")
con.execute("""CREATE TABLE symbol_state(
    timestamp DATETIME, 
    date DATE, 
    portfolio_script_run_id TEXT, 
    symbol TEXT,
    portfolio TEXT,
    strategy TEXT,
    is_open TEXT,
    open_trade_PL REAL, 
    open_trade_total_return REAL,
    cost_basis REAL, 
    daily_return REAL,
    last_day_close REAL,
    current_price REAL,
    market_value REAL,
    quantity REAL,
    side TEXT, 
    trade_opened DATE,
    days_opened REAL,        
    closed_trades_cnt INT, 
    closed_trades_PL REAL, 
    last_closed_trade_at DATE,
    days_since_last_closed_trade INT,
    closed_winning_trades_cnt INT,
    win_rate REAL, 
    sharpe_ratio REAL, 
    calmar_ratio REAL,
    sortino_ratio REAL,
    total_return REAL,
    max_drawdown REAL,
    max_drawdown_duration INT,
    absolute_return REAL
    );""")
con.commit()
con.close()


# create strategy table NOT YET

# con.execute("DROP TABLE IF EXISTS strategy;")
# con.execute("""CREATE TABLE strategy(
#     timestamp DATETIME, 
#     date DATE, 
#     portfolio_script_run_id TEXT, 
#     portfolio_name TEXT, 
#     symbol TEXT, 
#     datasource TEXT,
#     hist_date DATETIME,
#     close_price REAL,
#     entries BOOL,
#     exits BOOL
#     );""")
# con.commit()
# con.close()

# # create trades table NOT YET

# con.execute("DROP TABLE IF EXISTS backtest_trades;")
# con.execute("""CREATE TABLE backtest_trades(
#     timestamp DATETIME, 
#     date DATE, 
#     portfolio_script_run_id TEXT, 
#     portfolio_name TEXT, 
#     symbol TEXT, 
#     trade_entry_date DATETIME,
#     trade_exit_date DATETIME
#     avg_entry_price REAL,
#     avg_exit_price REAL,
#     pl REAL,
#     return REAL
#     );""")
# con.commit()
# con.close()