import os
import gc
import ast
import pickle
import logging

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import vectorbt as vbt
import yaml
import yfinance as yf

from time import ctime
from matplotlib.dates import date2num
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform, pdist
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import davies_bouldin_score
from sklearn.cluster import KMeans
from yellowbrick.cluster import KElbowVisualizer
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.timeframe import TimeFrame
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from requests.exceptions import RequestException

from calpha import ROOT_DIR
from calpha.strategies import HigherHighStrategy

logger = logging.getLogger(__name__)

cryptos = ['BTC/USD']


def get_alpaca_data(symbol, start, end, attempts=10):
    """Download daily OHLCV bars from the Alpaca API.

    Automatically selects the crypto or stock endpoint based on whether
    the symbol is in the `cryptos` list.

    Args:
        symbol: Ticker symbol, e.g. 'AAPL' or 'BTC/USD'.
        start: Start date (datetime or date-like).
        end: End date (datetime or date-like).
        attempts: Number of retry attempts on failure.

    Returns:
        DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        indexed by timestamp, with the 'symbol' multi-index level dropped.
    """
    keys = yaml.safe_load(open(ROOT_DIR / 'keys.yaml', 'r'))
    for attempt in range(1, attempts + 1):
        try:
            if symbol in cryptos:
                client = CryptoHistoricalDataClient()
                request_params = CryptoBarsRequest(
                    symbol_or_symbols=[symbol],
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
                    end=end
                )
                bars = client.get_stock_bars(request_params)
            break
        except Exception:
            logger.warning(f"{symbol} - attempt {attempt} to download data from alpaca, retrying")

    df = bars.df
    df = df[['open', 'high', 'low', 'close', 'volume']]
    df = df.droplevel('symbol')
    return df


def get_yf_data(symbol, start, end, attempts=10):
    """Download daily OHLCV bars from Yahoo Finance.

    Converts crypto-style slashes to dashes (e.g. 'BTC/USD' → 'BTC-USD')
    to match the yfinance ticker format.

    Args:
        symbol: Ticker symbol. Slashes are replaced with dashes automatically.
        start: Start date (datetime or date-like).
        end: End date (datetime or date-like).
        attempts: Number of retry attempts on connection errors.

    Returns:
        DataFrame with lowercase columns ['open', 'high', 'low', 'close',
        'adj close', 'volume'] and index named 'timestamp'.

    Raises:
        RequestException / ConnectionError / OSError after all attempts fail.
    """
    symbol = symbol.replace('/', '-')

    for attempt in range(1, attempts + 1):
        try:
            df = yf.download(symbol, start=start, end=end, timeout=100)
            break
        except (RequestException, ConnectionError, OSError) as e:
            logger.warning(f"{symbol} - attempt {attempt} to download data from YF failed, retrying. Error: {e}")
            if attempt == attempts:
                raise

    df = df[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
    df.columns = df.columns.str.lower()
    df.index.name = 'timestamp'
    return df


def data_load(symbol, data_preference, start, end):
    """Load OHLCV data for a symbol from the configured data source.

    Args:
        symbol: Ticker symbol, e.g. 'AAPL' or 'BTC/USD'.
        data_preference: One of 'yf' (Yahoo Finance), 'alpaca', or
            'longer_period' (picks whichever source returns more rows).
        start: Start date for the data range.
        end: End date for the data range.

    Returns:
        DataFrame of OHLCV bars, or an empty DataFrame if no data is available.
    """
    if data_preference == 'yf':
        logger.info(f"{symbol} - downloading data from yfinance")
        df = get_yf_data(symbol, start, end)
        if len(df) == 0:
            logger.warning(f"{symbol} - No data available from yfinance")
            return pd.DataFrame()
        return df
    elif data_preference == 'alpaca':
        logger.info(f"{symbol} - downloading data from alpaca")
        try:
            return get_alpaca_data(symbol, start, end)
        except Exception:
            logger.warning(f"{symbol} - problem downloading data from alpaca")
            return pd.DataFrame()
    elif data_preference == 'longer_period':
        logger.info(f"{symbol} - downloading data from yfinance")
        df_yf = get_yf_data(symbol, start, end)

        try:
            logger.info(f"{symbol} - downloading data from alpaca")
            df_alpaca = get_alpaca_data(symbol, start, end)
        except Exception:
            logger.warning(f"{symbol} - problem downloading data from alpaca")
            df_alpaca = pd.DataFrame()

        if len(df_yf) == 0 and len(df_alpaca) == 0:
            logger.warning(f"{symbol} - no data available from yfinance or alpaca")
            return pd.DataFrame()

        return df_yf if len(df_yf) > len(df_alpaca) else df_alpaca


def create_path(symbol, strategy=None):
    """Create the output directory structure for a symbol and optional strategy.

    Args:
        symbol: Ticker symbol. Slashes are preserved in the path (use the
            symbol as-is; callers should replace '/' if needed).
        strategy: Strategy name for a subfolder inside the symbol directory.
            If None, only the symbol directory is created.
    """
    main_folder = os.path.join("outputs", symbol)
    if not os.path.exists(main_folder):
        os.makedirs(main_folder)
        print(f"Folder created: {main_folder}")

    if strategy is not None:
        subfolder = os.path.join(main_folder, strategy)
        if not os.path.exists(subfolder):
            os.makedirs(subfolder)
            print(f"Subfolder created: {subfolder}")


def data_stats(df, symbol):
    """Compute and save summary statistics and plots for a symbol's price data.

    Saves a three-panel PNG (close price, volume, daily returns histogram)
    to `outputs/<symbol>/data_statistics.png`.

    Args:
        df: DataFrame with at least 'close' and 'volume' columns.
        symbol: Ticker symbol, used for labelling and output path.
    """
    logger.info(f"{symbol} - making symbol stats & plots")
    path = f"outputs/{symbol.replace('/', '-')}"

    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 12))

    df['close'].plot(ax=axes[0], title=f'Close Price - {symbol}', color='blue')
    axes[0].set_ylabel('Close Price')
    axes[0].set_xlabel('Timestamp')

    close_stats = df['close'].describe()
    close_stats['std%'] = (close_stats['std'] / close_stats['mean'])
    close_stats = close_stats.round(2)
    close_info = close_stats.to_string(header=False)
    min_date, max_date = df.index.min(), df.index.max()
    num_days = (max_date - min_date).days
    close_info_date = f"\nMin Date: {min_date.date()}\nMax Date: {max_date.date()}\nDate range: {num_days}"
    axes[0].annotate(close_info, xy=(0.05, 0.95), xycoords='axes fraction', verticalalignment='top')
    axes[0].annotate(close_info_date, xy=(0.8, 0.95), xycoords='axes fraction', verticalalignment='top')

    df['volume'].plot(ax=axes[1], title='Volume', color='green')
    axes[1].set_ylabel('Volume')
    axes[1].set_xlabel('Timestamp')

    df['daily_returns'] = df['close'].pct_change()
    df['daily_returns'].plot(ax=axes[2], kind='hist', bins=50, alpha=0.6, color='orange', title='Daily Returns Histogram')
    axes[2].set_xlabel('Daily Returns (%)')

    returns_stats = df['daily_returns'].describe().round(2)
    returns_info = returns_stats.to_string(header=False)
    axes[2].annotate(returns_info, xy=(0.05, 0.95), xycoords='axes fraction', verticalalignment='top')

    plt.tight_layout()
    plt.savefig(f"{path}/data_statistics.png")
    plt.close()


