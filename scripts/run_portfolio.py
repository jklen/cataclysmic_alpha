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
    orders_or_close, review_positions
    
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
        review_positions() # check v alpace ci nebol trigernuty stop loss alebo take profit
        weights = check_weights(config[portfolio])
        for symbol in config[portfolio]['symbols']:
            #pdb.set_trace()
            df_symbol = data_load(symbol, 
                                  config[portfolio]['data_preference'],
                                  datetime(2000, 1, 1), 
                                  datetime(2024, 2, 29))
            print(df_symbol.tail(1))
            for strategy in config[portfolio]['symbols'][symbol].keys():
                entries, exits = run_strategy(portfolio, 
                                              df_symbol, 
                                              symbol, 
                                              strategy, 
                                              strategy_params)
                today_entry, today_exit = check_today_signals(entries, exits)
                orders_or_close(weights, 
                                portfolio, 
                                symbol, 
                                strategy, 
                                today_entry.loc[today_entry == True],
                                today_exit.loc[today_exit == True])
            
    
if __name__ == '__main__':
    main()
    
    
#   1. spustim script, ktory natiahne najnovsie data z alpacy alebo yf, pre kazdy symbol
#   2. pre kazdu strategiu a kazdu parameter kombinaciu chekni ci je dnes entry alebo exit signal
#   3. vyhodnot vahy (bude ako 1. po prvej iteracii)
#   4. ak entry signal, daj order. Ked bude order filled, id pozicie prirad ku konkretnemu portfoliu
#   5. ak exit signal, closni poziciu pre dany symbol, strategiu a param kombinaciu pod danym postion id
# 
# ak market order + stop order - trigernutie stop loss sa moze bit s vectorbt signalmi