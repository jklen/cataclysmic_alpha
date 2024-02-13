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
import seaborn as sns
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import davies_bouldin_score
from sklearn.cluster import KMeans
from yellowbrick.cluster import KElbowVisualizer
from scipy.spatial.distance import pdist, squareform
import pickle

logger = logging.getLogger(__name__)

# Define the strategy logic in a function
def hh_hl_strategy_logic(close, window_entry, hh_hl_counts, 
                   window_exit, lh_counts):
    
    if isinstance(close, np.ndarray):
        close = pd.DataFrame(close)
        
    if (hh_hl_counts > window_entry) or (lh_counts > window_exit):
        df_empty = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
        return df_empty, df_empty
    
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
    
    (price_open, indexes_open) = df['open'].shift(-1).vbt.rolling_split(**split_params) # execution at next day open
    (price_close, indexes_close) = df['close'].vbt.rolling_split(**split_params)
    
    return price_open, indexes_open, price_close, indexes_close

def strategy_stats(open_price, close_price, strategy, strategy_params):
    logger.info("calculating strategy stats")    
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
                                    sl_stop = strategy_params['stop_loss'], 
                                    freq='1D')
    df_stats = pf.stats(agg_func=None)
    
    return df_stats

def strategy_grouped_stats(df_stats, period_length, symbol, strategy):
    logger.info(f"{symbol} - {strategy} - calculating grouped stats of the strategy")
    path = f"../outputs/{symbol.replace('/', '-')}"
    columns_to_describe = ['Total Return [%]', 'Max Drawdown [%]', 
                           'Max Drawdown Duration', 'Total Trades', 'Total Trades per year',
                           'Win Rate [%]', 'Sharpe Ratio']
    df_stats['Max Drawdown Duration'] = df_stats['Max Drawdown Duration'].dt.days
    df_stats['Total Trades per year'] = df_stats['Total Trades']*360/period_length

    df_stats = df_stats.droplevel('split_idx')
    df_grouped_stats = df_stats.groupby(level=df_stats.index.names)[columns_to_describe].describe()
    df_grouped_stats.columns = df_grouped_stats.columns.map('_'.join)
    df_grouped_stats['Total Return [%]_std_perc'] = df_grouped_stats['Total Return [%]_std']/df_grouped_stats['Total Return [%]_mean']
    df_grouped_stats['Max Drawdown [%]_std_perc'] = df_grouped_stats['Max Drawdown [%]_std']/df_grouped_stats['Max Drawdown [%]_mean']
    df_grouped_stats['Total Trades_std_perc'] = df_grouped_stats['Total Trades_std']/df_grouped_stats['Total Trades_mean']
    df_grouped_stats['Sharpe Ratio_std_perc'] = df_grouped_stats['Sharpe Ratio_std']/df_grouped_stats['Sharpe Ratio_mean']
        
    df_grouped_stats.to_csv(f"{path}/{strategy}_grouped_stats.csv", header = True, index = True)
        
    return df_grouped_stats

def calculate_returns(df_stats, symbol, strategy, strategy_params, price_close, price_open):
    #pdb.set_trace()
    logger.info(f"{symbol} - calculating returns of final params")
    path = f"../outputs/{symbol.replace('/', '-')}"
    params = df_stats.index.to_frame().apply(list, axis = 'columns').tolist()
    params_dict = {'window_entry': [item[0] for item in params], 
          'hh_hl_counts': [item[1] for item in params],
          'window_exit': [item[2] for item in params], 
          'lh_counts': [item[3] for item in params]}
    
    if strategy == 'hhhl':
        Strategy = HigherHighStrategy
        
    indicator = Strategy.run(price_close, **params_dict)
    entries = indicator.entry_signal
    exits = indicator.exit_signal

    pf = vbt.Portfolio.from_signals(price_close, 
                                    entries, 
                                    exits,
                                    price = price_open,
                                    fees=strategy_params['fees'], 
                                    slippage=strategy_params['slippage'],
                                    sl_stop = strategy_params['stop_loss'],
                                    freq='1D')
    df_top_params_stats = pf.stats(agg_func=None)
    daily_ret = pf.daily_returns()
    
    daily_ret.to_csv(f"{path}/{strategy}_top_params_returns.csv", header = True, index = True)
    df_top_params_stats.to_csv(f"{path}/{strategy}_top_params_stats.csv", header = True, index = True)
    
    return daily_ret

