from utils_strategy import HigherHighStrategy
import pandas as pd


strategies_directions = {
    'hhhl':'long'
}

def review_positions():
    pass

def check_weights():
    pass

def run_strategy(df_symbol, symbol, strategy, strategy_params):
    if strategy == 'hhhl':
        Strategy = HigherHighStrategy
    
    close_price = df_symbol['close']
    indicator = Strategy.run(close_price, **strategy_params)
    entries = indicator.entry_signal
    exits = indicator.exit_signal
    
    return entries, exits    

def orders_or_close():
    pass