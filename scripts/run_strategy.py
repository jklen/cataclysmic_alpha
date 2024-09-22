import click
import subprocess
import yaml
import sys
import shutil
import os
from utils_strategy import data_load, data_stats, data_split, strategy_stats,\
    strategy_grouped_stats, get_best_params, create_path, process_df_stats
from strategies import HigherHighStrategy
from datetime import datetime
from time import ctime
import pdb
import logging
import logging.config
from logging.handlers import TimedRotatingFileHandler
import json
import pandas as pd
import pickle
# Create logger
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create console handler and set level to INFO
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create file handler
logger_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
file_handler = TimedRotatingFileHandler(f'../logs/strategy_{logger_timestamp}.log', when="h", interval=1, backupCount=0)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info('Logger is setup')

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    processed_stats_dfs_list = []
    if isinstance(config['symbols'], list):
        symbols = config['symbols']
    else:
        with open(config['symbols'], 'rb') as file:
            symbols = pickle.load(file)
    
    if config['rewrite_existing_symbols']: 
        shutil.rmtree('../outputs')
        os.mkdir('../outputs')
        
    backtested_symbols = [f.name for f in os.scandir('../outputs') if f.is_dir()]

    for symbol in symbols:
        
        if symbol not in backtested_symbols:
            
            # data load
            
            print(f"{ctime()} - {symbol}")
            df = data_load(symbol,
                        config['data']['data_preference'],
                        config['data']['start_date'], 
                        config['data']['end_date'])
            if len(df) >= config['data']['min_days']:
                create_path(symbol.replace('/', '-'))
                data_stats(df, symbol)
                open_price, _, close_price, _ = data_split(df, symbol, 
                                                        config['rolling_split_params'])
                print(open_price.shape, close_price.shape)
                for strategy in config['strategies']:
                    create_path(symbol.replace('/', '-'), strategy)
                    #pdb.set_trace()
                    df_stats = strategy_stats(open_price, 
                                            close_price, 
                                            strategy, 
                                            config['strategy_params'][strategy],
                                            symbol)
                    
                    df_grouped_stats = strategy_grouped_stats(df_stats, 
                                                            len(open_price), 
                                                            symbol, 
                                                            strategy)
                    print(f"param combinations - {df_grouped_stats.shape}")
                    final_params, df_processed_stats = get_best_params(df_grouped_stats, 
                                    symbol, 
                                    config['eval_params'], 
                                    strategy, 
                                    config['strategy_params'][strategy],
                                    df['close'], 
                                    df['open'].shift(-1))
                    if df_processed_stats is not None:
                        processed_stats_dfs_list.append(df_processed_stats)
                    logger.info(f"{symbol} - final params - {final_params}")
            else:
                logger.warning(f"{symbol} - not enough data - just {len(df)} days")
    try:
        df_stats_final = pd.concat(processed_stats_dfs_list, ignore_index = True)
        current_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
        df_stats_final.to_csv(f"../outputs/all_intermediate_params_{current_time}.csv", index = False, header = True)
    except:
        logger.info(f"{symbol} - some problem with concat of all symbols params df")
    logger.info(f"XXXXXXXXXXXXXXXXXXXXX ---- DONE ---- XXXXXXXXXXXXXXXXXXXXX")

        # daj filter na max drawdown %
        # upravit strategiu
        
if __name__ == '__main__':
    main()