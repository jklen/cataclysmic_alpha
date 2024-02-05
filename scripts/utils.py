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
import matplotlib.pyplot as plt
import os
from matplotlib.dates import date2num

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

def data_stats(df, symbol):
    logger.info(f"{symbol} - making symbol stats & plots")
    # Ensure 'timestamp' is datetime type for operations
    #df['timestamp'] = pd.to_datetime(df['timestamp'])
    path = f"../outputs/{symbol.replace('/', '-')}"
    if not os.path.exists(path):
        os.makedirs(path)
    
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 12))
    
    # Close Price Plot
    df['close'].plot(ax=axes[0], title=f'Close Price - {symbol}', color='blue')
    axes[0].set_ylabel('Close Price')
    axes[0].set_xlabel('Timestamp')
    
    # Annotations for Close Price
    close_stats = df['close'].describe()
    close_stats['std%'] = (close_stats['std'] / close_stats['mean'])
    close_stats = close_stats.round(2)
    close_stats = close_stats
    close_info = close_stats.to_string(header=False)
    min_date, max_date = df.index.min(), df.index.max()
    num_days = (max_date - min_date).days
    close_info_date = f"\nMin Date: {min_date.date()}\nMax Date: {max_date.date()}\nDate range: {num_days}"
    axes[0].annotate(close_info, xy=(0.05, 0.95), xycoords='axes fraction', verticalalignment='top')
    axes[0].annotate(close_info_date, xy=(0.8, 0.95), xycoords='axes fraction', verticalalignment='top')
    
    # Volume Plot
    df['volume'].plot(ax=axes[1], title='Volume', color='green')
    axes[1].set_ylabel('Volume')
    axes[1].set_xlabel('Timestamp')
    
    # Daily Returns Calculation & Plot
    df['daily_returns'] = df['close'].pct_change()
    df['daily_returns'].plot(ax=axes[2], kind='hist', bins=50, alpha=0.6, color='orange', title='Daily Returns Histogram')
    axes[2].set_xlabel('Daily Returns (%)')
    
    # Annotations for Daily Returns
    returns_stats = df['daily_returns'].describe()
    returns_stats = returns_stats.round(2)
    returns_stats = returns_stats
    returns_info = returns_stats.to_string(header = False)
    axes[2].annotate(returns_info, xy=(0.05, 0.95), xycoords='axes fraction', verticalalignment='top')
    
    plt.tight_layout()
    plt.savefig(f"{path}/data_statistics.png")
    plt.close()

def data_split(df, symbol, split_params):
    logger.info(f"{symbol} - splitting data via rolling split")
    path = f"../outputs/{symbol.replace('/', '-')}"
    
    window_len = int(split_params['period_ratio'] * len(df))
    window_len = min(window_len, split_params['period_years_max'] * 360)
    
    split_params = dict(n = split_params['n_periods'],
                            window_len = window_len,
                            left_to_right = True)
    
    figure = df['close'].vbt.rolling_split(**split_params,
                                           plot = True)
    figure.update_layout(width = 800, height = 400, title = f"rolling split - {symbol}")
    
    figure.add_annotation(
        text=f"Window Length: {window_len}<br>Total Length: {len(df)}",
        xref="paper", yref="paper",
        x=1, y=1, xanchor="right", yanchor="top",
        showarrow=False,
        font=dict(size=12)
        )
    
    figure.write_image(f"{path}/rolling_split.png")
    
    (price_open, indexes_open) = df['open'].shift(-1).vbt.rolling_split(**split_params)
    (price_close, indexes_close) = df['close'].vbt.rolling_split(**split_params)
    
    return price_open, indexes_open, price_close, indexes_close

def strategy_stats(open_price, close_price, strategy, strategy_params):
    logger.info("calculating portfolio stats")    
    param_ranges = strategy_params['param_ranges']
    param_ranges = {key: np.arange(value[0], value[1] + 1) for key, value in param_ranges.items()}
        
    if strategy == 'hhhl':
        Strategy = HigherHighStrategy
        
    indicator = Strategy.run(close_price, **param_ranges, param_product = True)
    entries = indicator.entry_signal
    exits = indicator.exit_signal

    pf = vbt.Portfolio.from_signals(close_price, 
                                    entries, 
                                    exits,
                                    price = open_price,
                                    fees=strategy_params['fees'], 
                                    slippage=strategy_params['slippage'], 
                                    freq='1D')
    df_stats = pf.stats(agg_func=None)
    
    return df_stats

def strategy_grouped_stats(df_stats, symbol):
    logger.info(f"{symbol} - calculating grouped stats of the strategy")
    path = f"../outputs/{symbol.replace('/', '-')}"
    columns_to_describe = ['Total Return [%]', 'Max Drawdown [%]', 
                           'Max Drawdown Duration', 'Total Trades', 
                           'Win Rate [%]', 'Sharpe Ratio']

    df_stats = df_stats.droplevel('split_idx')
    df_grouped_stats = df_stats.groupby(level=df_stats.index.names)[columns_to_describe].describe()
    df_grouped_stats.columns = df_grouped_stats.columns.map('_'.join)
    df_grouped_stats.reset_index(inplace=True)
    
    df_grouped_stats.to_csv(f"{path}/wf_grouped_stats.csv", header = True, index = False)
