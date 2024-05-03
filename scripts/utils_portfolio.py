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
                time_in_force = 'day',
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
        running_params = str(config['weights']['runnig_params'])
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
    
    return {'pl': closed_trades_pl, 
            'trades_cnt': closed_trades_cnt,
            'win_rate': win_rate}
    
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
        
def update_portfolio_state(portfolio, portfolio_size, symbols, run_id, timestamp):
    logger.info(f"Updating state of portfolio - {portfolio}")
    con = sqlite3.connect('../db/calpha.db')
    date = timestamp.date() # OK
    # portfolio_script_run_id OK
    # portfolio_name OK
    # available_cash
    #   portfolio_size + sum(PL of closed trades) - (cost basis of open trades)
    result_closed_trades = calculate_closed_trades_stats(symbols)
    result_open_trades = calculate_open_trades_stats(symbols)
    available_cash = portfolio_size + result_closed_trades['pl'] - \
        result_open_trades['cost_basis']
        
    # equity
    #   avilable_cash + (cost basis of open trades) + (PL of open trades)
    equity = available_cash + result_open_trades['cost_basis'] + result_open_trades['pl']
    
    # sharpe ratio 
    
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
            None, None, None, None, None, None)
    con.execute("""INSERT INTO portfolio_state VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
    con.commit()
    con.close()
    
    # open_trades_PL
    # open_trades_cost_basis_sum
    # closed_trades_cnt
    # closed_trades_PL
    # win_rate
    # sharpe_ratio
    # sharpe_ratio_rolling_1w
    # sharpe_ratio_rolling_1m # dorobit
    # sharpe_ratio_rolling_3m # dorobit
    # calmar_ratio
    # sortino_ratio
    # total_return
    # total_return_rolling_1w # dorobit
    # total_return_rolling_1m # dorobit
    # total_return_rolling_3m # dorobit
    # absolute_return # dorobit
    # absolute_return_rolling_1w # dorobit
    # absolute_return_rolling_1m # dorobit
    # absolute_return_rolling_3m # dorobit
    # daily return - #TODO dorobit stlpec v db
    # max_drawdown
    # max_drawdown_duration
    
    

def generate_id():
    unique_id = uuid.uuid4()
    unique_id_str = str(unique_id)
    return unique_id_str
