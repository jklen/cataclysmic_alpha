import pandas as pd
import numpy as np
import vectorbt as vbt
import itertools
import pdb

# HigherHigh strategy

def hh_hl_strategy_logic(close, window_entry, hh_hl_counts, 
                   window_exit, lh_counts):
    #pdb.set_trace()
    if isinstance(close, np.ndarray):
        close = pd.DataFrame(close)
        
    if (hh_hl_counts > window_entry) or (lh_counts > window_exit):
        df_empty = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
        return df_empty, df_empty
    
    higher_highs = close > close.rolling(window=window_entry, min_periods=window_entry).max().shift(1)
    higher_lows = close > close.rolling(window=window_entry, min_periods=window_entry).min().shift(1)

    hh_count = higher_highs.rolling(window=window_entry).sum() # asi -1, lebo prenasa True z higher_highs z predosleho okna
    hl_count = higher_lows.rolling(window=window_entry).sum() # asi -1, lebo prenasa True z higher_lows z predosleho okna

    entry_signal = (hl_count.shift(1) >= hh_hl_counts) & (hh_count.shift(1) >= hh_hl_counts) & higher_lows

    lower_highs = close < close.rolling(window=window_exit, min_periods=1).max().shift(1)
    lh_count = lower_highs.rolling(window=window_exit).sum()
    exit_signal = (lh_count >= lh_counts) & lower_highs

    return entry_signal, exit_signal

HigherHighStrategy = vbt.IndicatorFactory(
    input_names=['close'],
    param_names=['window_entry', 'hh_hl_counts',
                 'window_exit', 'lh_counts'],
    output_names=['entry_signal', 'exit_signal']
).from_apply_func(hh_hl_strategy_logic)

# HigherHigh ML strategy 1

def hhhl_ml1_strategy_logic(dataset, model, dataset_params:dict, 
                           probability_threshold:float):
    
    close = dataset['Adj Close']
    expanded_params = {key: list(range(val[0], val[1] + 1)) for key, val in dataset_params.items()}
    combinations = list(itertools.product(*expanded_params.values()))
    entry_signals_list = []
    exit_signals_list = []
    probs_list = []
    print(f"starting processing param combinations")
    for comb in combinations:
        
        # entry signals - original strategy
        
        higher_highs = close > close.rolling(window=comb[0], 
                                            min_periods=comb[0]).max().shift(1)
        higher_lows = close > close.rolling(window=comb[0], 
                                            min_periods=comb[0]).min().shift(1)

        hh_count = higher_highs.rolling(window=comb[0]).sum() # asi -1, lebo prenasa True z higher_highs z predosleho okna
        hl_count = higher_lows.rolling(window=comb[0]).sum() # asi -1, lebo prenasa True z higher_lows z predosleho okna

        entry_signal = (hl_count.shift(1) >= comb[1]) & \
                (hh_count.shift(1) >= comb[1]) & higher_lows
        entry_signal.name = comb
        entry_signals_list.append(entry_signal)
        
        # probability predictions
        
        x = dataset.copy()
        x['window_entry'] = comb[0]
        x['hh_hl_counts'] = comb[1]
        x['window_exit'] = comb[2]
        x['lh_counts'] = comb[3] # dataset ready
        predicted_proba = model.predict_proba(x)[:,1] # len True classa
        probs_list.append(pd.Series(predicted_proba, name = comb, index = close.index))
        
        # exit signals - original strategy
                            
        lower_highs = close < close.rolling(window=comb[2], min_periods=1).max().shift(1)
        lh_count = lower_highs.rolling(window=comb[2]).sum()
        exit_signal = (lh_count >= comb[3]) & lower_highs
        exit_signal.name = comb
        exit_signals_list.append(exit_signal)
    
    print("param combinations finished")
    
    df_probs = pd.concat(probs_list, axis = 1) # df s probabilities pre kazdu param comb, eg (6,1,2,1) ako colname
    df_entry_signals = pd.concat(entry_signals_list, axis = 1) # df s entry signalmi
    df_exit_signals = pd.concat(exit_signals_list, axis = 1) # df s exit signalmi

    df_probs_masked = df_probs.where(df_entry_signals)
    max_combs = df_probs_masked.idxmax(axis=1) # series s param kombinaciami kde bolo max prob
    max_probs = df_probs_masked.max(axis=1)# series s max prob
    true_entry_signal = max_probs >= probability_threshold
    print("calculating final entry and exit signals")
    #pdb.set_trace()
    open_trade = False
    for i, entry in enumerate(true_entry_signal.tolist()):
        if open_trade:
            is_exit_signal = df_exit_signals[params][i]
            if is_exit_signal: # when closing trade, only exit signal must be True
                true_entry_signal[i] = False
                open_trade = False
            else:
                true_entry_signal[i] = True
        else:
            if entry: # when opening trade, entry signal must be True and exit signal must be False (default vbt setting)
                params = max_combs[i]
                if df_exit_signals[params][i] == False:
                    open_trade = True
    true_exit_signal = ~true_entry_signal
    
    true_entry_signal.name = 'entry_signal'
    true_exit_signal.name = 'exit_signal'
    max_combs.name = 'max_combs'
    max_probs.name = 'max_probs'

    return true_entry_signal, true_exit_signal, max_combs, max_probs