def calculate_best_params_pca(df_returns, symbol, strategy, final_params_nr):
    logger.info(f"{symbol} - getting best params via PCA")
    path = f"../outputs/{symbol.replace('/', '-')}"
    # Standardize the data
    scaler = StandardScaler()
    scaled_df = scaler.fit_transform(df_returns)

    # Apply PCA
    pca = PCA(n_components=final_params_nr)
    pca.fit(scaled_df)

    # Get indices of the most important variable for each component, ensuring uniqueness
    most_important_indices = set()
    for component in pca.components_:
        for importance in np.argsort(np.abs(component))[::-1]:
            if importance not in most_important_indices:
                most_important_indices.add(importance)
                break

    # Get the names of these variables
    final_params = [df_returns.columns[idx] for idx in most_important_indices]
    
    df_corr_final = df_returns[final_params].corr()
    plt.figure(figsize=(8, 6))
    sns.heatmap(df_corr_final, cmap='coolwarm', linewidths=.5)
    plt.title(f"{symbol} - daily returns - final params PCA - correlations")
    plt.savefig(f"{path}/{strategy}_daily_returns_correlations_final_params_pca.jpg")

    return final_params

def calculate_best_params_hc(df_returns, symbol, strategy, final_params_nr):
    logger.info(f"{symbol} - getting best params via hierarchical clustering")
    path = f"../outputs/{symbol.replace('/', '-')}"
    
    df_corr = df_returns.corr()
    plt.figure(figsize=(8, 6))
    sns.heatmap(df_corr, cmap='coolwarm', linewidths=.5)
    plt.title(f"{symbol} - daily returns - correlations")
    plt.savefig(f"{path}/{strategy}_daily_returns_correlations.jpg")
    
    #pdb.set_trace()
    dist_matrix = squareform(1 - df_corr)
    Z = linkage(dist_matrix, 'ward')
    num_clusters = final_params_nr

    cluster_labels = fcluster(Z, num_clusters, criterion='maxclust')

    final_params = []
    for i in range(1, num_clusters+1):
        cluster_vars = df_returns.columns[cluster_labels == i]
        final_params.append(cluster_vars[0])  # Choosing the first variable as an example

    df_corr_final = df_returns[final_params].corr()
    plt.figure(figsize=(8, 6))
    sns.heatmap(df_corr_final, cmap='coolwarm', linewidths=.5)
    plt.title(f"{symbol} - daily returns - final params HC - correlations")
    plt.savefig(f"{path}/{strategy}_daily_returns_correlations_final_params_hc.jpg")
    
    return final_params

def average_intra_cluster_similarity(group):
    pairwise_distances = pdist(group, metric='euclidean')
    return pairwise_distances.mean() if len(pairwise_distances) > 0 else 0

def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
    
