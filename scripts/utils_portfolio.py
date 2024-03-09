from utils_strategy import HigherHighStrategy
import pandas as pd


strategies_directions = {
    'hhhl':'long'
}

def review_positions():
    pass

def closed_trades_cnt(symbols):
    pass #TODO

def running_weights(symbols, weights_params):
    
    if weights_params['running'] == 'win_rate':
        s_closed_trades_cnt = closed_trades_cnt(symbols)
        symbols_meeting_min_trades_cnt = (s_closed_trades_cnt >= weights_params['running']['min_trades']).sum()
        
        if symbols_meeting_min_trades_cnt >= weights_params['running']['min_symbols']:
            return True
        else:
            return False
  
def calculate_win_rates(symbols):
    pass #TODO

def check_weights(symbols, weights_params):
    
    if (weights_params['initial'] == 'equal') & (weights_params['running'] == 'equal'):
        one_symbol_weight = 1./len(symbols)
        return {symbol:one_symbol_weight for symbol in symbols}
    else:
        if running_weights(symbols, weights_params):
            if weights_params['running'] == 'win_rate':
                win_rates = calculate_win_rates(symbols)
                # calculate & return weights #TODO
        else: # initial
            if weights_params['initial'] == 'equal':
                one_symbol_weight = 1./len(symbols)
                return {symbol:one_symbol_weight for symbol in symbols}

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