def data_split(df, symbol, split_params):
    """Split price data into rolling train/test windows using VectorBT.

    Window length is capped at `period_years_max * 360` bars to prevent
    very long lookback periods from dominating the backtest.

    Args:
        df: DataFrame with at least 'open' and 'close' columns.
        symbol: Ticker symbol for logging and plot titles.
        split_params: Dict with keys:
            - period_ratio (float): Fraction of total length to use as window.
            - period_years_max (int): Maximum window length in years.
            - n_periods (int): Number of rolling splits.

    Returns:
        Tuple of (price_open, indexes_open, price_close, indexes_close)
        as VectorBT split objects. Open prices are shifted by -1 to simulate
        next-day execution at the open.
    """
    logger.info(f"{symbol} - splitting data via rolling split")
    path = f"outputs/{symbol.replace('/', '-')}"

    window_len = int(split_params['period_ratio'] * len(df))
    window_len = min(window_len, split_params['period_years_max'] * 360)

    vbt_split_params = dict(n=split_params['n_periods'],
                            window_len=window_len,
                            left_to_right=True)

    figure = df['close'].vbt.rolling_split(**vbt_split_params, plot=True)
    figure.update_layout(width=800, height=400, title=f"rolling split - {symbol}")
    figure.add_annotation(
        text=f"Window Length: {window_len}<br>Total Length: {len(df)}",
        xref="paper", yref="paper",
        x=1, y=1, xanchor="right", yanchor="top",
        showarrow=False,
        font=dict(size=12)
    )
    figure.write_image(f"{path}/rolling_split.png")

    # Shift open by -1 to simulate execution at the next day's open price
    (price_open, indexes_open) = df['open'].shift(-1).vbt.rolling_split(**vbt_split_params)
    (price_close, indexes_close) = df['close'].vbt.rolling_split(**vbt_split_params)

    return price_open, indexes_open, price_close, indexes_close


