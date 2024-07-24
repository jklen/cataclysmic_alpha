import yaml
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.trading.requests import GetOrdersRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
import logging
import pandas as pd
import pdb
import yfinance as yf

logger = logging.getLogger(__name__)
keys = yaml.safe_load(open('../keys.yaml', 'r'))

crypto_map = {'BTCUSD':'BTC/USD'}

def get_alpaca_data(symbols, start, end, attempts = 10):
    keys = yaml.safe_load(open('../keys.yaml', 'r'))
    dfs = []
    for symbol in symbols:
        for attempt in range(1, attempts + 1):
            try:
                if symbol in crypto_map.keys():
                    client = CryptoHistoricalDataClient()
                    request_params = CryptoBarsRequest(
                                            symbol_or_symbols=[crypto_map[symbol]],
                                            timeframe=TimeFrame.Day,
                                            start=start,
                                            end=end
                                            )
                    bars = client.get_crypto_bars(request_params)
                else:
                    client = StockHistoricalDataClient(api_key=keys['paper_key'],
                                                    secret_key=keys['paper_secret'])
                    request_params = StockBarsRequest(
                                            symbol_or_symbols=[symbol],
                                            timeframe=TimeFrame.Day,
                                            start=start,
                                            end=end)
                    bars = client.get_stock_bars(request_params)
                break
            except:
                pass
        try:
            df = bars.df
        except:
            continue
        df = df[['open', 'high', 'low', 'close', 'volume']]
        dfs.append(df)
    df_whole = pd.concat(dfs, axis = 0)
    df_whole.reset_index(inplace = True)
    
    return df_whole

def get_yf_data(symbols, start, end, attempts = 10):
    dfs = []
    for symbol in symbols:
        if symbol in crypto_map.keys():
            symbol = crypto_map[symbol].replace('/', '-')
        for attempt in range(1, attempts + 1):
            try:
                df = yf.download(symbol, start=start, end=end, timeout=100)
                break
            except:
                pass
            
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.columns = df.columns.str.lower()
        df['symbol'] = symbol
        df.index.name = 'timestamp'
        dfs.append(df)
    df_whole = pd.concat(dfs, axis = 0)
    df_whole.reset_index(inplace = True)
    
    return df_whole

def create_trading_client():
    trading_client = TradingClient(keys['paper_key'], keys['paper_secret'], paper=True)
    return trading_client

def get_trades(symbols):

    trading_client = create_trading_client()
    trades = []
    for symbol in symbols:
        symbol_orig = symbol
        if symbol in crypto_map.keys():
            symbol = crypto_map[symbol]
            
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
        
        if len(df_orders) >= 2: # 2 orders - buy & sell for 1 closed trade
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
            df_trades['return'] = ((df_trades['filled_qty'] * df_trades['filled_avg_price']) / (df_trades['filled_qty_lag'] * df_trades['filled_avg_price_lag'])) - 1
            df_trades['symbol'] = symbol_orig
            
            trades.append(df_trades)
        else:
            df_trades =  pd.DataFrame()
    #pdb.set_trace()
    df_trades_whole = pd.concat(trades)
    
    return df_trades_whole
            
