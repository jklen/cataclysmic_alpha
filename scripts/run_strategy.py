import click
import subprocess
import yaml
import sys
from utils import HigherHighStrategy, data_load, data_stats, data_split, strategy_stats,\
    strategy_grouped_stats
from datetime import datetime
from time import ctime
import pdb
import logging
import logging.config
import json

with open('../logging_config.json', 'r') as config_file:
    config_dict = json.load(config_file)

logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)
logger.info("Logging is set up.")

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    for symbol in config['symbols']:
        
        # data load
        
        print(f"{ctime()} - {symbol}")
        df = data_load(symbol,
                       config['data_preference'],
                       datetime(2000, 1, 1), 
                       datetime(2024, 1, 25))
        if df is not None:
            data_stats(df, symbol)
            open_price, _, close_price, _ = data_split(df, symbol, 
                                                       config['rolling_split_params'])
            print(open_price.shape, close_price.shape)
            df_stats = strategy_stats(open_price, 
                                       close_price, 
                                       config['strategy'], 
                                       config['strategy_params'])
            print(df_stats.shape)
            strategy_grouped_stats(df_stats, symbol)
    # portfolio stats
    # eval
    #   read & filter stats df
    #   clustering eval
    #   final clustering    
    
if __name__ == '__main__':
    main()