def strategy_stats(open_price, close_price, strategy, strategy_params, symbol):
    """Run a full parameter grid backtest and return per-parameter statistics.

    Runs the strategy across all combinations in `strategy_params['param_ranges']`
    using VectorBT's portfolio simulation, then saves histogram plots of the
    raw parameter stats.

    Args:
        open_price: VectorBT split price object for execution prices (next-day open).
        close_price: VectorBT split price object used for signal generation.
        strategy: Strategy name string, currently only 'hhhl' is supported.
        strategy_params: Dict with keys 'param_ranges', 'fees', 'slippage', 'stop_loss'.
        symbol: Ticker symbol for logging and output paths.

    Returns:
        DataFrame of VectorBT portfolio stats indexed by parameter combinations
        and split index.
    """
    logger.info("calculating strategy stats")
    param_ranges = strategy_params['param_ranges']
    param_ranges = {key: np.arange(value[0], value[1] + 1) for key, value in param_ranges.items()}

    if strategy == 'hhhl':
        Strategy = HigherHighStrategy

    indicator = Strategy.run(close_price, **param_ranges, param_product=True)
    entries = indicator.entry_signal
    exits = indicator.exit_signal

    # Strip the 'custom_' prefix added by VectorBT's IndicatorFactory
    entries.columns.names = [param[7:] if 'custom_' in param else param for param in entries.columns.names]
    exits.columns.names = [param[7:] if 'custom_' in param else param for param in exits.columns.names]

    pf = vbt.Portfolio.from_signals(close_price,
                                    entries,
                                    exits,
                                    price=open_price,
                                    fees=strategy_params['fees'],
                                    slippage=strategy_params['slippage'],
                                    sl_stop=strategy_params['stop_loss'],
                                    freq='1D')
    df_stats = pf.stats(agg_func=None)
    df_stats['Max Drawdown Duration'] = df_stats['Max Drawdown Duration'].dt.days
    df_stats['Total Trades per year'] = df_stats['Total Trades'] * 360 / len(open_price)

    del pf
    gc.collect()

    plot_params_histograms(df_stats, symbol, strategy)
    return df_stats


def plot_params_histograms(df_stats, symbol, strategy):
    """Save histograms of key backtest metrics across all parameter combinations.

    Only includes rows with positive total return to keep histograms readable.
    Output saved to `outputs/<symbol>/<strategy>/<strategy>_raw_params_histograms.jpg`.

    Args:
        df_stats: DataFrame of VectorBT stats (output of strategy_stats).
        symbol: Ticker symbol for the output path.
        strategy: Strategy name for the output path and file name.
    """
    logger.info(f"{symbol} - {strategy} - making histograms for raw params stats")
    path = f"outputs/{symbol.replace('/', '-')}"
    df_stats = df_stats.loc[df_stats['Total Return [%]'] > 0, :]
    cols_to_hist = ['Total Return [%]', 'Max Drawdown [%]', 'Max Drawdown Duration', 'Total Trades',
                    'Total Trades per year', 'Sharpe Ratio', 'Calmar Ratio', 'Omega Ratio', 'Sortino Ratio']

    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    axes = axes.flatten()
    for i, (col, ax) in enumerate(zip(cols_to_hist, axes)):
        values_to_plot = df_stats[col][np.isfinite(df_stats[col])]
        values_to_plot.plot(kind='hist', title=col, bins=100, color='skyblue', edgecolor='black', ax=ax)
        ax.set_title(col)
        ax.set_xlabel('Value')
        ax.set_ylabel('Frequency')

    plt.tight_layout()
    plt.savefig(f"{path}/{strategy}/{strategy}_raw_params_histograms.jpg")


def strategy_grouped_stats(df_stats, period_length, symbol, strategy):
    """Aggregate per-split backtest stats by parameter combination.

    Drops the 'split_idx' level and computes describe() statistics grouped
    by the remaining parameter index levels. Adds coefficient-of-variation
    columns for return, drawdown, trade count, and Sharpe ratio.

    Args:
        df_stats: DataFrame of VectorBT stats with a MultiIndex including 'split_idx'.
        period_length: Unused; reserved for future period-length normalization.
        symbol: Ticker symbol for logging and output path.
        strategy: Strategy name for output path and file name.

    Returns:
        DataFrame of grouped describe() statistics, one row per parameter combo,
        also saved as a CSV.
    """
    logger.info(f"{symbol} - {strategy} - calculating grouped stats of the strategy")
    path = f"outputs/{symbol.replace('/', '-')}"
    columns_to_describe = ['Total Return [%]', 'Max Drawdown [%]',
                           'Max Drawdown Duration', 'Total Trades', 'Total Trades per year',
                           'Win Rate [%]', 'Sharpe Ratio']

    df_stats = df_stats.droplevel('split_idx')
    df_grouped_stats = df_stats.groupby(level=df_stats.index.names)[columns_to_describe].describe()
    df_grouped_stats.columns = df_grouped_stats.columns.map('_'.join)
    df_grouped_stats['Total Return [%]_std_perc'] = df_grouped_stats['Total Return [%]_std'] / df_grouped_stats['Total Return [%]_mean']
    df_grouped_stats['Max Drawdown [%]_std_perc'] = df_grouped_stats['Max Drawdown [%]_std'] / df_grouped_stats['Max Drawdown [%]_mean']
    df_grouped_stats['Total Trades_std_perc'] = df_grouped_stats['Total Trades_std'] / df_grouped_stats['Total Trades_mean']
    df_grouped_stats['Sharpe Ratio_std_perc'] = df_grouped_stats['Sharpe Ratio_std'] / df_grouped_stats['Sharpe Ratio_mean']

    df_grouped_stats.to_csv(f"{path}/{strategy}/{strategy}_params_grouped_stats.csv", header=True, index=True)
    return df_grouped_stats


