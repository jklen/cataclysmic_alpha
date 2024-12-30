import click
import pickle
import shutil
import os
import yaml
import yfinance as yf
from utils_strategy import get_yf_data
from datetime import datetime
from strategies import HigherHighStrategy
import numpy as np
import vectorbt as vbt
import pandas_ta as ta
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV, StratifiedKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report
import pandas as pd
import pickle
import logging
import logging.config
import pdb
# Create logger
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)

# Create formatter``
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create console handler and set level to INFO
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create file handler (single log file for the entire script run)
logger_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
file_handler = logging.FileHandler(f'../logs_model_train/hhhl_ml1_train_models_prod_{logger_timestamp}.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info('Logger is setup')

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    logger.info(f"Starting training prod models - {config['experiment_name']}")
    if isinstance(config['symbols'], list):
        symbols = config['symbols']
    else:
        with open(config['symbols'], 'rb') as file:
            symbols = pickle.load(file)
    
    if config['rewrite_existing_symbols']:
        if os.path.exists(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}"):
            shutil.rmtree(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}")
        os.mkdir(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}")
        os.chmod(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}", 0o777)
    
    shutil.copy(path_config, f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}/config.yaml")        
    already_existing_symbols = [f.name for f in os.scandir(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}") if f.is_dir()]

    for symbol in symbols:
        try:
            
            if symbol not in already_existing_symbols:
                os.mkdir(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}/{symbol}")
                os.chmod(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}/{symbol}", 0o777)
                logger.info(f"Downloading price data for symbol - {symbol} from yfinance")
                
                data= get_yf_data(symbol, start=datetime(2000, 1,1), end=datetime.now())
                close_price = data.loc[:, 'close']
                open_price = data.loc[:, 'open']
                
                param_ranges = config['strategy_params']['hhhl']['param_ranges']
                stop_loss = config['strategy_params']['hhhl']['stop_loss']
                
                logger.info(f"Generating trades for symbol - {symbol}")
                
                param_ranges = {key: np.arange(value[0], value[1] + 1) for key, value in param_ranges.items()}
                indicator = HigherHighStrategy.run(close_price, **param_ranges, param_product = True)
                entries = indicator.entry_signal
                exits = indicator.exit_signal
                entries.columns.names = [param[7:] if 'custom_' in param else param for param in entries.columns.names]
                exits.columns.names = [param[7:] if 'custom_' in param else param for param in exits.columns.names]

                pf = vbt.Portfolio.from_signals(close_price, 
                                                entries, 
                                                exits,
                                                price = open_price.shift(-1),
                                                sl_stop = stop_loss, 
                                                freq='1D',
                                                direction = 'longonly')
                df_trades = pf.entry_trades.records_readable
                
                logger.info(f"Generating dataset with technical data for symbol - {symbol}")

                df_price = data
                df_price.drop(columns = ['adj close'], inplace = True)
                df_price.ta.strategy('All')
                df_price.drop(columns = ['SSF_10_2', 'TOS_STDEVALL_LR', 'TOS_STDEVALL_L_1', 
                                         'TOS_STDEVALL_U_1', 'TOS_STDEVALL_L_2', 'TOS_STDEVALL_U_2', 
                                         'TOS_STDEVALL_L_3', 'TOS_STDEVALL_U_3'], inplace = True) # + PSARs_0.02_0.2,
                df_price.to_csv(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}/{symbol}/df_price.csv", index = True, header = True)        
                df_trades[['window_entry', 'hh_hl_counts', 'window_exit', 'lh_counts']] = df_trades['Column'].tolist()
                df = df_trades.loc[:, ['window_entry', 'hh_hl_counts', 'window_exit', 'lh_counts', 'Entry Timestamp']]
                df['positive_return'] = df_trades['Return'] > 0
                df.set_index('Entry Timestamp', inplace = True)
                df = df_price.shift(1).join(df, how = 'right') # shift lebo den otvorenia pozicie berie close price + stats predosleho dna
                df = df.loc[df['positive_return'].notna(),:]
                
                x = df.iloc[:, :-1]
                y = df.iloc[:, -1]
                
                param_grid = {
                    'learning_rate': [0.01, 0.05, 0.1],
                    'max_iter': [100, 200],
                    'max_depth': [None, 3, 5],
                    'min_samples_leaf': [20, 50],
                    'l2_regularization': [0.0, 0.1]
                }
                
                train_stuff = {}                
                
                logger.info(f"Training symbol - {symbol}")
                
                train_min_date = x.index.min().date()
                train_max_date = x.index.max().date()
                train_trades_cnt = len(x)
                
                logger.info(f"Training period has {(train_max_date - train_min_date).days} days, nr of trades - {train_trades_cnt}")
                
                train_stuff['train_min'] = train_min_date
                train_stuff['train_max'] = train_max_date
                
                clf = HistGradientBoostingClassifier(class_weight='balanced', random_state=42)
                cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
                
                grid_search = GridSearchCV(
                    estimator=clf,
                    param_grid=param_grid,
                    cv=cv,  
                    scoring='precision',
                    n_jobs=-1, 
                    verbose=1,
                    return_train_score= True
                )
                                
                grid_search.fit(x, y)    
                train_stuff['gridsearch_obj'] = grid_search
                y_pred_train = grid_search.predict(x)
                
                gs_best_params = grid_search.best_params_
                train_class_report = classification_report(y, y_pred_train)
                
                train_stuff['gridsearch_best_params'] = gs_best_params
                train_stuff['train_class_report'] = train_class_report
                
                res = grid_search.cv_results_
                best_index = grid_search.best_index_
                mean_train_precision = res['mean_train_score'][best_index]
                mean_test_precision = res['mean_test_score'][best_index]
                train_stuff['mean_train_precision'] = mean_train_precision
                train_stuff['mean_test_precision'] = mean_test_precision
                
                logger.info('Best model params:\n%s', gs_best_params)
                logger.info('Train classification report:\n%s:', train_class_report)
                logger.info(f"Mean train precision - {mean_train_precision}")
                logger.info(f"Mean test precision - {mean_test_precision}")
                
                logger.info(f"Dumping train stuff - periods and model")
                with open(f"../outputs_hhhl_ml1_train_prod/{config['experiment_name']}/{symbol}/train_stuff.pickle", 'wb') as f:
                    pickle.dump(train_stuff, f)
                logger.info(f"XXXXXXXXXXXXXXXXXXXXXXXXXX - symbol {symbol} DONE - XXXXXXXXXXXXXXXXXXXXXXXXXX")
        except Exception as e:
            logger.error(f"Error occured: {e}")
            continue
    logger.info(f"XXXXXXXXXXXXXXXXXXXXXXXXXX - ALL SYMBOLS DONE - XXXXXXXXXXXXXXXXXXXXXXXXXX")

if __name__ == '__main__':
    main()