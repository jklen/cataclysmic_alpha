from utils_strategy import HigherHighStrategy
import pandas as pd
import yaml
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import OrderRequest, GetOrdersRequest, GetOrderByIdRequest
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest, StockLatestTradeRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import pdb
from datetime import datetime, timedelta
import vectorbt as vbt
import uuid
import sqlite3
import ast
import logging
import quantstats as qs
import requests

logger = logging.getLogger(__name__)

keys = yaml.safe_load(open('../keys.yaml', 'r'))

strategies_directions = {
    'hhhl':'long'
}

crypto_map = {'BTC/USD':'BTCUSD', 'LINK/BTC':'LINKBTC'}

def review_positions():
    pass

def create_trading_client():
    trading_client = TradingClient(keys['paper_key'], keys['paper_secret'], paper=True)
    return trading_client

def closed_trades_cnt(symbols):
    logger.info(f"Calculating closed trades count")
    trading_client = create_trading_client()
    closed_trades = {}
    for symbol in symbols:
        request_params = GetOrdersRequest(
            status='closed',
            symbols=[symbol]
        )

        # long only strategies
        orders = trading_client.get_orders(filter=request_params)
        orders_dicts = map(dict, orders)
        keys_to_keep = ['symbol', 'filled_at', 'filled_qty', 'side']
        filtered_orders = [{key: value for key, value in d.items() if key in keys_to_keep} for d in orders_dicts]
        
        if len(filtered_orders) >= 2:
            df_orders = pd.DataFrame(filtered_orders)
            df_orders['side'] = df_orders['side'].apply(str)
            df_orders.sort_values(by = 'filled_at', inplace = True)
            df_orders[['filled_qty_lag', 'side_lag']] = df_orders[['filled_qty', 'side']].shift(1)
            
            df_trades = df_orders.loc[(df_orders['side'] == 'OrderSide.SELL') &
                                    (df_orders['side_lag'] == 'OrderSide.BUY') &
                                    (df_orders['filled_qty'] == df_orders['filled_qty_lag']),:]
            closed_trades[symbol] = len(df_trades)
        else:
            closed_trades[symbol] = 0
        
    return pd.Series(closed_trades, name = 'closed_trades_cnt')

def if_running_weights(symbols, weights_params):
    
    if weights_params['running'] == 'win_rate':
        s_closed_trades_cnt = closed_trades_cnt(symbols)
        symbols_meeting_min_trades_cnt = (s_closed_trades_cnt >= weights_params['running_params']['min_trades']).sum()
        
        if symbols_meeting_min_trades_cnt >= weights_params['running_params']['min_symbols']:
            return True
        else:
            return False
  
def calculate_win_rates(symbols):
    logger.info(f"Calculating win rates")
    trading_client = create_trading_client()
    win_rates = {}
    for symbol in symbols:
        request_params = GetOrdersRequest(
            status='closed',
            symbols=[symbol]
        )

        # long only strategies
        orders = trading_client.get_orders(filter=request_params)
        orders_dicts = map(dict, orders)
        keys_to_keep = ['symbol', 'filled_at', 'filled_qty', 'filled_avg_price', 'side']
        filtered_orders = [{key: value for key, value in d.items() if key in keys_to_keep} for d in orders_dicts]
        df_orders = pd.DataFrame(filtered_orders)
        df_orders['filled_qty'] = df_orders['filled_qty'].round(3)
        df_orders['side'] = df_orders['side'].apply(str)
        df_orders.sort_values(by = 'filled_at', inplace = True)
        df_orders[['filled_qty_lag', 'side_lag', 'filled_avg_price_lag']] = df_orders[['filled_qty', 'side', 'filled_avg_price']].shift(1)
        
        df_trades = df_orders.loc[(df_orders['side'] == 'OrderSide.SELL') &
                                (df_orders['side_lag'] == 'OrderSide.BUY') &
                                (df_orders['filled_qty'] == df_orders['filled_qty_lag']),:]
        df_trades.loc[:,['filled_qty', 'filled_avg_price', 'filled_avg_price_lag']] = df_trades.loc[:,['filled_qty', 'filled_avg_price', 'filled_avg_price_lag']].astype('Float32')
        df_trades['pl'] = (df_trades['filled_qty'] * df_trades['filled_avg_price']) - (df_trades['filled_qty'] * df_trades['filled_avg_price_lag'])
        wins_cnt = (df_trades['pl'] > 0).sum()
        losses_cnt = (df_trades['pl'] < 0).sum()
        win_rates[symbol] = wins_cnt/(wins_cnt + losses_cnt)
    
    return pd.Series(win_rates, name = 'win_rate')