def plot_returns(pf, params, symbol, strategy):
    """Save individual return plots for a list of parameter combinations.

    Args:
        pf: VectorBT Portfolio object.
        params: List of parameter tuples to plot.
        symbol: Ticker symbol for the output path.
        strategy: Strategy name for the output path and file names.
    """
    logger.info(f"{symbol} - plotting stats for final params")
    path = f"outputs/{symbol.replace('/', '-')}"
    for param in params:
        fig = pf[param].plot()
        fig.update_layout(title=str(param))
        fig.write_image(f"{path}/{strategy}/{strategy}_final_params_{str(param)}.png")


def pca_or_hc_params(pca_params, best_params_hc, df_returns):
    """Select the parameter set with the higher average pairwise return correlation.

    Higher correlation means the parameters are more similar to each other,
    which is undesirable for diversification. This function picks the set
    with higher internal correlation — used as a tie-breaker when both PCA
    and hierarchical clustering produce candidates.

    Args:
        pca_params: List of parameter tuples from PCA selection.
        best_params_hc: List of parameter tuples from hierarchical clustering.
        df_returns: DataFrame of daily returns, one column per parameter combo.

    Returns:
        The parameter list (pca_params or best_params_hc) with higher
        average pairwise correlation among its daily return series.
    """
    df_corr_pca = df_returns[pca_params].corr()
    upper_triangle = np.triu(df_corr_pca, k=1)
    avg_pca = np.mean(upper_triangle[upper_triangle != 0])

    df_corr_hc = df_returns[best_params_hc].corr()
    upper_triangle = np.triu(df_corr_hc, k=1)
    avg_hc = np.mean(upper_triangle[upper_triangle != 0])

    return pca_params if avg_pca > avg_hc else best_params_hc


def calculate_returns(df_stats, symbol, strategy, strategy_params, price_close, price_open):
    """Re-run the backtest for a specific subset of parameter combinations.

    Used after filtering/clustering to compute daily returns and detailed
    statistics only for the surviving parameter candidates.

    Args:
        df_stats: DataFrame indexed by parameter combinations to backtest.
        symbol: Ticker symbol for logging and output paths.
        strategy: Strategy name string.
        strategy_params: Dict with keys 'fees', 'slippage', 'stop_loss'.
        price_close: VectorBT split close price object.
        price_open: VectorBT split open price object (next-day execution).

    Returns:
        Tuple of (daily_ret, df_top_params_stats, pf):
            - daily_ret: DataFrame of daily returns per parameter combo.
            - df_top_params_stats: VectorBT stats for the subset.
            - pf: VectorBT Portfolio object.
    """
    logger.info(f"{symbol} - calculating returns of final params")
    path = f"outputs/{symbol.replace('/', '-')}"
    params_names = df_stats.index.names

    params_dict = {}
    for level_num, level_name in enumerate(df_stats.index.names):
        level_values = df_stats.index.get_level_values(level_num).tolist()
        params_dict[level_name] = level_values

    if strategy == 'hhhl':
        Strategy = HigherHighStrategy

    indicator = Strategy.run(price_close, **params_dict)
    entries = indicator.entry_signal
    exits = indicator.exit_signal

    if isinstance(entries, pd.DataFrame):
        entries.columns.names = params_names
        exits.columns.names = params_names
    else:
        entries = entries.to_frame()
        exits = exits.to_frame()
        entries.columns = df_stats.index
        exits.columns = df_stats.index

    pf = vbt.Portfolio.from_signals(price_close,
                                    entries,
                                    exits,
                                    price=price_open,
                                    fees=strategy_params['fees'],
                                    slippage=strategy_params['slippage'],
                                    sl_stop=strategy_params['stop_loss'],
                                    freq='1D')
    df_top_params_stats = pf.stats(agg_func=None)
    df_top_params_stats['Max Drawdown Duration'] = df_top_params_stats['Max Drawdown Duration'].dt.days
    df_top_params_stats['Total Trades per year'] = df_top_params_stats['Total Trades'] * 360 / len(price_close)
    df_top_params_stats['Period'] = df_top_params_stats['Period'].dt.days

    daily_ret = pf.daily_returns()

    daily_ret.to_csv(f"{path}/{strategy}/{strategy}_intermediate_params_returns.csv", header=True, index=True)
    df_top_params_stats.to_csv(f"{path}/{strategy}/{strategy}_intermediate_params_stats.csv", header=True, index=True)

    return daily_ret, df_top_params_stats, pf


