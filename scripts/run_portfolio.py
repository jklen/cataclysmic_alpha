import pdb
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import pandas as pd
import click
import yaml
from datetime import datetime, timedelta
from utils_strategy import data_load
from utils_portfolio import check_weights, run_strategy, position_sizes, \
    open_positions, close_positions, eval_position, strategies_directions, correct_date, \
    update_portfolio_state, update_portfolio_info, generate_id, crypto_map, \
    update_whole_portfolio_state
    
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
file_handler = TimedRotatingFileHandler(f'../logs/portfolio_{logger_timestamp}.log', when="h", interval=1, backupCount=0)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info('Logger is setup')

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    script_run_id = generate_id()
    timestamp = datetime.now()
    update_whole_portfolio_state(script_run_id, timestamp, config)
    
    for portfolio in config.keys():
        
        update_portfolio_info(portfolio, 
                              config[portfolio], 
                              script_run_id, 
                              timestamp)
        update_portfolio_state(portfolio, 
                               config[portfolio]['portfolio_size'], 
                               list(config[portfolio]['symbols'].keys()), 
                               script_run_id, 
                               timestamp)
        
        weights = check_weights(config[portfolio]['symbols'].keys(), config[portfolio]['weights'])
        logger.info(f"Portfolio {portfolio} symbols weights - {str(weights)}")
        trades = {}
        for symbol in config[portfolio]['symbols'].keys():
            df_symbol = data_load(symbol, 
                                  config[portfolio]['data_preference'],
                                  datetime(2000, 1, 1), 
                                  datetime.today().date())

            # po polnoci do rana (rozdiel cas pasma) alpaca vyhodi error - nesmiem kverovat ten isty den ako v us
            strategy = config[portfolio]['symbols'][symbol].keys()
            strategy = list(strategy)[0]
            strategy_params = config[portfolio]['symbols'][symbol][strategy]['params']
            strategy_direction = strategies_directions[strategy]
            stoploss = config[portfolio]['symbols'][symbol][strategy]['stoploss']
            take_profit = config[portfolio]['symbols'][symbol][strategy]['take_profit']
            try:
                last_day = df_symbol.tail(1).index.get_level_values('timestamp')[0].date()
            except:
                logger.warning(f"{portfolio} - {symbol} - data is empty, skipping symbol")
                continue
            if correct_date(symbol, last_day):
                entries, exits = run_strategy(df_symbol, 
                                            symbol, 
                                            strategy, 
                                            strategy_params)
                trades[symbol] = eval_position(df_symbol['close'],
                                               entries, 
                                               exits, 
                                               strategy_direction, 
                                               stoploss,
                                               take_profit)
                    
        # check na total non_marginable_amount?
        
        trades = {crypto_map[key] if key in crypto_map else key: value for key, value in trades.items()}
        logger.info(f"Portfolio {portfolio} symbols actions - {str(trades)}")
        close_positions(trades)
        sizes = position_sizes(portfolio,   
                               config[portfolio]['min_available_cash'],
                               weights,
                               script_run_id,
                               timestamp)
        logger.info(f"Portfolio {portfolio} position sizes - {str(sizes)}")
        open_positions(sizes, trades)
        
        logger.info(f"XXXXXXXXXXXXXXXXXXXX --- DONE --- XXXXXXXXXXXXXXXXXXXX") 
    
if __name__ == '__main__':
    main()
    
# trigernutie stop loss v alpace sa moze bit s 
#   vectorbt signalmi kvoli close price - ak toto nastane, cakaj na najblizsi exit signal,
#   a az potom pri dalsom signale otvor dalsiu poziciu
# tento script bude zbiehat len pred market open a bude davat riadne order open/close
# separe script bude bezat pocas market open, ktory kazdu pol hodinu checkne symboly,
#   ci bol trigernuty stop loss, ak ano, poziciu zavrie
# separe script ktory checkne po market open, ci moje ordre boli exekuovane

