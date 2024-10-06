
#%% load pacakes

import pandas as pd
import sys
import os
import pickle
from strategies import hhhl_ml1_strategy_logic
import pdb
import vectorbt as vbt
import plotly.io as pio
import logging
from datetime import datetime
import click
import yaml

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

# Create file handler (single log file for the entire script run)
logger_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
file_handler = logging.FileHandler(f'../logs_backtest/hhhl_ml1_backtest_{logger_timestamp}.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info('Logger is setup')

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    experiment = config['experiment_name']
    experiment_dir = f"../outputs_hhhl_ml1/{experiment}"
    symbols = [entry for entry in os.listdir(experiment_dir) if os.path.isdir(os.path.join(experiment_dir, entry))]
    params = yaml.safe_load(open(f"{experiment_dir}/config.yaml", 'r'))['strategy_params']['hhhl']['param_ranges']
    
    logger.info(f'Starting backtest of hhhl_ml1 strategy experiment - {experiment}')

    for symbol in symbols:
        logger.info(f'Starting backtesting symbol - {symbol}')
        symbol_dir = f"../outputs_hhhl_ml1/{experiment}/{symbol}"
        df_price = pd.read_csv(f"{symbol_dir}/df_price.csv", index_col='Date', parse_dates = ['Date'])
        with open(f"{symbol_dir}/train_stuff.pickle", 'rb') as f:
            train_stuff = pickle.load(f)
        backtest_dir = f"{symbol_dir}/backtest"
        os.makedirs(backtest_dir, exist_ok=True)

        stats_all = []
        for i in range(0, len(train_stuff['train_mins'])):
            dataset_train = df_price.loc[train_stuff['train_mins'][i]:train_stuff['train_maxs'][i]]
            dataset_test = df_price.loc[train_stuff['test_mins'][i]:train_stuff['test_maxs'][i]]
            
            logger.info(f'Calculating entry & exit signals on train dataset - {i}')
            train_result = hhhl_ml1_strategy_logic(dataset_train,
                                                    train_stuff['gridsearch_objs'][i],
                                                    params,
                                                    0.5)
            true_entry_signals_train = train_result[0]
            true_exit_signals_train = train_result[1]
            max_combs_all_train = train_result[2]
            max_probs_all_train = train_result[3]
            
            logger.info(f'Calculating entry & exit signals on test dataset - {i}')
            test_result = hhhl_ml1_strategy_logic(dataset_test,
                                                    train_stuff['gridsearch_objs'][i],
                                                    params,
                                                    0.5)
            true_entry_signals_test = test_result[0]
            true_exit_signals_test = test_result[1]
            max_combs_all_test = test_result[2]
            max_probs_all_test = test_result[3]

            logger.info(f'Creating train portfolio {i} and calculating stats')
            pf_train = vbt.Portfolio.from_signals(dataset_train['Adj Close'], 
                                            true_entry_signals_train, 
                                            true_exit_signals_train,
                                            price = dataset_train['Open'].shift(-1),
                                            direction = 'longonly', 
                                            freq='1D',
                                            sl_stop=0.1)
            stats_train = pf_train.stats(agg_func = None).T
            stats_train.columns = [f"{i}_train"]
            
            logger.info(f'Creating test portfolio {i} and calculating stats')
            pf_test = vbt.Portfolio.from_signals(dataset_test['Adj Close'], 
                                            true_entry_signals_test, 
                                            true_exit_signals_test,
                                            price = dataset_test['Open'].shift(-1),
                                            direction = 'longonly', 
                                            freq='1D',
                                            sl_stop = 0.1)
            stats_test  = pf_test.stats(agg_func = None).T
            stats_test.columns = [f"{i}_test"]
            
            stats_all.append(stats_train)
            stats_all.append(stats_test)
            
            df_info_train = pd.concat([true_entry_signals_train, true_exit_signals_train,
                                    max_combs_all_train, max_probs_all_train], axis = 1)
            df_info_test = pd.concat([true_entry_signals_test, true_exit_signals_test,
                                    max_combs_all_test, max_probs_all_test], axis = 1)
            
            logger.info('Dumping intermediate backtest results to disk')
            pf_train.trades.records_readable.to_csv(f"{backtest_dir}/train_{i}_trades.csv", index = True, header = True)
            df_info_train.to_csv(f"{backtest_dir}/df_info_train_{i}.csv", index = True, header = True)
            pf_test.trades.records_readable.to_csv(f"{backtest_dir}/test_{i}_trades.csv", index = True, header = True)
            df_info_test.to_csv(f"{backtest_dir}/df_info_test_{i}.csv", index = True, header = True)
        
            fig = pf_train.plot()
            fig.update_layout(title=f"train_{i}_stats")
            pio.write_html(fig, file = f"{backtest_dir}/train_{i}_stats.html")
            fig.write_image(f"{backtest_dir}/train_{i}_stats.png")
            
            fig = pf_test.plot()
            fig.update_layout(title=f"test_{i}_stats")
            pio.write_html(fig, file = f"{backtest_dir}/test_{i}_stats.html")
            fig.write_image(f"{backtest_dir}/test_{i}_stats.png")
            
        df_stats = pd.concat(stats_all, axis = 1)
        #pdb.set_trace()
        logger.info(f'Dumping final backtesting stats to disk')
        df_stats.to_csv(f"{backtest_dir}/df_stats.csv", index = True, header = True)
        logger.info(f'XXXXXXXXXXXXXXXX Backtesting symbo - {symbol} DONE XXXXXXXXXXXXXXXX')
    logger.info(f'-------------------- Backtests of all symbols in experiment - {experiment} DONE --------------------')
        
if __name__ == '__main__':
    main()

    #TODO
# liftcharty
# probability threshold ako param (ked zvysim, zvysi sa mi win rate strategie?)
# custom scoring metrika, eg. meria precision na top n podla predikovanej probability
# entry exit signaly obchodu musia byt rovnake ako v orig. strategii !!!
# koreluje nejaka metrika modelu s nejakou metrikou strategie?
# zanalyzovat obchody na train a test periodach strategie:
#   uspesny obchod vs. probability, liftcharty
#   trvanie obchodu vs. win rate
# v backteste test perioda premenliva, podla toho ci potrebujem retrenovat model - ako?
# scripty:
#   data prep
#   trening + mlflow
#   backtest
#   eval
