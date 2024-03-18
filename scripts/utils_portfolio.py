from utils_strategy import HigherHighStrategy
import pandas as pd
import yaml
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import OrderRequest, GetOrdersRequest, GetOrderByIdRequest
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest, StockLatestTradeRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import pdb
from datetime import datetime, timedelta
keys = yaml.safe_load(open('../keys.yaml', 'r'))


strategies_directions = {
    'hhhl':'long'
}

def review_positions():
    pass

def create_trading_client():
    trading_client = TradingClient(keys['paper_key'], keys['paper_secret'], paper=True)
    return trading_client

def closed_trades_cnt(symbols):
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
        df_orders = pd.DataFrame(filtered_orders)
        df_orders['side'] = df_orders['side'].apply(str)
        df_orders.sort_values(by = 'filled_at', inplace = True)
        df_orders[['filled_qty_lag', 'side_lag']] = df_orders[['filled_qty', 'side']].shift(1)
        
        df_trades = df_orders.loc[(df_orders['side'] == 'OrderSide.SELL') &
                                (df_orders['side_lag'] == 'OrderSide.BUY') &
                                (df_orders['filled_qty'] == df_orders['filled_qty_lag']),:]
        closed_trades[symbol] = len(df_trades)
        
    return pd.Series(closed_trades, name = 'closed_trades_cnt')

def running_weights(symbols, weights_params):
    
    if weights_params['running'] == 'win_rate':
        s_closed_trades_cnt = closed_trades_cnt(symbols)
        symbols_meeting_min_trades_cnt = (s_closed_trades_cnt >= weights_params['running_params']['min_trades']).sum()
        
        if symbols_meeting_min_trades_cnt >= weights_params['running_params']['min_symbols']:
            return True
        else:
            return False
  
def calculate_win_rates(symbols):
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
    #TODO symbol ktory splni podmienku a ma nulovy win rate, ma vahu 0 - musi byt min 0.05

    if series_metric.name == 'win_rate':
        closed_trades = closed_trades_cnt(series_metric.index.tolist())
        df = series_metric.to_frame()
        df = df.join(closed_trades.to_frame())
        mask_symbols_to_weight = df['closed_trades_cnt'] >= running_params['min_trades']
        symbols_with_min_weight_cnt = len(df) - mask_symbols_to_weight.sum()
        df['weight'] = running_params['min_weight']
        df.loc[mask_symbols_to_weight, 'weight'] = df.loc[mask_symbols_to_weight, 'win_rate']/df.loc[mask_symbols_to_weight, 'win_rate'].sum()
        df.loc[mask_symbols_to_weight, 'weight'] = (1-symbols_with_min_weight_cnt*running_params['min_weight']) * df.loc[mask_symbols_to_weight, 'weight']
        
        return df['weight'].to_dict()

def check_weights(symbols, weights_params):
    
    if (weights_params['initial'] == 'equal') & (weights_params['running'] == 'equal'):
        one_symbol_weight = 1./len(symbols)
        return {symbol:one_symbol_weight for symbol in symbols}
    else:
        if running_weights(symbols, weights_params):
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
    if strategy == 'hhhl':
        Strategy = HigherHighStrategy
    
    close_price = df_symbol['close']
    indicator = Strategy.run(close_price, **strategy_params)
    entries = indicator.entry_signal
    exits = indicator.exit_signal
    
    return entries, exits

def is_trading_day(day):
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
    cryptos = ['BTC/USD']
    todays_date = datetime.today().date()
    
    if symbol in cryptos:
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
        
def orders_or_close():
    pass