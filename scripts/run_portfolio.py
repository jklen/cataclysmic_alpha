import pdb
import logging
import logging.config
import json
import pandas as pd
import click
import yaml
from datetime import datetime, timedelta
from utils_strategy import data_load
from utils_portfolio import check_weights, run_strategy, \
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
            #review_positions(symbol) # ci bol trigernuty stoploss
            df_symbol = data_load(symbol, 
                                  config[portfolio]['data_preference'],
                                  datetime(2000, 1, 1), 
                                  datetime.today().date())

            strategy = config[portfolio]['symbols'][symbol].keys()
            strategy = list(strategy)[0]
            strategy_params = config[portfolio]['symbols'][symbol][strategy]
            strategy_direction = strategies_directions[strategy]
            
            last_day = df_symbol.tail(1).index.get_level_values(1)[0].date()
            todays_date = datetime.today().date() - timedelta(days=1)
            
            if last_day == todays_date:
                entries, exits = run_strategy(df_symbol, 
                                            symbol, 
                                            strategy, 
                                            strategy_params)
                pdb.set_trace()
                today_entry, today_exit = entries.iloc[-1], exits.iloc[-1]
                orders_or_close(weights[symbol], 
                                symbol, 
                                today_entry,
                                today_exit,
                                strategy_direction,
                                config[portfolio]['portfolio_size'])
            
    
if __name__ == '__main__':
    main()
    
# trigernutie stop loss v alpace sa moze bit s 
#   vectorbt signalmi kvoli close price - ak toto nastane, cakaj na najblizsi exit signal,
#   a az potom pri dalsom signale otvor dalsiu poziciu
# tento script bude zbiehat len pred market open a bude davat riadne order open/close
# separe script bude bezat pocas market open, ktory kazdu pol hodinu checkne symboly,
#   ci bol trigernuty stop loss, ak ano, poziciu zavrie
# entry a exit signaly bude treba este upravit aby presne ako trade entry v vectorbt, asi:
#   - prvy moze byt len entry signal
#   - ak je otvoreny obchod, nasledovne entry signaly su ignorovane, caka sa len na exit signal
#   - ak nie je otvoreny ziadny obchod, caka sa len na entry signal, exit signaly su ignorovane
#   - ak nastane stav True/True, co potom? - podla vectorbt