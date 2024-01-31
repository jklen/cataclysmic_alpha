import vectorbt as vbt
import numpy as np
import pandas as pd
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.timeframe import TimeFrame
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
import yaml
from time import ctime
import pdb
import logging

logger = logging.getLogger(__name__)

# Define the strategy logic in a function
def hh_hl_strategy_logic(close, window_entry, hh_hl_counts, 
                   window_exit, lh_counts):
    #close = pd.Series(close.flatten())
    if isinstance(close, np.ndarray):
        close = pd.DataFrame(close)
    higher_highs = close > close.rolling(window=window_entry, min_periods=1).max().shift(1)
    higher_lows = close > close.rolling(window=window_entry, min_periods=1).min().shift(1)

    hh_count = higher_highs.rolling(window=window_entry).sum()
    hl_count = higher_lows.rolling(window=window_entry).sum()

    entry_signal = (hl_count.shift(1) >= hh_hl_counts) & (hh_count.shift(1) >= hh_hl_counts) & higher_lows

    lower_highs = close < close.rolling(window=window_exit, min_periods=1).max().shift(1)
    lh_count = lower_highs.rolling(window=window_exit).sum()
    exit_signal = (lh_count >= lh_counts) & lower_highs

    return entry_signal, exit_signal

# Create a custom indicator using the IndicatorFactory
HigherHighStrategy = vbt.IndicatorFactory(
    input_names=['close'],
    param_names=['window_entry', 'hh_hl_counts',
                 'window_exit', 'lh_counts'],
    output_names=['entry_signal', 'exit_signal']
).from_apply_func(hh_hl_strategy_logic)

def get_alpaca_crypto_data(symbol, start, end):
    client = CryptoHistoricalDataClient()

    # Creating request object
    request_params = CryptoBarsRequest(
                            symbol_or_symbols=symbol,
                            timeframe=TimeFrame.Day,
                            start=start,
                            end=end
                            )
    bars = client.get_crypto_bars(request_params)
    df = bars.df
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    return df

def get_alpaca_stock_data(symbol, start, end):
    keys = yaml.safe_load(open('../keys.yaml', 'r'))
    client = StockHistoricalDataClient(api_key=keys['paper_key'],
                                        secret_key=keys['paper_secret'])
    request_params = StockBarsRequest(
                            symbol_or_symbols=symbol,
                            timeframe=TimeFrame.Day,
                            start=start,
                            end=end
                            )
    bars = client.get_stock_bars(request_params)
    df = bars.df
    df = df[['open', 'high', 'low', 'close', 'volume']]
    
    return df

def get_yf_data(symbol, start, end):
    symbol = symbol.replace('/', '-')
    df = yf.download(symbol, start=start, end=end)
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    df.columns = df.columns.str.lower()
    df.index.name = 'timestamp' 
    
    return df

def data_load(symbol, data_preference, start, end):
    if data_preference == 'yf':
        logger.info(f"{symbol} - downloading data from yfinance")
        df = get_yf_data(symbol, start, end)
        if len(df) == 0:
            return None
        return df
    elif data_preference == 'alpaca':
        try:
            logger.info(f"{symbol} - downloading data from alpaca - stock client")
            df = get_alpaca_stock_data(symbol, start, end)
            return df
        except:
            try:
                logger.info(f"{symbol} - downloading data from alpaca - crypto client")
                df = get_alpaca_crypto_data(symbol, start, end)
                return df
            except Exception as e:
                logger.warning(f"{symbol} - problem downloading data from alpaca via crypto or stock client")
                return None
    elif data_preference == 'longer_period':
        logger.info(f"{symbol} - downloading data from yfinance")
        df_yf =  get_yf_data(symbol, start, end)
            
        try:
            logger.info(f"{symbol} - downloading data from alpaca - stock client")
            df_alpaca = get_alpaca_stock_data(symbol, start, end)
        except:
            try:
                logger.info(f"{symbol} - downloading data from alpaca - crypto client")
                df_alpaca = get_alpaca_crypto_data(symbol, start, end)
            except Exception as e:
                logger.warning(f"{symbol} - problem downloading data from alpaca via crypto or stock client")
                df_alpaca = pd.DataFrame()
                
        if len(df_yf) == 0 and len(df_alpaca) == 0:
            return None
        
        df = df_yf if len(df_yf) > len(df_alpaca) else df_alpaca
        return df