def calculate_best_params_pca(df_returns, symbol, strategy, final_params_nr):
    """Select the most representative parameter combinations via PCA.

    Standardizes daily returns, applies PCA, and picks the parameter combo
    with the highest absolute loading on each principal component (unique
    selection — no combo appears twice).

    Args:
        df_returns: DataFrame of daily returns, one column per parameter combo.
        symbol: Ticker symbol for logging.
        strategy: Strategy name for output paths.
        final_params_nr: Number of parameter combinations to select.

    Returns:
        List of parameter tuples of length `final_params_nr`.
    """
    logger.info(f"{symbol} - getting best params via PCA")
    scaler = StandardScaler()
    scaled_df = scaler.fit_transform(df_returns)

    pca = PCA(n_components=final_params_nr)
    pca.fit(scaled_df)

    most_important_indices = set()
    for component in pca.components_:
        for importance in np.argsort(np.abs(component))[::-1]:
            if importance not in most_important_indices:
                most_important_indices.add(importance)
                break

    final_params = [df_returns.columns[idx] for idx in most_important_indices]
    plot_returns_corr(df_returns[final_params], symbol, strategy, 'final_params_PCA')
    return final_params


def plot_returns_corr(df_returns, symbol, strategy, title):
    """Save a heatmap of pairwise daily return correlations.

    Args:
        df_returns: DataFrame of daily returns, one column per parameter combo.
        symbol: Ticker symbol for the plot title and output path.
        strategy: Strategy name for the output path and file name.
        title: Suffix added to the output file name to distinguish multiple plots.
    """
    path = f"outputs/{symbol.replace('/', '-')}"
    df_corr = df_returns.corr()
    plt.figure(figsize=(8, 6))
    sns.heatmap(df_corr, cmap='coolwarm', linewidths=.5)
    plt.title(f"{symbol} - daily returns - correlations")
    plt.savefig(f"{path}/{strategy}/{strategy}_{title}_daily_returns_correlations.jpg")


def calculate_best_params_hc(df_returns, symbol, strategy, final_params_nr):
    """Select the most representative parameter combinations via hierarchical clustering.

    Builds a Ward-linkage dendrogram on the correlation-distance matrix of
    daily returns, cuts it into `final_params_nr` clusters, and picks the
    first parameter combo from each cluster as the representative.

    Args:
        df_returns: DataFrame of daily returns, one column per parameter combo.
        symbol: Ticker symbol for logging.
        strategy: Strategy name for output paths.
        final_params_nr: Number of clusters (and thus final parameter combos).

    Returns:
        List of parameter tuples, one representative per cluster.
        May be shorter than `final_params_nr` if some clusters are empty.
    """
    logger.info(f"{symbol} - getting best params via hierarchical clustering")

    df_corr = df_returns.corr()
    dist_matrix = squareform(1 - df_corr)
    Z = linkage(dist_matrix, 'ward')

    cluster_labels = fcluster(Z, final_params_nr, criterion='maxclust')

    final_params = []
    for i in range(1, final_params_nr + 1):
        cluster_vars = df_returns.columns[cluster_labels == i]
        try:
            # Take the first element as a simple representative; cluster may be empty
            # if fewer distinct clusters emerge than requested
            final_params.append(cluster_vars[0])
        except IndexError:
            pass

    plot_returns_corr(df_returns[final_params], symbol, strategy, 'final_params_HC')
    return final_params


def average_intra_cluster_distance(group):
    """Compute the mean pairwise Euclidean distance within a cluster.

    Args:
        group: 2D array-like of data points belonging to one cluster.

    Returns:
        Mean pairwise distance, or 0 if the cluster has fewer than 2 points.
    """
    pairwise_distances = pdist(group, metric='euclidean')
    return pairwise_distances.mean() if len(pairwise_distances) > 0 else 0


