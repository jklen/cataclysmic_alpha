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
    absolute_return REAL);""")

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