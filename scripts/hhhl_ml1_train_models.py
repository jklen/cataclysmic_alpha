import click
import pickle
import shutil
import os
import yaml
import yfinance as yf
from datetime import datetime
from strategies import HigherHighStrategy
import numpy as np
import vectorbt as vbt
import pandas_ta as ta
from sklearn.model_selection import train_test_split, TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report
import pandas as pd
import pickle
import logging
import logging.config
from logging.handlers import TimedRotatingFileHandler

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
file_handler = TimedRotatingFileHandler(f'../logs_model_train/hhhl_ml1_train_models_{logger_timestamp}.log', when="h", interval=1, backupCount=0)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info('Logger is setup')

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    if isinstance(config['symbols'], list):
        symbols = config['symbols']
    else:
        with open(config['symbols'], 'rb') as file:
            symbols = pickle.load(file)
    
    if config['rewrite_existing_symbols']: 
        shutil.rmtree('../outputs_hhhl_ml1')
        os.mkdir('../outputs_hhhl_ml1')
        
    already_existing_symbols = [f.name for f in os.scandir('../outputs_hhhl_ml1') if f.is_dir()]

    for symbol in symbols:
        
        if symbol not in already_existing_symbols:
            os.mkdir(f"../outputs_hhhl_ml1/{symbol}")
            logger.info(f"Downloading price data for symbol - {symbol} from yfinance")
            
            data= yf.download(symbol, start=datetime(2000, 1,1), end=datetime.now())
            close_price = data.loc[:, 'Adj Close']
            open_price = data.loc[:, 'Open']
            
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
            
            df_price = data.loc[:, (slice(None), 'AAPL')].droplevel(1, axis = 'columns')
            df_price.ta.strategy('All')            
            df_trades[['window_entry', 'hh_hl_counts', 'window_exit', 'lh_counts']] = df_trades['Column'].tolist()
            df = df_trades.loc[:, ['window_entry', 'hh_hl_counts', 'window_exit', 'lh_counts', 'Entry Timestamp']]
            df['positive_return'] = df_trades['Return'] > 0
            df.set_index('Entry Timestamp', inplace = True)
            df = df_price.shift(1).join(df, how = 'right') # shift lebo den otvorenia pozicie berie close price + stats predosleho dna
            df = df.loc[df['positive_return'].notna(),:]
            
            x = df.iloc[:, :-1]
            y = df.iloc[:, -1]
            tscv = TimeSeriesSplit(**config['timeseries_split'])
            
            param_grid = {
                'learning_rate': [0.01, 0.05, 0.1],
                'max_iter': [100, 200],
                'max_depth': [None, 3, 5],
                'min_samples_leaf': [20, 50],
                'l2_regularization': [0.0, 0.1]
            }
            
            train_stuff = {'train_mins':[],
                'train_maxs':[],
                'test_mins':[],
                'test_maxs':[],
                'gridsearch_objs':[]
            }

            clf = HistGradientBoostingClassifier(class_weight='balanced', random_state=42)

            grid_search = GridSearchCV(
                estimator=clf,
                param_grid=param_grid,
                cv=3,  
                scoring='precision',
                n_jobs=-1, 
                verbose=1
            )

            logger.info(f"Starting training loop for symbol - {symbol}")
            
            for train_index, test_index in tscv.split(x):
                train_stuff['train_mins'].append(x.iloc[train_index].index.min().date())
                train_stuff['train_maxs'].append(x.iloc[train_index].index.max().date())
                train_stuff['test_mins'].append(x.iloc[test_index].index.min().date() + pd.Timedelta(days = 1))
                train_stuff['test_maxs'].append(x.iloc[test_index].index.max().date())
                
                x_train, x_test = x.iloc[train_index], x.iloc[test_index]
                y_train, y_test = y.iloc[train_index], y.iloc[test_index]
                
                print(len(x_train), len(x_test))
                
                grid_search.fit(x_train, y_train)    
                train_stuff['gridsearch_objs'].append(grid_search)
                y_pred_test = grid_search.predict(x_test)
                y_pred_train = grid_search.predict(x_train)
                
                print(grid_search.best_params_)
                print('--- train ---')
                print(classification_report(y_train, y_pred_train))
                print('--- test ---')
                print(classification_report(y_test, y_pred_test))
                print(100*'-')
            
            logger.info(f"Dumping train stuff - periods and models")
            with open(f"../outputs_hhhl_ml1/{symbol}/train_stuff.pickle", 'wb') as f:
                pickle.dump(train_stuff, f)
            logger.info(f"XXXXXXXXXXXXXXXXXXXXXXXXXX - symbol {symbol} DONE - XXXXXXXXXXXXXXXXXXXXXXXXXX")
    logger.info(f"XXXXXXXXXXXXXXXXXXXXXXXXXX - ALL YMBOLS DONE - XXXXXXXXXXXXXXXXXXXXXXXXXX")

if __name__ == '__main__':
    main()