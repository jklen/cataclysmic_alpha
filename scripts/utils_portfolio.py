from utils_strategy import HigherHighStrategy
import pandas as pd
import yaml
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import OrderRequest, GetOrdersRequest, GetOrderByIdRequest, \
    CryptoBarsRequest, StockBarsRequest, StockLatestTradeRequest
from alpaca.trading.enums import OrderSide, TimeInForce
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
        
    return pd.Series(closed_trades)

def running_weights(symbols, weights_params):
    
    if weights_params['running'] == 'win_rate':
        s_closed_trades_cnt = closed_trades_cnt(symbols)
        symbols_meeting_min_trades_cnt = (s_closed_trades_cnt >= weights_params['running']['min_trades']).sum()
        
        if symbols_meeting_min_trades_cnt >= weights_params['running']['min_symbols']:
            return True
        else:
            return False
  
def calculate_win_rates(symbols):
    pass #TODO

def check_weights(symbols, weights_params):
    
    if (weights_params['initial'] == 'equal') & (weights_params['running'] == 'equal'):
        one_symbol_weight = 1./len(symbols)
        return {symbol:one_symbol_weight for symbol in symbols}
    else:
        if running_weights(symbols, weights_params):
            if weights_params['running'] == 'win_rate':
                win_rates = calculate_win_rates(symbols)
                # calculate & return weights #TODO
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

def orders_or_close():
    pass