def calculate_weights(series_metric, running_params):
    
    if series_metric.name == 'win_rate':
        closed_trades = closed_trades_cnt(series_metric.index.tolist())
        df = series_metric.to_frame()
        df = df.join(closed_trades.to_frame())
        
        mask_symbols_to_weight = df['closed_trades_cnt'] >= running_params['min_trades']
        symbols_with_min_weight_cnt = len(df) - mask_symbols_to_weight.sum()
        df['weight'] = running_params['min_weight']
        df.loc[mask_symbols_to_weight, 'weight'] = df.loc[mask_symbols_to_weight, 'win_rate']/df.loc[mask_symbols_to_weight, 'win_rate'].sum()
        df.loc[mask_symbols_to_weight, 'weight'] = (1-symbols_with_min_weight_cnt*running_params['min_weight']) * df.loc[mask_symbols_to_weight, 'weight']
        
        to_min_weight_mask = df['weight'] < running_params['min_weight']
        df.loc[to_min_weight_mask, 'weight'] = running_params['min_weight']
        calc = (1 - (df['weight'] == running_params['min_weight']).sum() * running_params['min_weight'])/(df.loc[df['weight'] > running_params['min_weight'], 'weight']).sum()
        df.loc[df['weight'] > running_params['min_weight'], 'weight'] = df.loc[df['weight'] > running_params['min_weight'], 'weight'] * calc
        
        return df['weight'].to_dict()

def check_weights(symbols, weights_params):
    logger.info(f"Calculating symbols weights")
    
    if (weights_params['initial'] == 'equal') & (weights_params['running'] == 'equal'):
        one_symbol_weight = 1./len(symbols)
        return {symbol:one_symbol_weight for symbol in symbols}
    else:
        if if_running_weights(symbols, weights_params):
            if weights_params['running'] == 'win_rate':
                series_metric = calculate_win_rates(symbols)
                print(series_metric)
            weights = calculate_weights(series_metric, weights_params['running_params'])
            return weights
        else: # initial
            if weights_params['initial'] == 'equal':
                one_symbol_weight = 1./len(symbols)
                return {symbol:one_symbol_weight for symbol in symbols}

def run_strategy(df_symbol, symbol, strategy, strategy_params):
    logger.info(f"{symbol} - running symbols strategy to get entries and exits")
    if strategy == 'hhhl':
        Strategy = HigherHighStrategy
    
    close_price = df_symbol['close']
    indicator = Strategy.run(close_price, **strategy_params)
    entries = indicator.entry_signal
    exits = indicator.exit_signal
    
    return entries, exits

def is_trading_day(day):
    # https://www.investopedia.com/ask/answers/06/stockexchangeclosed.asp
    # mozno podla alpacy - ma metodu na calendar
    
    us_stock_market_holidays = [datetime(2025, 1,1), datetime(2025, 1, 15), datetime(2025, 2, 19),
                            datetime(2024, 3, 29), datetime(2024, 5, 27), datetime(2024, 6, 19),
                            datetime(2024, 7, 4), datetime(2024, 9, 2), datetime(2024, 11, 28),
                            datetime(2024, 12, 25)]
    us_stock_market_holidays = map(lambda x: x.date(), us_stock_market_holidays)

    if (day.weekday() in [i for i in range(0,5)]) and \
        (day not in us_stock_market_holidays):
         return True
    else:
        return False   