def params_clustering(df_stats, symbol, strategy, clustering_params):
    logger.info(f"{symbol} - clustering params")
    path = f"../outputs/{symbol.replace('/', '-')}"
    
    # data to clustering
    
    df_to_cluster = df_stats[clustering_params['cluster_cols']]
    x_minmax = MinMaxScaler().fit_transform(df_to_cluster)
    
    #pdb.set_trace()
    
    # eploring clusters
    
    if clustering_params['explore']:
        max_clusters = clustering_params['max_clusters']
        n_init = 100
        
        plt.figure()
        model = KMeans(n_init = n_init)
        visualizer = KElbowVisualizer(
            model, k=(2,max_clusters), metric='calinski_harabasz', timings=False
        )
        visualizer.fit(x_minmax)    
        plt.savefig(f"{path}/{strategy}_cluster_calinski_harabasz.png")
        
        plt.figure()
        visualizer = KElbowVisualizer(
            model, k=(2,max_clusters), metric='silhouette', timings=False
        )
        visualizer.fit(x_minmax)    
        plt.savefig(f"{path}/{strategy}_cluster_silhuette_index.png")
        
        plt.figure()
        visualizer = KElbowVisualizer(
            model, k=(2,max_clusters), metric='distortion', timings=False
        )
        visualizer.fit(x_minmax)    
        plt.savefig(f"{path}/{strategy}_cluster_distortion.png")
        
        plt.figure()
        db = []
        for i in range(2, max_clusters + 1):
            kmeans = KMeans(n_init = n_init, n_clusters = i)
            clusters = kmeans.fit_predict(x_minmax)
            db.append(davies_bouldin_score(x_minmax, clusters)) # lower values better clustering
        s_db = pd.Series(db)
        s_db.plot()
        plt.savefig(f"{path}/{strategy}_cluster_davies_bouldin.png")
        
    # final clustering
    
    dynamic_clusters = min(clustering_params['max_clusters'], max(1, x_minmax.shape[0] // clustering_params['scaling_factor']))

    km_final = KMeans(n_init = n_init, n_clusters = dynamic_clusters)
    km_final.fit(x_minmax)
    predicted_clusters = km_final.predict(x_minmax)
    
    # clustering eval
    
    df_cluster_x_minmax = pd.DataFrame(x_minmax)
    df_cluster_x_minmax['cluster'] = predicted_clusters
    avg_similarity = df_cluster_x_minmax.groupby('cluster').apply(average_intra_cluster_similarity)
    #pdb.set_trace()
    df_cluster_stats = df_stats
    df_cluster_stats['cluster'] = predicted_clusters
    df_cluster_stats.reset_index(inplace = True)
    # Group by the 'cluster' column
    cluster_groups = df_cluster_stats.groupby('cluster')

    # Initialize a dictionary to hold your statistics
    cluster_stats = {}

    # Loop through each group to calculate statistics
    for cluster, group in cluster_groups:
        stats = {
            'nr_of_rows': len(group),
            'avg': group[['Total Return [%]_mean', 'Sharpe Ratio_mean', 'Max Drawdown [%]_mean', 
                                    'Total Trades_mean', 'Total Return [%]_std_perc', 'Sharpe Ratio_std_perc']].mean().to_dict(),
            'min': group[['Sharpe Ratio_min', 'Total Return [%]_min', 'Total Trades_min']].min().to_dict(),
            'max': group[['Max Drawdown [%]_max', 'Sharpe Ratio_std_perc', 'Total Return [%]_std_perc']].max().to_dict(),
            'unique_cnt': group[['custom_window_entry', 'custom_hh_hl_counts','custom_window_exit', 'custom_lh_counts']].nunique().to_dict(),
            'value_counts': group[['custom_window_entry', 'custom_hh_hl_counts','custom_window_exit', 'custom_lh_counts']].apply(pd.Series.value_counts).to_dict()
        }
        cluster_stats[cluster] = stats
        
    df_cluster_stats_result = pd.DataFrame()
    for key in cluster_stats.keys():
        # Flattening the nested dictionary
        flat_data = flatten_dict(cluster_stats[key])

        # Remove the separator at the beginning of the keys in the top level
        flat_data = {k.lstrip('_'): v for k, v in flat_data.items()}

        # Converting to Pandas Series
        series = pd.Series(flat_data)
        
        df_cluster_stats_result[f'cluster_{key}'] = series
    
    df_similarity = pd.Series(avg_similarity).to_frame().T
    df_similarity.columns = df_cluster_stats_result.columns
    df_similarity.index = pd.Index(['avg_similarity'])

    df_cluster_stats_result  = pd.concat([df_similarity, df_cluster_stats_result])

    df_cluster_stats_result.to_csv(f"{path}/{strategy}_clustering_profiles.csv", index = True, header = True)
    df_cluster_stats.to_csv(f"{path}/{strategy}_clustering_params_with_clusters.csv", index = False, header = True)

    # changing param names to original
    #pdb.set_trace()
    df_cluster_stats.rename(columns = {'custom_window_entry':'window_entry',
                                       'custom_hh_hl_counts':'hh_hl_counts',
                                       'custom_window_exit':'window_exit', 
                                       'custom_lh_counts':'lh_counts'}, inplace = True)
    df_cluster_stats.set_index(['window_entry', 'hh_hl_counts','window_exit', 'lh_counts'], inplace = True)
    return df_cluster_stats

def get_best_params(df_stats, symbol, eval_params, strategy, strategy_params, price_close, price_open):
    logger.info(f"{symbol} - getting top params")
    
    filters = eval_params['filters']
    clustering = eval_params['clustering']
    final_params = eval_params['final_params']
        
    df_stats_f = df_stats.loc[(df_stats['Sharpe Ratio_min'] > filters['sharpe_ratio_min']) &
                            (df_stats['Total Return [%]_min'] > filters['total_returns_min']) &
                            (df_stats['Total Trades per year_min'] > filters['trades_in_year_min']),:]
    
    if final_params['force'] == False:
        if 0 < len(df_stats_f) <= final_params['final_params_nr']:
            df_returns = calculate_returns(df_stats_f, symbol, strategy, strategy_params, price_close, price_open)
            return df_stats_f.index.to_frame().apply(list, axis = 'columns').tolist()
        elif final_params['final_params_nr'] < len(df_stats_f) < clustering['min_items_to_cluster']:
            df_stats_f_c = df_stats_f.loc[(df_stats_f['Total Trades per year_mean'] >= clustering['filters']['trades_in_year_mean']) &
                                          (df_stats_f['Sharpe Ratio_mean'] >= clustering['filters']['sharpe_ratio_mean']),:]
            if 0 < len(df_stats_f_c) <= final_params['final_params_nr']:
                df_returns = calculate_returns(df_stats_f_c, symbol, strategy, strategy_params, price_close, price_open)
                return df_stats_f_c.index
            elif final_params['final_params_nr'] < len(df_stats_f_c):
                df_returns = calculate_returns(df_stats_f_c, symbol, strategy, strategy_params, price_close, price_open)
                best_params_pca = calculate_best_params_pca(df_returns, symbol, strategy, final_params['final_params_nr'])
                best_params_hc = calculate_best_params_hc(df_returns, symbol, strategy, final_params['final_params_nr'])
                return best_params_pca, best_params_hc
            else:
                return None
        elif len(df_stats_f) >= clustering['min_items_to_cluster']:
            df_clustered = params_clustering(df_stats_f, symbol, strategy, clustering)
            df_clustered_f = df_clustered.loc[(df_clustered['Total Trades per year_mean'] >= clustering['filters']['trades_in_year_mean']) &
                                          (df_clustered['Sharpe Ratio_mean'] >= clustering['filters']['sharpe_ratio_mean']),:]
            df_cluster_f_s = df_clustered_f.groupby('cluster').apply(lambda df: df.sort_values(by = 'Sharpe Ratio_std') \
                .head(clustering['filters']['items_from_cluster_nr'])).droplevel(0)       
            if 0 < len(df_cluster_f_s) <= final_params['final_params_nr']:
                df_returns = calculate_returns(df_cluster_f_s, symbol, strategy, strategy_params, price_close, price_open)
                return df_cluster_f_s.index.to_frame().apply(list, axis = 'columns').tolist()
            elif final_params['final_params_nr'] < len(df_cluster_f_s):
                df_returns = calculate_returns(df_cluster_f_s, symbol, strategy, strategy_params, price_close, price_open)
                best_params_pca = calculate_best_params_pca(df_returns, symbol, strategy, final_params['final_params_nr'])
                best_params_hc = calculate_best_params_hc(df_returns, symbol, strategy, final_params['final_params_nr'])
                return best_params_pca, best_params_hc
            else:
                return None
        else:
            return None
            
                
    print(df_stats.shape)
    
#     pseudocode:

# elif force == True:
#   if len(params_after_filtering) is between 0 - final_params_nr:
#     do_realase_filter_constraits - aby ich bolo aspon 5
#     do_sort_by_std_and_take_top_params
#     return final_params
#   elif len(params_after_filtering) is between - final_params_nr - min_items_to_cluster:
#     do_release_filter_constraints - aby ich bolo aspon min_items_to_cluster # tu moze byt alternative, chod rovno na returns calc
#     do_clustering
#     do_within_cluster_filters
#     do_top_params_from_each_cluster
#     if len(params_after_top_params_from_each_cluster) is between 0 -final_params_nr:
#       do_release_clustering_constraints - aby ich bolo aspon 5 - aj vratane top_params_from each_cluster
#       do_top_params_from_each_cluster
#       do_sort_by_std_and_take_top_params
#     elif len(params_after_top_params_from_each_cluster) is > final_params_nr:
#       do_calculate_daily_returns
#       do_calcualte_correlations_of_daily_returns
#       do_hierarchical_clustering_or/and_pca
#       return final_params
#   elif len(params_after_filtering) is > min_items_to_cluster:
#     do_clustering
#     do_within_cluster_filters
#     do_top_params_from_each_cluster
#     if len(params_after_top_params_from_each_cluster) is between 0 -final_params_nr:
#       do_release_clustering_constraints - aby ich bolo aspon 5 - aj vratane top_params_from each_cluster
#       do_top_params_from_each_cluster
#       do_sort_by_std_and_take_top_params
#     elif len(params_after_top_params_from_each_cluster) is > final_params_nr:
#       do_calculate_daily_returns
#       do_calcualte_correlations_of_daily_returns
#       do_hierarchical_clustering_or/and_pca
#       return final_params