def flatten_dict(d, parent_key='', sep='_'):
    """Recursively flatten a nested dictionary by joining keys with a separator.

    Args:
        d: Dictionary to flatten (may contain nested dicts).
        parent_key: Key prefix carried from the parent level (used in recursion).
        sep: Separator string inserted between parent and child keys.

    Returns:
        Flat dictionary with compound keys.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def params_clustering(df_stats, symbol, strategy, clustering_params):
    """Cluster strategy parameter combinations by backtest performance metrics.

    Scales the selected metric columns to [0, 1], then runs K-Means with a
    dynamically determined number of clusters. Optionally generates elbow and
    silhouette plots for cluster count exploration.

    Args:
        df_stats: DataFrame of grouped backtest stats indexed by parameter combos.
        symbol: Ticker symbol for logging and output paths.
        strategy: Strategy name for output paths.
        clustering_params: Dict with keys:
            - cluster_cols (list): Columns used as clustering features.
            - explore (bool): Whether to generate cluster-exploration plots.
            - max_clusters (int): Upper bound for cluster count search.
            - scaling_factor (int): Divisor applied to row count to derive
              the dynamic cluster count.

    Returns:
        DataFrame equal to `df_stats` with an added 'cluster' column.
    """
    logger.info(f"{symbol} - clustering params")
    path = f"outputs/{symbol.replace('/', '-')}"

    df_to_cluster = df_stats[clustering_params['cluster_cols']]
    x_minmax = MinMaxScaler().fit_transform(df_to_cluster)
    n_init = 100

    if clustering_params['explore']:
        max_clusters = clustering_params['max_clusters']

        plt.figure()
        model = KMeans(n_init=n_init)
        visualizer = KElbowVisualizer(model, k=(2, max_clusters), metric='calinski_harabasz', timings=False)
        visualizer.fit(x_minmax)
        plt.savefig(f"{path}/{strategy}/{strategy}_cluster_plot_calinski_harabasz.png")

        plt.figure()
        visualizer = KElbowVisualizer(model, k=(2, max_clusters), metric='silhouette', timings=False)
        visualizer.fit(x_minmax)
        plt.savefig(f"{path}/{strategy}/{strategy}_cluster_plot_silhouette_index.png")

        plt.figure()
        visualizer = KElbowVisualizer(model, k=(2, max_clusters), metric='distortion', timings=False)
        visualizer.fit(x_minmax)
        plt.savefig(f"{path}/{strategy}/{strategy}_cluster_plot_distortion.png")

        plt.figure()
        db = []
        for i in range(2, max_clusters + 1):
            kmeans = KMeans(n_init=n_init, n_clusters=i)
            clusters = kmeans.fit_predict(x_minmax)
            db.append(davies_bouldin_score(x_minmax, clusters))  # lower is better
        s_db = pd.Series(db)
        s_db.plot()
        plt.savefig(f"{path}/{strategy}/{strategy}_cluster_plot_davies_bouldin.png")

    dynamic_clusters = min(clustering_params['max_clusters'],
                           max(1, x_minmax.shape[0] // clustering_params['scaling_factor']))

    km_final = KMeans(n_init=n_init, n_clusters=dynamic_clusters)
    km_final.fit(x_minmax)
    predicted_clusters = km_final.predict(x_minmax)

    df_cluster_x_minmax = pd.DataFrame(x_minmax)
    df_cluster_x_minmax['cluster'] = predicted_clusters
    avg_distance = df_cluster_x_minmax.groupby('cluster').apply(average_intra_cluster_distance)

    df_cluster_stats = df_stats.copy()
    df_cluster_stats['cluster'] = predicted_clusters
    params = df_cluster_stats.index.names
    df_cluster_stats.reset_index(inplace=True)

    cluster_groups = df_cluster_stats.groupby('cluster')

    cluster_stats = {}
    for cluster, group in cluster_groups:
        stats = {
            'nr_of_rows': len(group),
            'avg': group[['Total Return [%]_mean', 'Sharpe Ratio_mean', 'Max Drawdown [%]_mean',
                           'Total Trades_mean', 'Total Return [%]_std_perc', 'Sharpe Ratio_std_perc']].mean().to_dict(),
            'min': group[['Sharpe Ratio_min', 'Total Return [%]_min', 'Total Trades_min']].min().to_dict(),
            'max': group[['Max Drawdown [%]_max', 'Sharpe Ratio_std_perc', 'Total Return [%]_std_perc']].max().to_dict(),
            'unique_cnt': group[params].nunique().to_dict(),
            'value_counts': group[params].apply(pd.Series.value_counts).to_dict()
        }
        cluster_stats[cluster] = stats

    df_cluster_stats_result = pd.DataFrame()
    for key in cluster_stats.keys():
        flat_data = flatten_dict(cluster_stats[key])
        flat_data = {k.lstrip('_'): v for k, v in flat_data.items()}
        series = pd.Series(flat_data)
        df_cluster_stats_result[f'cluster_{key}'] = series

    df_distance = pd.Series(avg_distance).to_frame().T
    df_distance.columns = df_cluster_stats_result.columns
    df_distance.index = pd.Index(['avg_distance'])

    df_cluster_stats_result = pd.concat([df_distance, df_cluster_stats_result])

    df_cluster_stats.set_index(params, inplace=True)

    df_cluster_stats_result.to_csv(f"{path}/{strategy}/{strategy}_cluster_profiles.csv", index=True, header=True)
    df_cluster_stats.to_csv(f"{path}/{strategy}/{strategy}_cluster_params_with_clusters.csv", index=True, header=True)

    return df_cluster_stats


def get_best_params(df_stats, symbol, eval_params, strategy, strategy_params, price_close, price_open):
    """Select the final set of strategy parameter combinations for a symbol.

    Applies a multi-stage filtering and clustering pipeline:
    1. Hard filters on Sharpe ratio, total return, and trade frequency.
    2. Secondary filters on mean Sharpe and mean trade frequency.
    3. Hierarchical clustering or PCA when the filtered set is still too large.

    Args:
        df_stats: DataFrame of grouped backtest stats indexed by parameter combos
            (output of strategy_grouped_stats).
        symbol: Ticker symbol for logging and output paths.
        eval_params: Dict with keys:
            - filters: Dict of minimum thresholds (sharpe_ratio_min,
              total_returns_min, trades_in_year_min).
            - clustering: Dict controlling cluster count, within-cluster filters,
              and minimum item count to trigger clustering.
            - final_params: Dict with final_params_nr (target count) and
              force (bool, reserved for future forced-selection logic).
        strategy: Strategy name string.
        strategy_params: Dict passed through to calculate_returns.
        price_close: VectorBT split close price object.
        price_open: VectorBT split open price object.

    Returns:
        Tuple of (result_params, df_processed):
            - result_params: List of selected parameter tuples, or None if no
              candidates survive filtering.
            - df_processed: DataFrame from process_df_stats, or None.
    """
    logger.info(f"{symbol} - getting top params")
    path = f"outputs/{symbol.replace('/', '-')}/{strategy}"

    filters = eval_params['filters']
    clustering = eval_params['clustering']
    final_params = eval_params['final_params']

    df_stats_f = df_stats.loc[
        (df_stats['Sharpe Ratio_min'] > filters['sharpe_ratio_min']) &
        (df_stats['Total Return [%]_min'] > filters['total_returns_min']) &
        (df_stats['Total Trades per year_min'] > filters['trades_in_year_min']), :
    ]

    if final_params['force'] == False:
        if 0 < len(df_stats_f) <= final_params['final_params_nr']:
            df_returns, df_returns_stats, pf = calculate_returns(df_stats_f, symbol, strategy, strategy_params, price_close, price_open)
            plot_returns(pf, df_returns.columns.tolist(), symbol, strategy)
            plot_returns_corr(df_returns, symbol, strategy, 'final_params')
            df_returns_stats.to_csv(f"{path}/{strategy}_final_params_stats_1st_filters.csv", index=True, header=True)
            df_returns.to_csv(f"{path}/{strategy}_final_params_returns_1st_filters.csv", index=True, header=True)
            result_params = df_stats_f.index.to_frame().apply(list, axis='columns').tolist()
            return result_params, process_df_stats(df_returns_stats, result_params, symbol, strategy)

        elif final_params['final_params_nr'] < len(df_stats_f) < clustering['min_items_to_cluster']:
            df_stats_f_c = df_stats_f.loc[
                (df_stats_f['Total Trades per year_mean'] >= clustering['filters']['trades_in_year_mean']) &
                (df_stats_f['Sharpe Ratio_mean'] >= clustering['filters']['sharpe_ratio_mean']), :
            ]
            if 0 < len(df_stats_f_c) <= final_params['final_params_nr']:
                df_returns, df_returns_stats, pf = calculate_returns(df_stats_f_c, symbol, strategy, strategy_params, price_close, price_open)
                plot_returns(pf, df_returns.columns.tolist(), symbol, strategy)
                plot_returns_corr(df_returns, symbol, strategy, 'final_params')
                df_returns_stats.to_csv(f"{path}/{strategy}_final_params_stats_2nd_filters.csv", index=True, header=True)
                df_returns.to_csv(f"{path}/{strategy}_final_params_returns_2nd_filters.csv", index=True, header=True)
                result_params = df_stats_f_c.index.to_frame().apply(list, axis='columns').tolist()
                return result_params, process_df_stats(df_returns_stats, result_params, symbol, strategy)
            elif final_params['final_params_nr'] < len(df_stats_f_c):
                df_returns, df_returns_stats, pf = calculate_returns(df_stats_f_c, symbol, strategy, strategy_params, price_close, price_open)
                plot_returns_corr(df_returns, symbol, strategy, 'intermediate_params')
                best_params_pca = calculate_best_params_pca(df_returns, symbol, strategy, final_params['final_params_nr'])
                best_params_hc = calculate_best_params_hc(df_returns, symbol, strategy, final_params['final_params_nr'])
                result_params = pca_or_hc_params(best_params_pca, best_params_hc, df_returns)
                plot_returns(pf, result_params, symbol, strategy)
                plot_returns_corr(df_returns[result_params], symbol, strategy, 'final_params')
                df_returns_stats.loc[result_params, :].to_csv(f"{path}/{strategy}_final_params_stats_2nd_filters_pca_hc.csv", index=True, header=True)
                df_returns[result_params].to_csv(f"{path}/{strategy}_final_params_returns_2nd_filters_pca_hc.csv", index=True, header=True)
                return result_params, process_df_stats(df_returns_stats, result_params, symbol, strategy)
            else:
                return None, None

        elif len(df_stats_f) >= clustering['min_items_to_cluster']:
            df_clustered = params_clustering(df_stats_f, symbol, strategy, clustering)
            df_clustered_f = df_clustered.loc[
                (df_clustered['Total Trades per year_mean'] >= clustering['filters']['trades_in_year_mean']) &
                (df_clustered['Sharpe Ratio_mean'] >= clustering['filters']['sharpe_ratio_mean']), :
            ]

            if len(df_clustered_f) == 0:
                df_returns, df_returns_stats, pf = calculate_returns(df_stats_f, symbol, strategy, strategy_params, price_close, price_open)
                plot_returns_corr(df_returns, symbol, strategy, 'intermediate_params')
                best_params_pca = calculate_best_params_pca(df_returns, symbol, strategy, final_params['final_params_nr'])
                best_params_hc = calculate_best_params_hc(df_returns, symbol, strategy, final_params['final_params_nr'])
                result_params = pca_or_hc_params(best_params_pca, best_params_hc, df_returns)
                plot_returns(pf, result_params, symbol, strategy)
                plot_returns_corr(df_returns[result_params], symbol, strategy, 'final_params')
                df_returns_stats.loc[result_params, :].to_csv(f"{path}/{strategy}_final_params_stats_1st_filters_pca_hc.csv", index=True, header=True)
                df_returns[result_params].to_csv(f"{path}/{strategy}_final_params_returns_1st_filters_pca_hc.csv", index=True, header=True)
                return result_params, process_df_stats(df_returns_stats, result_params, symbol, strategy)
            else:
                df_cluster_f_s = df_clustered_f.groupby('cluster').apply(
                    lambda df: df.sort_values(by='Sharpe Ratio_std').head(clustering['filters']['items_from_cluster_nr'])
                ).droplevel(0)

            if 0 < len(df_cluster_f_s) <= final_params['final_params_nr']:
                df_returns, df_returns_stats, pf = calculate_returns(df_cluster_f_s, symbol, strategy, strategy_params, price_close, price_open)
                plot_returns(pf, df_returns.columns.tolist(), symbol, strategy)
                plot_returns_corr(df_returns, symbol, strategy, 'final_params')
                df_returns_stats.to_csv(f"{path}/{strategy}_final_params_stats_2nd_filters.csv", index=True, header=True)
                df_returns.to_csv(f"{path}/{strategy}_final_params_returns_2nd_filters.csv", index=True, header=True)
                result_params = df_cluster_f_s.index.to_frame().apply(list, axis='columns').tolist()
                return result_params, process_df_stats(df_returns_stats, result_params, symbol, strategy)
            elif final_params['final_params_nr'] < len(df_cluster_f_s):
                df_returns, df_returns_stats, pf = calculate_returns(df_cluster_f_s, symbol, strategy, strategy_params, price_close, price_open)
                plot_returns_corr(df_returns, symbol, strategy, 'intermediate_params')
                best_params_pca = calculate_best_params_pca(df_returns, symbol, strategy, final_params['final_params_nr'])
                best_params_hc = calculate_best_params_hc(df_returns, symbol, strategy, final_params['final_params_nr'])
                result_params = pca_or_hc_params(best_params_pca, best_params_hc, df_returns)
                plot_returns(pf, result_params, symbol, strategy)
                plot_returns_corr(df_returns[result_params], symbol, strategy, 'final_params')
                df_returns_stats.loc[result_params, :].to_csv(f"{path}/{strategy}_final_params_stats_after_clust.csv", index=True, header=True)
                df_returns[result_params].to_csv(f"{path}/{strategy}_final_params_returns_after_clust.csv", index=True, header=True)
                return result_params, process_df_stats(df_returns_stats, result_params, symbol, strategy)
            else:
                return None, None
        else:
            return None, None


def process_df_stats(df_int_returns, final_params, symbol, strategy):
    """Build a flat summary DataFrame marking which parameter combos were selected.

    Args:
        df_int_returns: DataFrame of stats for the intermediate parameter set,
            indexed by parameter combinations.
        final_params: List of parameter tuples that were selected as final.
        symbol: Ticker symbol added as a column.
        strategy: Strategy name added as a column.

    Returns:
        DataFrame with columns ['symbol', 'strategy', 'parameters', 'is_final']
        joined with `df_int_returns`, with the index reset to integers.
    """
    df = pd.DataFrame(index=df_int_returns.index, columns=['symbol', 'strategy', 'parameters', 'is_final'])
    df['symbol'] = symbol
    df['strategy'] = strategy
    df['parameters'] = [dict(zip(df.index.names, index)) for index in df.index.tolist()]
    df.loc[final_params, 'is_final'] = 1
    df = df.join(df_int_returns).reset_index(drop=True)
    return df
