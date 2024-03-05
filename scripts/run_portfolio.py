import pdb
import logging
import logging.config
import json
import pandas as pd
import click
import yaml
from datetime import datetime
from utils_strategy import data_load
from utils_portfolio import check_weights, run_strategy, check_today_signals, \
    orders_or_close, review_positions, strategies_directions
    
with open('../portfolio_logging_config.json', 'r') as config_file:
    config_dict = json.load(config_file)

logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)
logger.info("Logging is set up.")

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    
    for portfolio in config.keys():
        weights = check_weights(config[portfolio]['symbols'].keys(), config[portfolio]['weights'])
        for symbol in config[portfolio]['symbols']:
            review_positions(symbol)
            #pdb.set_trace()
            df_symbol = data_load(symbol, 
                                  config[portfolio]['data_preference'],
                                  datetime(2000, 1, 1), 
                                  datetime.today().date())
            print(df_symbol.tail(1))
            strategy = config[portfolio][symbol].keys()[0]
            strategy_params = config[portfolio][symbol][strategy]
            strategy_direction = strategies_directions[strategy]
            entries, exits = run_strategy(df_symbol, 
                                          symbol, 
                                          strategy, 
                                          strategy_params) #TODO
            today_entry, today_exit = check_today_signals(entries, exits) #true/false
            orders_or_close(weights[symbol], 
                            symbol, 
                            today_entry,
                            today_exit,
                            strategy_direction)
            
    
if __name__ == '__main__':
    main()
    
# ak market order + stop order - trigernutie stop loss sa moze bit s vectorbt signalmi kvoli close priceyg