def correct_date(symbol, last_day):
    logger.info(f"Checking if we have correct date")
    todays_date = datetime.today().date()
    
    if symbol in crypto_map.keys():
        if last_day == (todays_date - timedelta(days = 1)):
            return True
        else:
            return False
    else:
        today = is_trading_day(todays_date)
        today_1 = is_trading_day(todays_date - timedelta(days = 1))
        today_2 = is_trading_day(todays_date - timedelta(days = 2))
        today_3 = is_trading_day(todays_date - timedelta(days = 3))
        
        if today:
            if today_1: # yesterday was normal trading day
                if last_day == (todays_date - timedelta(days = 1)):
                    return True
                else:
                    return False
            elif not today_1 and today_2: # yesterday was holiday, and day before that was trading day
                if last_day == (todays_date - timedelta(days = 2)):
                    return True
                else:
                    return False
            elif not today_1 and not today_2: # it was weekend
                if last_day == (todays_date - timedelta(days = 3)):
                    return True
                else:
                    return False
            elif not today_1 and not today_2 and not today_3: # it was weekend + holiday
                if last_day == (todays_date - timedelta(days = 4)):
                    return True
                else:
                    return False
        else:
            return False # when script is run on non-trading days nothing happens - for regular stocks. Cryptos are 24/7

def eval_position(close_price, entries, exits, strategy_direction, stoploss, take_profit):
    logger.info(f"Evaluating symbol if to open, close, or no change")
    if strategy_direction == 'long':
        pf = vbt.Portfolio.from_signals(close_price, 
                                    entries, 
                                    exits,
                                    sl_stop = stoploss, 
                                    tp_stop = take_profit,
                                    direction='longonly',
                                    freq='1D')
        df_trades = pf.trades.records_readable
        last_date = close_price.tail(1).index[0].date()
        
        if last_date in list(df_trades['Entry Timestamp'].apply(lambda x:x.date())):
            return 'open'
        elif (last_date in list(df_trades['Exit Timestamp'].apply(lambda x:x.date()))) and \
                (df_trades['Status'].iloc[-1] == 'Closed'):
            return 'close'
        else:
            return 'no_change'
            
    elif strategy_direction == 'short':
        pass
    elif strategy_direction == 'long_and_short':
        pass
    pass

def close_positions(trades):
    logger.info(f"Submitting orders to close existing positions")
    # da ordre na zavretie pozice daneho symbolu
    trading_client = create_trading_client()
    
    for symbol in trades.keys():
        if trades[symbol] == 'close':
            try:
                trading_client.close_position(symbol)
            except:
                logger.warning(f"{symbol} - trying to close non-existing position")
    
def position_sizes(portfolio, min_avail_cash, weights, run_id, timestamp):
    # kalkulacia velkosti pozicii symbolov kde sa maju otvorit nove pozicie
    logger.info(f"Portfolio {portfolio} - calculating position sizes")
    
    con = sqlite3.connect('../db/calpha.db')
    df_portfolio = pd.read_sql(f"""SELECT * FROM portfolio_state WHERE portfolio_script_run_id = '{run_id}' AND
                     portfolio_name = '{portfolio}'""", con)
    open_symbols = ast.literal_eval(df_portfolio['open_trades_symbols'][0])
    
    available_cash = max(df_portfolio['available_cash'][0], min_avail_cash)
    if df_portfolio['available_cash'][0] < min_avail_cash:
        logger.warning('Increasing of the portfolio size because not having min available cash')
        portfolio_size = df_portfolio['portfolio_size'][0] + min_avail_cash - df_portfolio['available_cash'][0]
    else:
        portfolio_size = df_portfolio['portfolio_size'][0]
        
    df = pd.Series(weights, name = 'weight').to_frame() # symbol as index
    df.index = df.index.map(lambda x: crypto_map[x] if x in crypto_map else x)
    df['is_open'] = 'N'
    df.loc[open_symbols, 'is_open'] = 'Y'
    df['base'] = portfolio_size + df_portfolio['closed_trades_PL'][0]
    df['available_cash'] = available_cash
    df['position'] = df['weight'] * df['base']
    
    if df.loc[df['is_open'] == 'N', 'position'].sum() > available_cash:
        coef = available_cash/df.loc[df['is_open'] == 'N', 'position'].sum()
        df.loc[df['is_open'] == 'N', 'position'] = df.loc[df['is_open'] == 'N', 'position'] * coef
    
    # df to db

    df['portfolio_name'] = portfolio
    df['portfolio_script_run_id'] = run_id
    df['min_available_cash'] = min_avail_cash
    df['portfolio_size'] = portfolio_size
    df['timestamp'] = timestamp
    df['date'] = timestamp.date()
    df.reset_index(inplace=True)
    df.rename(columns = {'index':'symbol'}, inplace = True)
    df = df[['timestamp', 'date', 'portfolio_script_run_id', 'portfolio_name', 'symbol', 'is_open', 'weight', 'position', 
             'portfolio_size', 'base', 'available_cash', 'min_available_cash']]
    df.to_sql('positions', con, if_exists = 'append', index = False)
       
    con.close()
    return df.set_index('symbol')['position'].round(2) #df[['symbol', 'position']].set_index('symbol')

