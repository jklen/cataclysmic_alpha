import pdb
import logging
import logging.config
import json
import pandas as pd
import click
import yaml
from datetime import datetime, timedelta
from utils_strategy import data_load
from utils_portfolio import check_weights, run_strategy, position_sizes, \
    open_positions, close_positions, eval_position , strategies_directions, correct_date
    
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
        trades = {}
        for symbol in config[portfolio]['symbols']:
            df_symbol = data_load(symbol, 
                                  config[portfolio]['data_preference'],
                                  datetime(2000, 1, 1), 
                                  datetime.today().date())

            strategy = config[portfolio]['symbols'][symbol].keys()
            strategy = list(strategy)[0]
            strategy_params = config[portfolio]['symbols'][symbol][strategy]
            strategy_direction = strategies_directions[strategy]
            
            last_day = df_symbol.tail(1).index.get_level_values('timestamp')[0].date()
            print(portfolio, symbol, weights)
            
            if correct_date(symbol, last_day):
                entries, exits = run_strategy(df_symbol, 
                                            symbol, 
                                            strategy, 
                                            strategy_params)
                trades[symbol] = eval_position(symbol, entries, exits, strategy, strategy_params) # strategy_params - direction, stoploss - zbehne vbt.portfolio.from_signals, symbol bude mat: 'entry', 'exit', alebo None
            
        close_positions(trades)
    
    # check na total non_marginable_amount?
    # ako vyratat velkost pozicie v ramci jedneho portfolia?
    #   pl otvorenej pozicie - market_value - cost_basis, unrealized_pl - abs profit/loss, unrealized_plpc - % profit/loss
        sizes = position_sizes(trades)
        open_positions(sizes)
            
    
if __name__ == '__main__':
    main()
    
# trigernutie stop loss v alpace sa moze bit s 
#   vectorbt signalmi kvoli close price - ak toto nastane, cakaj na najblizsi exit signal,
#   a az potom pri dalsom signale otvor dalsiu poziciu
# tento script bude zbiehat len pred market open a bude davat riadne order open/close
# separe script bude bezat pocas market open, ktory kazdu pol hodinu checkne symboly,
#   ci bol trigernuty stop loss, ak ano, poziciu zavrie

#TODO otestuj ci v v den ked zatvaram trade mozem zaroven aj otvorit novy
