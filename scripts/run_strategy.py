import click
import subprocess
import yaml
import sys
from utils_strategy import HigherHighStrategy, data_load, data_stats, data_split, strategy_stats,\
    strategy_grouped_stats, get_best_params, create_path, process_df_stats
from datetime import datetime
from time import ctime
import pdb
import logging
import logging.config
import json
import pandas as pd

with open('../strategy_logging_config.json', 'r') as config_file:
    config_dict = json.load(config_file)

logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)
logger.info("Logging is set up.")

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    processed_stats_dfs_list = []
    for symbol in config['symbols']:
        
        # data load
        
        print(f"{ctime()} - {symbol}")
        df = data_load(symbol,
                       config['data_preference'],
                       datetime(2000, 1, 1), 
                       datetime(2024, 1, 25))
        if df is not None:
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
    df_stats_final = pd.concat(processed_stats_dfs_list, ignore_index = True)
    df_stats_final.to_csv(f"../outputs/all_intermediate_params.csv", index = False, header = True)
    # prefix p_ alebo param_ v nazvoch stlpcov?
    # symboly do separe fajlu (asi bude separe script na ich vygenerovanie)
    # daj filter na max drawdown %
    # upravit strategiu
    
if __name__ == '__main__':
    main()