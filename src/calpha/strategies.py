import pandas as pd
import numpy as np
import vectorbt as vbt
import itertools


def hh_hl_strategy_logic(close, window_entry, hh_hl_counts,
                         window_exit, lh_counts):
    """Core signal logic for the Higher High / Higher Low (HHHL) strategy.

    Entry: price has made at least `hh_hl_counts` higher highs AND higher lows
    within the last `window_entry` bars.
    Exit: price has made at least `lh_counts` lower highs within the last
    `window_exit` bars.

    Args:
        close: Series or ndarray of closing prices.
        window_entry: Lookback window (bars) for detecting higher highs/lows on entry.
        hh_hl_counts: Minimum number of higher highs and higher lows required to trigger entry.
        window_exit: Lookback window (bars) for detecting lower highs on exit.
        lh_counts: Minimum number of lower highs required to trigger exit.

    Returns:
        Tuple of (entry_signal, exit_signal) as boolean DataFrames/Series.
        Returns a pair of NaN DataFrames when parameters are logically invalid
        (e.g. hh_hl_counts > window_entry).
    """
    if isinstance(close, np.ndarray):
        close = pd.DataFrame(close)

    if (hh_hl_counts > window_entry) or (lh_counts > window_exit):
        df_empty = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
        return df_empty, df_empty

    higher_highs = close > close.rolling(window=window_entry, min_periods=window_entry).max().shift(1)
    higher_lows = close > close.rolling(window=window_entry, min_periods=window_entry).min().shift(1)

    # Rolling sums carry forward True values from the previous window, so the
    # shift(1) on the count is intentional — we check the prior bar's count.
    hh_count = higher_highs.rolling(window=window_entry).sum()
    hl_count = higher_lows.rolling(window=window_entry).sum()

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


def hhhl_ml1_strategy_logic(dataset, model, dataset_params: dict,
                            probability_threshold: float):
    """ML-enhanced HHHL signal logic (HHHL ML1).

    For each bar, evaluates all valid HHHL parameter combinations. The trained
    ML model predicts the win probability for each combination. On bars where
    the HHHL entry condition fires, the combination with the highest predicted
    probability is selected. An entry signal is generated only when that
    probability exceeds `probability_threshold`.

    The function also enforces trade state: once a trade is open, the same
    parameter combination's exit signal is tracked until it fires, preventing
    overlapping trades.

    Args:
        dataset: DataFrame with columns including 'close' and all technical
            indicator features used during model training.
        model: Trained scikit-learn classifier with a predict_proba method.
        dataset_params: Dict mapping each HHHL parameter name to a [min, max]
            range, e.g. {'window_entry': [2, 9], 'hh_hl_counts': [1, 5], ...}.
        probability_threshold: Minimum win probability required to open a trade.

    Returns:
        Tuple of (true_entry_signal, true_exit_signal, max_combs, max_probs):
            - true_entry_signal: Boolean Series, True on entry bars.
            - true_exit_signal: Boolean Series, True on exit bars.
            - max_combs: Series of the winning parameter tuple selected on each bar.
            - max_probs: Series of the highest win probability on each entry bar.
    """
    close = dataset['close']
    expanded_params = {key: list(range(val[0], val[1] + 1)) for key, val in dataset_params.items()}
    combinations = list(itertools.product(*expanded_params.values()))
    entry_signals_list = []
    exit_signals_list = []
    probs_list = []

    print("starting processing param combinations")
    for comb in combinations:
        # Skip invalid combinations where count requirements exceed window size
        if (comb[1] > comb[0]) or (comb[3] > comb[2]):
            continue

        higher_highs = close > close.rolling(window=comb[0], min_periods=comb[0]).max().shift(1)
        higher_lows = close > close.rolling(window=comb[0], min_periods=comb[0]).min().shift(1)

        hh_count = higher_highs.rolling(window=comb[0]).sum()
        hl_count = higher_lows.rolling(window=comb[0]).sum()

        entry_signal = (hl_count.shift(1) >= comb[1]) & \
                       (hh_count.shift(1) >= comb[1]) & higher_lows
        entry_signal.name = comb
        entry_signals_list.append(entry_signal)

        x = dataset.copy()
        x['window_entry'] = comb[0]
        x['hh_hl_counts'] = comb[1]
        x['window_exit'] = comb[2]
        x['lh_counts'] = comb[3]
        predicted_proba = model.predict_proba(x)[:, 1]  # probability of the positive (win) class
        probs_list.append(pd.Series(predicted_proba, name=comb, index=close.index))

        lower_highs = close < close.rolling(window=comb[2], min_periods=1).max().shift(1)
        lh_count = lower_highs.rolling(window=comb[2]).sum()
        exit_signal = (lh_count >= comb[3]) & lower_highs
        exit_signal.name = comb
        exit_signals_list.append(exit_signal)

    print("param combinations finished")

    df_probs = pd.concat(probs_list, axis=1)
    df_entry_signals = pd.concat(entry_signals_list, axis=1)
    df_exit_signals = pd.concat(exit_signals_list, axis=1)

    df_probs_masked = df_probs.where(df_entry_signals)
    max_combs = df_probs_masked.idxmax(axis=1)
    max_probs = df_probs_masked.max(axis=1)
    true_entry_signal = max_probs >= probability_threshold

    print("calculating final entry and exit signals")

    # Walk forward through time enforcing single-trade state: once a trade is
    # open, hold until the exit signal for the selected parameter combo fires.
    open_trade = False
    for i, entry in enumerate(true_entry_signal.tolist()):
        if open_trade:
            is_exit_signal = df_exit_signals[params][i]
            if is_exit_signal:
                true_entry_signal[i] = False
                open_trade = False
            else:
                true_entry_signal[i] = True
        else:
            if entry:
                params = max_combs[i]
                if df_exit_signals[params][i] == False:
                    open_trade = True

    true_exit_signal = ~true_entry_signal

    true_entry_signal.name = 'entry_signal'
    true_exit_signal.name = 'exit_signal'
    max_combs.name = 'max_combs'
    max_probs.name = 'max_probs'

    return true_entry_signal, true_exit_signal, max_combs, max_probs
