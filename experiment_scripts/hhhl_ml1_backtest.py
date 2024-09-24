
#%% load pacakes

import pandas as pd
import sys
import os
import pickle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.strategies import hhhl_ml1_strategy_logic, HigherHighStrategyML1
import pdb
import vectorbt as vbt

#%% load data
df_price = pd.read_csv('../data/df_price_aapl.csv', index_col='Date', parse_dates = ['Date'])
with open('../data/hhhl_ml_df5_train_stuff.pickle', 'rb') as f:
    train_stuff = pickle.load(f)
    
datasets_train = []
datasets_test = []

for i in range(0, len(train_stuff['train_mins'])):
    datasets_train.append(df_price.loc[train_stuff['train_mins'][i]:train_stuff['train_maxs'][i]])
    datasets_test.append(df_price.loc[train_stuff['test_mins'][i]:train_stuff['test_maxs'][i]])
params = {'window_entry': [2, 9],
      'hh_hl_counts': [1, 5],
      'window_exit': [2, 9],
      'lh_counts': [1, 5]}

#%% backtest loop

stats_all = []
for i in range(0, len(train_stuff['train_mins'])):
    
    df_true_entry_signals_train, df_true_exit_signals_train = hhhl_ml1_strategy_logic([datasets_train[i]],
                                                    [train_stuff['gridsearch_objs'][i]],
                                                    params,
                                                    0.5)
    df_true_entry_signals_test, df_true_exit_signals_test = hhhl_ml1_strategy_logic([datasets_test[i]],
                                                        [train_stuff['gridsearch_objs'][i]],
                                                        params,
                                                        0.5)

    pf_train = vbt.Portfolio.from_signals(datasets_train[i]['Adj Close'], 
                                    df_true_entry_signals_train, 
                                    df_true_exit_signals_train,
                                    price = datasets_train[i]['Open'].shift(-1),
                                    fees=0.001, 
                                    slippage=0.0001,
                                    direction = 'longonly', 
                                    freq='1D')
    stats_train = pf_train.stats(agg_func = None).T
    stats_train.columns = [f"{i}_train"]

    pf_test = vbt.Portfolio.from_signals(datasets_test[i]['Adj Close'], 
                                    df_true_entry_signals_test, 
                                    df_true_exit_signals_test,
                                    price = datasets_test[i]['Open'].shift(-1),
                                    fees=0.001, 
                                    slippage=0.0001,
                                    direction = 'longonly', 
                                    freq='1D')
    stats_test  = pf_test.stats(agg_func = None).T
    stats_test.columns = [f"{i}_test"]
    
    stats_all.append(stats_train)
    stats_all.append(stats_test)
df_stats = pd.concat(stats_all, axis = 1)
df_stats.to_csv('df_stats_aapl.csv', index = True, header = True)

#TODO
# spravna metrika na modely
# liftcharty
# probability threshold ako param (ked zvysim, zvysi sa mi win rate strategie?)
# entry exit signaly obchodu musia byt rovnake ako v orig. strategii !!!
# zanalyzovat obchody na train a test periodach strategie:
#   uspesny obchod vs. probability, liftcharty
#   trvanie obchodu vs. win rate
# v backteste test perioda premenliva, podla toho ci potrebujem retrenovat model - ako?
# scripty:
#   data prep
#   trening + mlflow
#   backtest
#   eval