def open_positions(sizes, trades):
    logger.info(f"Submitting orders to open positions")
    trading_client = create_trading_client()
    for symbol in trades.keys():
        if trades[symbol] == 'open':
            params = OrderRequest(symbol = symbol,
                notional = sizes[symbol],
                side = 'buy',
                time_in_force = 'gtc' if symbol in crypto_map.values() else 'day',
                type = 'market',
                order_class = 'simple')

            trading_client.submit_order(params)
    

def update_portfolio_info(portfolio, config, run_id, timestamp):
    logger.info(f"Updating info of portfolio - {portfolio}")
    
    con = sqlite3.connect('../db/calpha.db')
    date = timestamp.date()
    weights_initial = config['weights']['initial']
    weights_running = config['weights']['running']
    try:
        running_params = str(config['weights']['running_params'])
    except:
        running_params = 'not_defined'
    portfolio_size = config['portfolio_size']
    data_preference = config['data_preference']
    
    for symbol in config['symbols'].keys():
            strategy = config['symbols'][symbol].keys()  
            strategy = list(strategy)[0]
            strategy_params = str(config['symbols'][symbol][strategy]['params'])
            stoploss = config['symbols'][symbol][strategy]['stoploss']
            take_profit = config['symbols'][symbol][strategy]['take_profit']
            data = (timestamp, date, run_id, portfolio, symbol, 
                    strategy, strategy_params, stoploss, take_profit, weights_initial, weights_running, running_params,
                    portfolio_size, data_preference)
            con.execute("INSERT INTO portfolio_info VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data)
            con.commit()
    con.close()
            
def calculate_closed_trades_stats(symbols):
    logger.info(f"Calculating closed trades stats")
    trading_client = create_trading_client()
    stats = []
    for symbol in symbols:
        request_params = GetOrdersRequest(
            status='closed',
            symbols=[symbol]
        )
        # long only strategies
        orders = trading_client.get_orders(filter=request_params)
        orders_dicts = map(dict, orders)
        keys_to_keep = ['symbol', 'filled_at', 'filled_qty', 'filled_avg_price', 'side']
        filtered_orders = [{key: value for key, value in d.items() if key in keys_to_keep} for d in orders_dicts]
        df_orders = pd.DataFrame(filtered_orders)
        
        if len(df_orders) > 0:
            df_orders = df_orders.loc[~df_orders['filled_at'].isna(),:]
            df_orders['filled_qty'] = df_orders['filled_qty'].apply(float)
            df_orders['filled_avg_price'] = df_orders['filled_avg_price'].apply(float) # converting via astype does not work
            df_orders['side'] = df_orders['side'].apply(str)
            df_orders['filled_qty'] = df_orders['filled_qty'].round(3)
            
            df_orders.sort_values(by = 'filled_at', inplace = True)
            df_orders[['filled_qty_lag', 'side_lag', 'filled_avg_price_lag']] = df_orders[['filled_qty', 'side', 'filled_avg_price']].shift(1)
            
            df_trades = df_orders.loc[(df_orders['side'] == 'OrderSide.SELL') &
                                    (df_orders['side_lag'] == 'OrderSide.BUY') &
                                    (df_orders['filled_qty'] == df_orders['filled_qty_lag']),:]
            df_trades['pl'] = (df_trades['filled_qty'] * df_trades['filled_avg_price']) - (df_trades['filled_qty_lag'] * df_trades['filled_avg_price_lag'])
            stats.append({'closed_trades_pl': df_trades['pl'].sum(), 
                          'closed_trades_cnt':len(df_trades),
                          'closed_winning_trades_cnt': len(df_trades.loc[df_trades['pl'] > 0, :])})
        else:
            stats.append({'closed_trades_pl': 0, 'closed_trades_cnt': 0, 'closed_winning_trades_cnt': 0})
    df_stats = pd.DataFrame(stats, index = symbols)
    closed_trades_pl = df_stats['closed_trades_pl'].sum()
    closed_trades_cnt = df_stats['closed_trades_cnt'].sum()
    win_rate = (df_stats['closed_winning_trades_cnt'].sum()/df_stats['closed_trades_cnt'].sum()) if closed_trades_cnt > 0 else None
    zero_tr_symbols_cnt = (df_stats['closed_trades_cnt'] == 0).sum()
    
    return {'pl': closed_trades_pl, 
            'trades_cnt': closed_trades_cnt,
            'win_rate': win_rate,
            'symbols_with_zero_trades_cnt': zero_tr_symbols_cnt}
    
def calculate_open_trades_stats(symbols):
    logger.info(f"Calculating open trades stats")
    trading_client = create_trading_client()
    stats = []
    for symbol in symbols:
        if symbol in crypto_map.keys():
            symbol = crypto_map[symbol]
        try:
            position = trading_client.get_open_position(symbol)
            position_dict = dict(position)
            keys_to_keep = ['symbol', 'cost_basis', 'unrealized_pl', 'unrealized_plpc']
            filtered_position = {key: position_dict[key] for key in keys_to_keep if key in position_dict}
            stats.append(filtered_position)
        except:
            pass
    if len(stats) > 0:
        df_stats = pd.DataFrame(stats)
        df_stats.loc[:,['cost_basis', 'unrealized_pl', 'unrealized_plpc']] = df_stats.loc[:,['cost_basis', 'unrealized_pl', 'unrealized_plpc']].astype('float')
        df_stats.set_index('symbol', inplace = True)     
        open_trades_cost_basis = df_stats['cost_basis'].sum()
        open_trades_cnt = len(df_stats)
        open_trades_symbols = str(df_stats.index.tolist())
        open_trades_pl = df_stats['unrealized_pl'].sum()
        
        return {'cost_basis': open_trades_cost_basis,
            'trades_cnt': open_trades_cnt,
            'symbols': open_trades_symbols,
            'pl': open_trades_pl}
        
    else:
        return {'cost_basis': 0,
                'trades_cnt': 0,
                'symbols': str([]),
                'pl':0}
        
def calculate_sharpe_ratio(portfolio, todays_return, date, period, trading_period = 252):
    con = sqlite3.connect('../db/calpha.db')
    
    if period == '1w':
        period_start = date - timedelta(weeks = 1)
    elif period == '1m':
        period_start = date - timedelta(days = 30)
    elif period == '3m':
        period_start = date - timedelta(days = 90)
    elif period == 'overall':
        period_start = date - timedelta(weeks = 10_000)
    
    period_start = period_start.strftime("%Y-%m-%d")
    df = pd.read_sql(f"""select date,
                            daily_return
                        from portfolio_state
                        where portfolio_name = '{portfolio}'
                            and date >= '{period_start}'""",
                    con)
    con.close()
    
    df.sort_values('date', inplace = True)
    s = df.set_index('date')['daily_return']
    s = pd.concat([s, pd.Series(todays_return, index = [date])])
    
    sharpe_ratio = trading_period**(1/2)*(s.mean()/s.std())
    return sharpe_ratio

def calculate_todays_return(portfolio, equity, portfolio_size):
    con = sqlite3.connect('../db/calpha.db')
    df = pd.read_sql(f"""select date,
                            portfolio_size,
                            equity
                        from portfolio_state
                        where portfolio_name = '{portfolio}'
                        order by date desc
                        limit 1""",
                    con)
    con.close()
    todays_return = ((equity - df['equity'][0])/df['equity'][0]) - ((portfolio_size - df['portfolio_size'][0])/df['equity'][0])
    
    return todays_return

def calculate_total_return(portfolio, todays_return, date, period):
    con = sqlite3.connect('../db/calpha.db')
    
    if period == '1w':
        period_start = date - timedelta(weeks = 1)
    elif period == '1m':
        period_start = date - timedelta(days = 30)
    elif period == '3m':
        period_start = date - timedelta(days = 90)
    elif period == 'overall':
        period_start = date - timedelta(weeks = 10_000)
    
    period_start = period_start.strftime("%Y-%m-%d")
        
    df = pd.read_sql(f"""select date,
                            daily_return
                        from portfolio_state
                        where portfolio_name = '{portfolio}'
                            and date >= '{period_start}'""",
                    con)
    con.close()
    
    df.sort_values('date', inplace = True)
    s = df.set_index('date')['daily_return']
    s = pd.concat([s, pd.Series(todays_return, index = [date])])
    total_return = (s + 1).prod() - 1
        
    return total_return

def calculate_absolute_return(portfolio, date, closed_trades_pl, open_trades_pl, period):
    con = sqlite3.connect('../db/calpha.db')
    
    if period == '1w':
        period_start = date - timedelta(weeks = 1)
    elif period == '1m':
        period_start = date - timedelta(days = 30)
    elif period == '3m':
        period_start = date - timedelta(days = 90)
    elif period == 'overall':
        period_start = date - timedelta(weeks = 10_000)
    
    period_start = period_start.strftime("%Y-%m-%d")
        
    df = pd.read_sql(f"""select date,
                            closed_trades_PL
                        from portfolio_state
                        where portfolio_name = '{portfolio}'
                            and date >= '{period_start}'""",
                    con)
    con.close()
    
    df.sort_values('date', inplace = True)
    s = df.set_index('date')['closed_trades_PL']
    s = pd.concat([s, pd.Series(closed_trades_pl, index = [date])])
    abs_return = (s - s.shift(1)).sum() + open_trades_pl
    
    return abs_return

def calculate_drawdown(portfolio, date, todays_return):
    con = sqlite3.connect('../db/calpha.db')    
        
    df = pd.read_sql(f"""select date,
                            daily_return
                        from portfolio_state
                        where portfolio_name = '{portfolio}'""",
                    con)
    con.close()
    
    df.sort_values('date', inplace = True)
    s = df.set_index('date')['daily_return']
    s = pd.concat([s, pd.Series(todays_return, index = [date])])
    
    max_drawdown = qs.stats.max_drawdown(s)
    
    cummax = (1 + s).cumprod().cummax()
    max_drawdown_duration = cummax.value_counts().head(1).iloc[0]
                
    return max_drawdown, max_drawdown_duration

def calculate_calmar_ratio(portfolio, date, max_drawdown, todays_return, trading_period = 252):
    con = sqlite3.connect('../db/calpha.db')    
        
    df = pd.read_sql(f"""select date,
                            daily_return
                        from portfolio_state
                        where portfolio_name = '{portfolio}'""",
                    con)
    con.close()
    
    df.sort_values('date', inplace = True)
    daily_returns = df.set_index('date')['daily_return']
    daily_returns = pd.concat([daily_returns, pd.Series(todays_return, index = [date])])
    
    investment_period_years = len(daily_returns) / trading_period
    cagr = (1 + daily_returns).prod() ** (1 / investment_period_years) - 1

    try:
        calmar_cagr = cagr / abs(max_drawdown)
    except:
        logger.warning(f"Portfolio - {portfolio} - unable to calculate calmar ratio")
        calmar_cagr = None
    
    return calmar_cagr

def calculate_sortino_ratio(portfolio, date, todays_return, trading_period = 252):
    con = sqlite3.connect('../db/calpha.db')    
        
    df = pd.read_sql(f"""select date,
                            daily_return
                        from portfolio_state
                        where portfolio_name = '{portfolio}'""",
                    con)
    con.close()
    
    df.sort_values('date', inplace = True)
    daily_returns = df.set_index('date')['daily_return']
    daily_returns = pd.concat([daily_returns, pd.Series(todays_return, index = [date])])
    
    if daily_returns.notna().sum() > 1:
        sortino_ratio = qs.stats.sortino(daily_returns, annualize = True, periods = trading_period)
    else:
        sortino_ratio = None
    
    return sortino_ratio
        
def update_portfolio_state(portfolio, portfolio_size, symbols, run_id, timestamp):
    logger.info(f"Updating state of portfolio - {portfolio}")
    con = sqlite3.connect('../db/calpha.db')
    date = timestamp.date() 

    # available_cash
    #   portfolio_size + sum(PL of closed trades) - (cost basis of open trades)
    result_closed_trades = calculate_closed_trades_stats(symbols)
    result_open_trades = calculate_open_trades_stats(symbols)
    available_cash = portfolio_size + result_closed_trades['pl'] - \
        result_open_trades['cost_basis']
        
    # equity
    #   avilable_cash + (cost basis of open trades) + (PL of open trades)
    equity = available_cash + result_open_trades['cost_basis'] + result_open_trades['pl']
    
    todays_return = calculate_todays_return(portfolio, equity, portfolio_size)
    sharpe_ratio = calculate_sharpe_ratio(portfolio, todays_return, date, 'overall')
    total_return = calculate_total_return(portfolio, todays_return, date, 'overall')
    absolute_return = calculate_absolute_return(portfolio, date, result_closed_trades['pl'], result_open_trades['pl'], 'overall')
    max_drawdown, max_drawdown_duration = calculate_drawdown(portfolio, date, todays_return)
    calmar_ratio = calculate_calmar_ratio(portfolio, date, max_drawdown, todays_return)
    sortino_ratio = calculate_sortino_ratio(portfolio, date, todays_return)
        
    data = (timestamp, 
            date, 
            run_id, 
            portfolio,
            portfolio_size, 
            float(available_cash), 
            float(equity), 
            result_open_trades['trades_cnt'],
            result_open_trades['symbols'], 
            float(result_open_trades['pl']), 
            result_open_trades['cost_basis'], 
            int(result_closed_trades['trades_cnt']), 
            float(result_closed_trades['pl']), 
            float(result_closed_trades['win_rate']), 
            float(sharpe_ratio), 
            calmar_ratio, 
            sortino_ratio,
            float(total_return), 
            float(max_drawdown), 
            int(max_drawdown_duration),
            float(todays_return),
            float(absolute_return),
            int(result_closed_trades['symbols_with_zero_trades_cnt']),
            len(symbols))
    con.execute("""INSERT INTO portfolio_state VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
    con.commit()
    con.close()
    
def update_whole_portfolio_state(run_id, timestamp):
    trading_client = create_trading_client()
    account_info = trading_client.get_account()
    url = "https://paper-api.alpaca.markets/v2/account/activities/TRANS"

    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": keys['paper_key'],
        "APCA-API-SECRET-KEY": keys['paper_secret']
    }

    response = requests.get(url, headers=headers)
    transactions = response.json()
    #TODO when real account, finish to get deposits/withdrawals

    
    equity = account_info['equity']
    last_equity = account_info['last_equity']
    cash = account_info['cash']
    long_mk_value = account_info['long_market_value']
    short_mk_value = account_info['short_market_value']
    non_marg_buying_power = account_info['non_marginable_buying_power']
    deposits_withdrawals = None
    

def generate_id():
    unique_id = uuid.uuid4()
    unique_id_str = str(unique_id)
    return unique_id_str
