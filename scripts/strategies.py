import pandas as pd
import numpy as np
import vectorbt as vbt
import itertools

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

def hhhl_ml1_strategy_logic(datasets:list, models:list, dataset_params:dict, 
                           probability_threshold:float):
    true_entry_signals = []
    true_exit_signals = []
    #pdb.set_trace()
    for i, dataset in enumerate(datasets):
        model = models[i]
        close = dataset['Adj Close']
        expanded_params = {key: list(range(val[0], val[1] + 1)) for key, val in dataset_params.items()}
        combinations = list(itertools.product(*expanded_params.values()))
        #combinations_as_dicts = [dict(zip(expanded_params.keys(), combo)) for combo in combinations]
        df_entry_signals = pd.DataFrame(index = close.index)
        df_exit_signals = pd.DataFrame(index = close.index)
        df_probs = pd.DataFrame(index = close.index)
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
            df_entry_signals[comb] = entry_signal # df entry signalov, s nazvami stlpcov ako napr. (6,1,2,1)
            
            # probability predictions
            
            x = dataset.copy()
            x['window_entry'] = comb[0]
            x['hh_hl_counts'] = comb[1]
            x['window_exit'] = comb[2]
            x['lh_counts'] = comb[3] # dataset ready
            predicted_proba = model.predict_proba(x)
            df_probs[comb] = predicted_proba # df predikovanych probabilit
            
            # exit signals - original strategy
                                
            lower_highs = close < close.rolling(window=comb[2], min_periods=1).max().shift(1)
            lh_count = lower_highs.rolling(window=comb[2]).sum()
            exit_signal = (lh_count >= comb[3]) & lower_highs
            df_exit_signals[comb] = exit_signal # df exit signalov
            
            
        df_probs_masked = df_probs.where(df_entry_signals)
        max_combs = df_probs_masked.idxmax(axis=1) # series s param kombinaciami kde bolo max prob
        max_probs = df_probs_masked.max(axis=1)# series s max prob
        true_entry_signal = max_probs >= probability_threshold
        
        open_trade = False
        for i, entry in true_entry_signal.tolist():
            if open_trade:
                exit_comb = df_exit_signals[params]
                is_exit_signal = exit_comb[i]
                if is_exit_signal:
                    true_entry_signal[i] = False
                    open_trade = False
                else:
                    true_entry_signal[i] = True
            else:
                if entry:
                    open_trade = True
                    params = max_combs[i]
                    
        true_exit_signal = not true_entry_signal
        true_exit_signals.append(true_exit_signal)
        true_entry_signals.append(true_entry_signal)
    df_true_entry_signals = pd.concat(true_entry_signals, axis = 1)
    df_true_exit_signals = pd.concat(true_exit_signals, axis = 1)

    return df_true_entry_signals, df_true_exit_signals # musia byt dfs

# Create a custom indicator using the IndicatorFactory
HigherHighStrategyML1 = vbt.IndicatorFactory(
    input_names=['datasets', 'models', 'dataset_params'],
    param_names=['probability_threshold'],
    output_names = ['entry_signal', 'exit_signal']
).from_apply_func(hhhl_ml1_strategy_logic)