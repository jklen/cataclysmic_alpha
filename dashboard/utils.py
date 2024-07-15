import yaml
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import logging
import pandas as pd
import pdb

logger = logging.getLogger(__name__)

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