
#%% load pacakes

import pandas as pd
import sys
import os
import pickle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.strategies import hhhl_ml1_strategy_logic
import pdb
import vectorbt as vbt
import plotly.io as pio

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
    train_result = hhhl_ml1_strategy_logic(datasets_train[i],
                                                    train_stuff['gridsearch_objs'][i],
                                                    params,
                                                    0.5)
    true_entry_signals_train = train_result[0]
    true_exit_signals_train = train_result[1]
    max_combs_all_train = train_result[2]
    max_probs_all_train = train_result[3]
    
    test_result = hhhl_ml1_strategy_logic(datasets_test[i],
                                                        train_stuff['gridsearch_objs'][i],
                                                        params,
                                                        0.5)
    true_entry_signals_test = test_result[0]
    true_exit_signals_test = test_result[1]
    max_combs_all_test = test_result[2]
    max_probs_all_test = test_result[3]

    pf_train = vbt.Portfolio.from_signals(datasets_train[i]['Adj Close'], 
                                    true_entry_signals_train, 
                                    true_exit_signals_train,
                                    price = datasets_train[i]['Open'].shift(-1),
                                    #fees=0.001, 
                                    #slippage=0.0001,
                                    direction = 'longonly', 
                                    freq='1D',
                                    sl_stop=0.1)
    stats_train = pf_train.stats(agg_func = None).T
    stats_train.columns = [f"{i}_train"]

    pf_test = vbt.Portfolio.from_signals(datasets_test[i]['Adj Close'], 
                                    true_entry_signals_test, 
                                    true_exit_signals_test,
                                    price = datasets_test[i]['Open'].shift(-1),
                                    #fees=0.001, 
                                    #slippage=0.0001,
                                    direction = 'longonly', 
                                    freq='1D',
                                    sl_stop = 0.1)
    stats_test  = pf_test.stats(agg_func = None).T
    stats_test.columns = [f"{i}_test"]
    
    stats_all.append(stats_train)
    stats_all.append(stats_test)
    
    df_info_train = pd.concat([true_entry_signals_train, true_exit_signals_train,
                               max_combs_all_train, max_probs_all_train])
    df_info_test = pd.concat([true_entry_signals_test, true_exit_signals_test,
                               max_combs_all_test, max_probs_all_test])
    
    pf_train.trades.records_readable.to_csv(f"debug/train_{i}_trades.csv", index = True, header = True)
    df_info_train.to_csv(f"debug/df_info_train_{i}.csv", index = True, header = True)
    pf_test.trades.records_readable.to_csv(f"debug/test_{i}_trades.csv", index = True, header = True)
    df_info_test.to_csv(f"debug/df_info_test_{i}.csv", index = True, header = True)
 
    fig = pf_train.plot()
    fig.update_layout(title=f"train_{i}_stats")
    pio.write_html(fig, file = f"debug/train_{i}_stats.html")
    fig.write_image(f"debug/train_{i}_stats.png")
    pdb.set_trace()
    fig = pf_test.plot()
    fig.update_layout(title=f"test_{i}_stats")
    pio.write_html(fig, file = f"debug/test_{i}_stats.html")
    fig.write_image(f"debug/test_{i}_stats.png")
    
df_stats = pd.concat(stats_all, axis = 1)
#pdb.set_trace()
df_stats.to_csv('debug/df_stats_aapl.csv', index = True, header = True)

#TODO
# spravna metrika na modely
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
