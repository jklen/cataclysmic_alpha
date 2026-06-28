from calpha import ROOT_DIR
from calpha.strategies import HigherHighStrategy, hhhl_ml1_strategy_logic
from calpha.utils_strategy import data_load
import pandas as pd
import pandas_ta as ta
import numpy as np
import yaml
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import OrderRequest, GetOrdersRequest, GetOrderByIdRequest
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest, StockLatestTradeRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from datetime import datetime, timedelta
import vectorbt as vbt
import uuid
import sqlite3
import ast
import logging
import quantstats as qs
import requests
import os

logger = logging.getLogger(__name__)

keys = yaml.safe_load(open(ROOT_DIR / 'keys.yaml', 'r'))

strategies_directions = {
    'hhhl': 'long',
    'hhhl_ml1': 'long'
}

model_strategies = ['hhhl_ml1']

crypto_map = {'BTC/USD': 'BTCUSD', 'LINK/BTC': 'LINKBTC'}


def review_positions():
    """Placeholder for future position review logic."""
    pass


def create_trading_client():
    """Create and return an Alpaca paper trading client.

    Returns:
        TradingClient configured for Alpaca paper trading.
    """
    return TradingClient(keys['paper_key'], keys['paper_secret'], paper=True)


def closed_trades_cnt(symbols):
    """Count the number of completed round-trip trades for each symbol.

    A trade is counted as one BUY followed by a SELL of the same quantity
    (long-only assumption). Orders are fetched from Alpaca.

    Args:
        symbols: List of ticker symbols (using yfinance/config format, e.g. 'BTC/USD').

    Returns:
        Series indexed by symbol with integer closed trade counts.
    """
    logger.info("Calculating closed trades count")
    trading_client = create_trading_client()
    closed_trades = {}
    for symbol in symbols:
        request_params = GetOrdersRequest(status='closed', symbols=[symbol])
        orders = trading_client.get_orders(filter=request_params)
        orders_dicts = map(dict, orders)
        keys_to_keep = ['symbol', 'filled_at', 'filled_qty', 'side']
        filtered_orders = [{key: value for key, value in d.items() if key in keys_to_keep} for d in orders_dicts]

        if len(filtered_orders) >= 2:
            df_orders = pd.DataFrame(filtered_orders)
            df_orders['side'] = df_orders['side'].apply(str)
            df_orders.sort_values(by='filled_at', inplace=True)
            df_orders[['filled_qty_lag', 'side_lag']] = df_orders[['filled_qty', 'side']].shift(1)

            df_trades = df_orders.loc[
                (df_orders['side'] == 'OrderSide.SELL') &
                (df_orders['side_lag'] == 'OrderSide.BUY') &
                (df_orders['filled_qty'] == df_orders['filled_qty_lag']), :
            ]
            closed_trades[symbol] = len(df_trades)
        else:
            closed_trades[symbol] = 0

    return pd.Series(closed_trades, name='closed_trades_cnt')


def if_running_weights(symbols, weights_params):
    """Check whether enough symbols have sufficient trade history for win-rate weighting.

    Args:
        symbols: List of ticker symbols.
        weights_params: Dict with keys 'running' (weighting method) and
            'running_params' (dict with 'min_trades' and 'min_symbols').

    Returns:
        True if the minimum number of symbols meet the minimum trade count
        threshold, False otherwise.
    """
    if weights_params['running'] == 'win_rate':
        s_closed_trades_cnt = closed_trades_cnt(symbols)
        symbols_meeting_min_trades_cnt = (s_closed_trades_cnt >= weights_params['running_params']['min_trades']).sum()
        return symbols_meeting_min_trades_cnt >= weights_params['running_params']['min_symbols']


def calculate_win_rates(symbols):
    """Compute the win rate for each symbol based on closed Alpaca orders.

    A trade is counted as a win when (sell P&L) > 0. Only long trades
    (BUY followed by matching SELL) are considered.

    Args:
        symbols: List of ticker symbols.

    Returns:
        Series indexed by symbol with win rate values in [0, 1].
    """
    logger.info("Calculating win rates")
    trading_client = create_trading_client()
    win_rates = {}
    for symbol in symbols:
        logger.info(f'Processing symbol - {symbol}')
        request_params = GetOrdersRequest(status='closed', symbols=[symbol])
        orders = trading_client.get_orders(filter=request_params)
        orders_dicts = map(dict, orders)
        keys_to_keep = ['symbol', 'filled_at', 'filled_qty', 'filled_avg_price', 'side']
        filtered_orders = [{key: value for key, value in d.items() if key in keys_to_keep} for d in orders_dicts]
        df_orders = pd.DataFrame(filtered_orders)
        df_orders.loc[:, ['filled_qty', 'filled_avg_price']] = df_orders.loc[:, ['filled_qty', 'filled_avg_price']].astype('float')
        df_orders['filled_qty'] = df_orders['filled_qty'].round(3)
        df_orders['side'] = df_orders['side'].apply(str)
        df_orders.sort_values(by='filled_at', inplace=True)
        df_orders[['filled_qty_lag', 'side_lag', 'filled_avg_price_lag']] = df_orders[['filled_qty', 'side', 'filled_avg_price']].shift(1)

        df_trades = df_orders.loc[
            (df_orders['side'] == 'OrderSide.SELL') &
            (df_orders['side_lag'] == 'OrderSide.BUY') &
            (df_orders['filled_qty'] == df_orders['filled_qty_lag']), :
        ]
        df_trades.loc[:, ['filled_qty', 'filled_avg_price', 'filled_avg_price_lag']] = \
            df_trades.loc[:, ['filled_qty', 'filled_avg_price', 'filled_avg_price_lag']].astype('Float32')
        df_trades['pl'] = (df_trades['filled_qty'] * df_trades['filled_avg_price']) - \
                          (df_trades['filled_qty'] * df_trades['filled_avg_price_lag'])
        wins_cnt = (df_trades['pl'] > 0).sum()
        losses_cnt = (df_trades['pl'] < 0).sum()
        win_rates[symbol] = wins_cnt / (wins_cnt + losses_cnt)

    return pd.Series(win_rates, name='win_rate')


def calculate_weights(series_metric, running_params):
    """Compute portfolio weights proportional to win rate, with a minimum floor.

    Symbols below `min_trades` receive a fixed `min_weight`. The remaining
    weight budget is distributed among qualifying symbols in proportion to
    their win rate. Any qualifying symbol whose computed weight falls below
    `min_weight` is also clipped and the excess redistributed.

    Args:
        series_metric: Series of win rates indexed by symbol (name='win_rate').
        running_params: Dict with keys 'min_trades', 'min_weight'.

    Returns:
        Dict mapping symbol → portfolio weight (floats summing to ~1).
    """
    if series_metric.name == 'win_rate':
        closed_trades = closed_trades_cnt(series_metric.index.tolist())
        df = series_metric.to_frame()
        df = df.join(closed_trades.to_frame())

        mask_symbols_to_weight = df['closed_trades_cnt'] >= running_params['min_trades']
        symbols_with_min_weight_cnt = len(df) - mask_symbols_to_weight.sum()
        df['weight'] = running_params['min_weight']
        df.loc[mask_symbols_to_weight, 'weight'] = \
            df.loc[mask_symbols_to_weight, 'win_rate'] / df.loc[mask_symbols_to_weight, 'win_rate'].sum()
        df.loc[mask_symbols_to_weight, 'weight'] = \
            (1 - symbols_with_min_weight_cnt * running_params['min_weight']) * df.loc[mask_symbols_to_weight, 'weight']

        to_min_weight_mask = df['weight'] < running_params['min_weight']
        df.loc[to_min_weight_mask, 'weight'] = running_params['min_weight']
        calc = (1 - (df['weight'] == running_params['min_weight']).sum() * running_params['min_weight']) / \
               (df.loc[df['weight'] > running_params['min_weight'], 'weight']).sum()
        df.loc[df['weight'] > running_params['min_weight'], 'weight'] = \
            df.loc[df['weight'] > running_params['min_weight'], 'weight'] * calc

        return df['weight'].to_dict()


def check_weights(symbols, weights_params):
    """Return the current portfolio weights for all symbols.

    Uses equal weights when both initial and running modes are 'equal'.
    Otherwise falls back to win-rate weighting if enough trade history
    exists, or equal weights if it does not.

    Args:
        symbols: Iterable of ticker symbols.
        weights_params: Dict with keys 'initial', 'running', and optionally
            'running_params'.

    Returns:
        Dict mapping symbol → weight (floats summing to 1).
    """
    logger.info("Calculating symbols weights")

    if (weights_params['initial'] == 'equal') & (weights_params['running'] == 'equal'):
        one_symbol_weight = 1. / len(symbols)
        return {symbol: one_symbol_weight for symbol in symbols}
    else:
        if if_running_weights(symbols, weights_params):
            if weights_params['running'] == 'win_rate':
                series_metric = calculate_win_rates(symbols)
                print(series_metric)
            weights = calculate_weights(series_metric, weights_params['running_params'])
            return weights
        else:
            if weights_params['initial'] == 'equal':
                one_symbol_weight = 1. / len(symbols)
                return {symbol: one_symbol_weight for symbol in symbols}


def run_strategy(df_symbol, symbol, strategy, strategy_params, **kwargs):
    """Generate entry and exit signals for a symbol using the configured strategy.

    Args:
        df_symbol: DataFrame of OHLCV data plus technical indicators for the symbol.
        symbol: Ticker symbol (used for logging).
        strategy: Strategy name, one of 'hhhl' or 'hhhl_ml1'.
        strategy_params: Dict of strategy parameters (e.g. window sizes, thresholds).
        **kwargs: Additional keyword arguments required by ML strategies:
            - strategy_setup: Dict with 'param_ranges' for HHHL ML1.
            - models: Dict with 'open_trade' containing the trained model object.

    Returns:
        Tuple of (entries, exits) as boolean Series.
    """
    logger.info(f"{symbol} - running symbol's strategy to get entries and exits")
    if strategy == 'hhhl':
        Strategy = HigherHighStrategy
    elif strategy == 'hhhl_ml1':
        param_ranges = kwargs['strategy_setup']['param_ranges']
        model_obj = kwargs['models']['open_trade']
        entries, exits, _, _ = hhhl_ml1_strategy_logic(df_symbol,
                                                        model_obj,
                                                        param_ranges,
                                                        strategy_params['probability_threshold'])
        return entries, exits

    close_price = df_symbol['close']
    indicator = Strategy.run(close_price, **strategy_params)
    entries = indicator.entry_signal
    exits = indicator.exit_signal
    return entries, exits


def is_trading_day(day):
    """Check whether a given date is a US stock market trading day.

    Checks for weekends and a hardcoded list of US market holidays.
    Note: Alpaca's trading calendar API could be used here for more accuracy.
    Reference: https://www.investopedia.com/ask/answers/06/stockexchangeclosed.asp

    Args:
        day: datetime.date object to check.

    Returns:
        True if the market is open on that day, False otherwise.
    """
    us_stock_market_holidays = [
        datetime(2025, 1, 9), datetime(2025, 1, 1), datetime(2025, 1, 20),
        datetime(2025, 1, 19),
        datetime(2024, 3, 29), datetime(2024, 5, 27), datetime(2024, 6, 19),
        datetime(2024, 7, 4), datetime(2024, 9, 2), datetime(2024, 11, 28),
        datetime(2024, 12, 25)
    ]
    us_stock_market_holidays = map(lambda x: x.date(), us_stock_market_holidays)

    if (day.weekday() in range(0, 5)) and (day not in us_stock_market_holidays):
        return True
    return False


def correct_date(symbol, last_day):
    """Check whether the most recent bar in the data matches today's expected last trading day.

    Crypto markets run 24/7, so the expected last bar is always yesterday.
    For stocks, the check accounts for weekends and holidays (up to 4 days back).

    Args:
        symbol: Ticker symbol. Crypto symbols are looked up in `crypto_map`.
        last_day: datetime.date of the last available bar in the symbol's data.

    Returns:
        True if `last_day` equals the expected last trading date, False otherwise.
        Returns False when the script is run on a non-trading day (stocks only).
    """
    logger.info("Checking if we have correct date")
    todays_date = datetime.today().date()

    if symbol in crypto_map.keys():
        return last_day == (todays_date - timedelta(days=1))

    today = is_trading_day(todays_date)
    today_1 = is_trading_day(todays_date - timedelta(days=1))
    today_2 = is_trading_day(todays_date - timedelta(days=2))
    today_3 = is_trading_day(todays_date - timedelta(days=3))

    if today:
        if today_1:
            return last_day == (todays_date - timedelta(days=1))
        elif not today_1 and today_2:
            return last_day == (todays_date - timedelta(days=2))
        elif not today_1 and not today_2 and today_3:
            return last_day == (todays_date - timedelta(days=3))
        elif not today_1 and not today_2 and not today_3:
            return last_day == (todays_date - timedelta(days=4))
    else:
        # Script runs on non-trading days are skipped for regular stocks;
        # crypto is handled separately above.
        return False


def eval_position(close_price, entries, exits, strategy_direction, stoploss, take_profit):
    """Determine whether to open, close, or hold a position based on today's signals.

    Runs a VectorBT portfolio simulation on the full price history to find
    the last signal date, then compares it to today's date.

    Args:
        close_price: Series of close prices.
        entries: Boolean Series of entry signals.
        exits: Boolean Series of exit signals.
        strategy_direction: 'long', 'short', or 'long_and_short'.
        stoploss: Stop-loss fraction (e.g. 0.1 for 10%).
        take_profit: Take-profit fraction, or None to disable.

    Returns:
        'open' if today is an entry date, 'close' if today is an exit date
        (and the trade is marked Closed), or 'no_change' otherwise.
    """
    logger.info("Evaluating symbol: open, close, or no change")
    if strategy_direction == 'long':
        pf = vbt.Portfolio.from_signals(close_price,
                                        entries,
                                        exits,
                                        sl_stop=stoploss,
                                        tp_stop=take_profit,
                                        direction='longonly',
                                        freq='1D')
        df_trades = pf.trades.records_readable
        last_date = close_price.tail(1).index[0].date()

        if last_date in list(df_trades['Entry Timestamp'].apply(lambda x: x.date())):
            return 'open'
        elif (last_date in list(df_trades['Exit Timestamp'].apply(lambda x: x.date()))) and \
                (df_trades['Status'].iloc[-1] == 'Closed'):
            return 'close'
        else:
            return 'no_change'

    elif strategy_direction == 'short':
        pass
    elif strategy_direction == 'long_and_short':
        pass


def close_positions(trades):
    """Submit close orders for all symbols marked as 'close' in the trades dict.

    Args:
        trades: Dict mapping symbol → action string. Only symbols with
            action == 'close' are processed.
    """
    logger.info("Submitting orders to close existing positions")
    trading_client = create_trading_client()
    for symbol in trades.keys():
        if trades[symbol] == 'close':
            try:
                trading_client.close_position(symbol)
            except Exception:
                logger.warning(f"{symbol} - trying to close non-existing position")


def position_sizes(portfolio, min_avail_cash, weights, run_id, timestamp):
    """Calculate dollar position sizes for symbols due to be opened.

    Reads current portfolio state from the DB to determine available cash.
    If available cash is below `min_avail_cash`, the portfolio size is
    temporarily increased to ensure the minimum is met. Position sizes are
    scaled down proportionally when total new positions exceed available cash.

    Persists the computed sizes to the `positions` table in the DB.

    Args:
        portfolio: Portfolio name string.
        min_avail_cash: Minimum cash to maintain after opening positions.
        weights: Dict mapping symbol → portfolio weight fraction.
        run_id: Unique run identifier string.
        timestamp: datetime of the current run.

    Returns:
        Series indexed by symbol with dollar position sizes (rounded to 2 dp).
    """
    logger.info(f"Portfolio {portfolio} - calculating position sizes")
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))
    df_portfolio = pd.read_sql(f"""SELECT * FROM portfolio_state WHERE portfolio_script_run_id = '{run_id}' AND
                     portfolio_name = '{portfolio}'""", con)
    open_symbols = ast.literal_eval(df_portfolio['open_trades_symbols'][0])

    available_cash = max(df_portfolio['available_cash'][0], min_avail_cash)
    if df_portfolio['available_cash'][0] < min_avail_cash:
        logger.warning('Increasing the portfolio size because available cash is below the minimum')
        portfolio_size = df_portfolio['portfolio_size'][0] + min_avail_cash - df_portfolio['available_cash'][0]
    else:
        portfolio_size = df_portfolio['portfolio_size'][0]

    df = pd.Series(weights, name='weight').to_frame()
    df.index = df.index.map(lambda x: crypto_map[x] if x in crypto_map else x)
    df['is_open'] = 'N'
    df.loc[open_symbols, 'is_open'] = 'Y'
    df['base'] = portfolio_size + df_portfolio['closed_trades_PL'][0]
    df['available_cash'] = available_cash
    df['position'] = df['weight'] * df['base']

    if df.loc[df['is_open'] == 'N', 'position'].sum() > available_cash:
        coef = available_cash / df.loc[df['is_open'] == 'N', 'position'].sum()
        df.loc[df['is_open'] == 'N', 'position'] = df.loc[df['is_open'] == 'N', 'position'] * coef

    df['portfolio_name'] = portfolio
    df['portfolio_script_run_id'] = run_id
    df['min_available_cash'] = min_avail_cash
    df['portfolio_size'] = portfolio_size
    df['timestamp'] = timestamp
    df['date'] = timestamp.date()
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'symbol'}, inplace=True)
    df = df[['timestamp', 'date', 'portfolio_script_run_id', 'portfolio_name', 'symbol', 'is_open', 'weight',
             'position', 'portfolio_size', 'base', 'available_cash', 'min_available_cash']]
    df.to_sql('positions', con, if_exists='append', index=False)
    con.close()

    return df.set_index('symbol')['position'].round(2)


def open_positions(sizes, trades):
    """Submit market buy orders for all symbols marked as 'open' in the trades dict.

    Args:
        sizes: Series indexed by symbol with dollar notional amounts.
        trades: Dict mapping symbol → action string. Only symbols with
            action == 'open' are processed.
    """
    logger.info("Submitting orders to open positions")
    trading_client = create_trading_client()
    for symbol in trades.keys():
        if trades[symbol] == 'open':
            params = OrderRequest(
                symbol=symbol,
                notional=sizes[symbol],
                side='buy',
                # Crypto trades use GTC because the market is open 24/7
                time_in_force='gtc' if symbol in crypto_map.values() else 'day',
                type='market',
                order_class='simple'
            )
            trading_client.submit_order(params)


def update_portfolio_info(portfolio, config, run_id, timestamp):
    """Persist the portfolio configuration snapshot for this run to the DB.

    Writes one row per symbol into the `portfolio_info` table.

    Args:
        portfolio: Portfolio name string.
        config: Portfolio config dict (as loaded from the YAML config file).
        run_id: Unique run identifier string.
        timestamp: datetime of the current run.
    """
    logger.info(f"Updating info of portfolio - {portfolio}")
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))
    date = timestamp.date()
    weights_initial = config['weights']['initial']
    weights_running = config['weights']['running']
    try:
        running_params = str(config['weights']['running_params'])
    except Exception:
        running_params = 'not_defined'
    portfolio_size = config['portfolio_size']
    data_preference = config['data_preference']

    for symbol in config['symbols'].keys():
        strategy = list(config['symbols'][symbol].keys())[0]
        strategy_params = str(config['symbols'][symbol][strategy]['params'])
        stoploss = config['symbols'][symbol][strategy]['stoploss']
        take_profit = config['symbols'][symbol][strategy]['take_profit']
        data = (timestamp, date, run_id, portfolio, symbol,
                strategy, strategy_params, stoploss, take_profit, weights_initial, weights_running, running_params,
                portfolio_size, data_preference)
        con.execute("INSERT INTO portfolio_info VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data)
        con.commit()
    con.close()


def calculate_closed_trades_stats(symbols):
    """Compute closed-trade P&L and win rate statistics for a list of symbols.

    Fetches all closed orders from Alpaca, aggregates consecutive same-side
    orders (partial fills), then pairs BUY/SELL to identify completed trades.

    Args:
        symbols: List of ticker symbols.

    Returns:
        Dict with keys:
            - pl (float): Total closed-trade P&L across all symbols.
            - trades_cnt (int): Total number of completed trades.
            - winning_trades_cnt (int): Number of trades with positive P&L.
            - win_rate (float): Fraction of winning trades, or NaN if no trades.
            - symbols_with_zero_trades_cnt (int): Count of symbols with no trades.
            - df_stats (DataFrame): Per-symbol stats indexed by Alpaca symbol name.
    """
    logger.info("Calculating closed trades stats")
    trading_client = create_trading_client()
    stats = []
    for symbol in symbols:
        logger.info(f"Processing symbol - {symbol}")
        request_params = GetOrdersRequest(status='closed', symbols=[symbol])
        orders = trading_client.get_orders(filter=request_params)
        orders_dicts = map(dict, orders)
        keys_to_keep = ['symbol', 'filled_at', 'filled_qty', 'filled_avg_price', 'side']
        filtered_orders = [{key: value for key, value in d.items() if key in keys_to_keep} for d in orders_dicts]
        df_orders = pd.DataFrame(filtered_orders)

        if len(df_orders) >= 2:
            df_orders['side'] = df_orders['side'].apply(str)

            if ('OrderSide.BUY' in df_orders['side'].tolist()) and \
               ('OrderSide.SELL' in df_orders['side'].tolist()):

                df_orders = df_orders.loc[~df_orders['filled_at'].isna(), :]
                df_orders['filled_qty'] = df_orders['filled_qty'].apply(float)
                df_orders['filled_avg_price'] = df_orders['filled_avg_price'].apply(float)

                df_orders.sort_values(by='filled_at', inplace=True)
                df_orders["group"] = (df_orders["side"] != df_orders["side"].shift()).cumsum()

                def weighted_avg_price(df):
                    return (df["filled_avg_price"] * df["filled_qty"]).sum() / df["filled_qty"].sum()

                df_agg = (
                    df_orders.groupby(["group"])
                    .apply(lambda group: pd.Series({
                        "filled_at": group["filled_at"].min(),
                        "filled_qty": group["filled_qty"].sum(),
                        "filled_avg_price": weighted_avg_price(group),
                        "side": group["side"].max()
                    }))
                    .reset_index()
                ).drop(columns=['group'])

                if len(df_agg) != len(df_orders):
                    logger.warning(f"symbol {symbol} - has weird combination of orders!!!")

                df_agg['filled_qty'] = df_agg['filled_qty'].round(3)
                df_agg[['filled_qty_lag', 'side_lag', 'filled_avg_price_lag']] = \
                    df_agg[['filled_qty', 'side', 'filled_avg_price']].shift(1)

                df_trades = df_agg.loc[
                    (df_agg['side'] == 'OrderSide.SELL') &
                    (df_agg['side_lag'] == 'OrderSide.BUY') &
                    (df_agg['filled_qty'] == df_agg['filled_qty_lag']), :
                ]
                df_trades['pl'] = (df_trades['filled_qty'] * df_trades['filled_avg_price']) - \
                                   (df_trades['filled_qty_lag'] * df_trades['filled_avg_price_lag'])

                last_trade_closed_at = df_trades['filled_at'].max().date()
                # last_trade_closed_at can be None when no trades have been closed yet
                days_since_last_closed_trade = (datetime.now().date() - last_trade_closed_at).days
                closed_winning_trades_cnt = len(df_trades.loc[df_trades['pl'] > 0, :])

                stats.append({
                    'closed_trades_pl': df_trades['pl'].sum(),
                    'closed_trades_cnt': len(df_trades),
                    'closed_winning_trades_cnt': closed_winning_trades_cnt,
                    'last_trade_closed_at': last_trade_closed_at,
                    'days_since_last_closed_trade': days_since_last_closed_trade,
                    'win_rate': closed_winning_trades_cnt / len(df_trades)
                })
            else:
                logger.warning(f"symbol {symbol} - has weird combination of orders!!!")
                stats.append({'closed_trades_pl': 0, 'closed_trades_cnt': 0,
                              'closed_winning_trades_cnt': 0, 'last_trade_closed_at': np.nan,
                              'days_since_last_closed_trade': 0, 'win_rate': np.nan})
        else:
            stats.append({'closed_trades_pl': 0, 'closed_trades_cnt': 0,
                          'closed_winning_trades_cnt': 0, 'last_trade_closed_at': np.nan,
                          'days_since_last_closed_trade': 0, 'win_rate': np.nan})

    index = pd.Series(symbols).map(lambda x: crypto_map[x] if x in crypto_map else x)
    df_stats = pd.DataFrame(stats, index=index)
    closed_trades_pl = df_stats['closed_trades_pl'].sum()
    closed_trades_cnt = df_stats['closed_trades_cnt'].sum()
    win_rate = (df_stats['closed_winning_trades_cnt'].sum() / df_stats['closed_trades_cnt'].sum()) \
        if closed_trades_cnt > 0 else np.nan
    zero_tr_symbols_cnt = (df_stats['closed_trades_cnt'] == 0).sum()
    winning_trades_cnt = df_stats['closed_winning_trades_cnt'].sum()

    return {
        'pl': closed_trades_pl,
        'trades_cnt': closed_trades_cnt,
        'winning_trades_cnt': winning_trades_cnt,
        'win_rate': win_rate,
        'symbols_with_zero_trades_cnt': zero_tr_symbols_cnt,
        'df_stats': df_stats
    }


def calculate_open_trades_stats(symbols):
    """Fetch current open position stats from Alpaca for a list of symbols.

    Symbols with no open position are included with zero values so that the
    returned DataFrame always covers all requested symbols.

    Args:
        symbols: List of ticker symbols (config format, e.g. 'BTC/USD').

    Returns:
        Dict with keys:
            - cost_basis (float): Total cost basis of open positions.
            - trades_cnt (int): Number of currently open positions.
            - symbols (list): List of symbols with open positions (Alpaca format).
            - pl (float): Total unrealized P&L.
            - market_value (float): Total market value.
            - total_return (float): Portfolio-level total return on open positions.
            - df_stats (DataFrame): Per-symbol position data.
    """
    logger.info("Calculating open trades stats")
    trading_client = create_trading_client()
    stats = []
    stats_not_opened = []
    for symbol in symbols:
        logger.info(f"Processing symbol - {symbol}")

        if symbol in crypto_map.keys():
            symbol_orig = symbol
            symbol = crypto_map[symbol]
        try:
            position = trading_client.get_open_position(symbol)
        except Exception:
            stats_not_opened.append({
                'symbol': symbol, 'cost_basis': 0, 'unrealized_pl': 0,
                'unrealized_plpc': 0, 'market_value': 0, 'change_today': 0.,
                'current_price': 0, 'lastday_price': 0, 'qty': 0,
                'side': np.nan, 'trade_opened_at': np.nan, 'days_since_open': 0
            })
        else:
            position_dict = dict(position)
            keys_to_keep = ['symbol', 'cost_basis', 'unrealized_pl', 'unrealized_plpc',
                            'market_value', 'change_today', 'current_price', 'lastday_price', 'qty', 'side']
            filtered_position = {key: position_dict[key] for key in keys_to_keep if key in position_dict}

            request_params = GetOrdersRequest(
                status='closed',
                symbols=[symbol if symbol not in crypto_map.values() else symbol_orig]
            )
            orders = trading_client.get_orders(filter=request_params)
            orders_dicts = map(dict, orders)
            keys_to_keep = ['symbol', 'filled_at']
            filtered_orders = [{key: value for key, value in d.items() if key in keys_to_keep} for d in orders_dicts]
            df_orders = pd.DataFrame(filtered_orders).sort_values(by='filled_at', ascending=False)

            trade_opened_at = df_orders['filled_at'][0].date()
            trade_opened_days = (datetime.now().date() - trade_opened_at).days

            filtered_position['trade_opened_at'] = trade_opened_at
            filtered_position['days_since_open'] = trade_opened_days
            stats.append(filtered_position)

    if len(stats_not_opened) > 0:
        df_stats_not_opened = pd.DataFrame(stats_not_opened).set_index('symbol')
    else:
        df_stats_not_opened = pd.DataFrame()

    if len(stats) > 0:
        df_stats = pd.DataFrame(stats)
        cols = ['cost_basis', 'unrealized_pl', 'unrealized_plpc', 'market_value',
                'change_today', 'current_price', 'lastday_price', 'qty']
        df_stats.loc[:, cols] = df_stats.loc[:, cols].astype('float')
        df_stats.set_index('symbol', inplace=True)
        df_stats['side'] = df_stats['side'].apply(lambda x: str(x).split('.')[1])

        open_trades_cost_basis = df_stats['cost_basis'].sum()
        open_trades_cnt = len(df_stats)
        open_trades_symbols = df_stats.index.tolist()
        open_trades_pl = df_stats['unrealized_pl'].sum()
        open_trades_market_value = df_stats['market_value'].sum()
        open_trades_total_return = (df_stats['market_value'].sum() / df_stats['cost_basis'].sum()) - 1

        df_stats = pd.concat([df_stats, df_stats_not_opened], axis=0)

        return {
            'cost_basis': open_trades_cost_basis,
            'trades_cnt': open_trades_cnt,
            'symbols': open_trades_symbols,
            'pl': open_trades_pl,
            'market_value': open_trades_market_value,
            'total_return': open_trades_total_return,
            'df_stats': df_stats
        }
    else:
        return {
            'cost_basis': 0,
            'trades_cnt': 0,
            'symbols': [],
            'pl': 0,
            'market_value': 0,
            'total_return': 0,
            'df_stats': df_stats_not_opened
        }


def calculate_sharpe_ratio(type, name, todays_return, date, period, trading_period=252):
    """Compute the annualised Sharpe ratio for a portfolio, strategy, or symbol.

    Fetches historical daily returns from the DB and appends today's return
    before computing the ratio.

    Args:
        type: One of 'portfolio', 'strategy', or 'symbol'.
        name: Name of the entity (portfolio name, strategy name, symbol, or 'whole').
        todays_return: Today's return to append to the historical series.
        date: Today's date (used as the index for today's return).
        period: Lookback period string: '1w', '1m', '3m', or 'overall'.
        trading_period: Number of trading days per year for annualisation (default 252).

    Returns:
        Annualised Sharpe ratio as a float.
    """
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))

    if period == '1w':
        period_start = date - timedelta(weeks=1)
    elif period == '1m':
        period_start = date - timedelta(days=30)
    elif period == '3m':
        period_start = date - timedelta(days=90)
    elif period == 'overall':
        period_start = date - timedelta(weeks=10_000)

    period_start = period_start.strftime("%Y-%m-%d")

    if type == 'portfolio':
        if name == 'whole':
            df = pd.read_sql(f"select date, daily_return from whole_portfolio_state where date >= '{period_start}'", con)
        else:
            df = pd.read_sql(f"select date, daily_return from portfolio_state where portfolio_name = '{name}' and date >= '{period_start}'", con)
    elif type == 'symbol':
        df = pd.read_sql(f"select date, daily_return from symbol_state where date >= '{period_start}' and symbol = '{name}'", con)
    elif type == 'strategy':
        df = pd.read_sql(f"select date, daily_return from strategy_state where date >= '{period_start}' and strategy = '{name}'", con)
    con.close()

    df.sort_values('date', inplace=True)
    s = df.set_index('date')['daily_return']
    s = pd.concat([s, pd.Series(todays_return, index=[date])])

    return trading_period ** (1 / 2) * (s.mean() / s.std())


def calculate_todays_return(portfolio, equity, portfolio_size):
    """Compute today's return for a portfolio, adjusted for any portfolio size change.

    Reads the previous row from the DB and calculates the return as:
    (equity_change - portfolio_size_change) / previous_equity.

    Args:
        portfolio: Portfolio name string.
        equity: Current equity value.
        portfolio_size: Current portfolio size (used to detect deposits/withdrawals).

    Returns:
        Today's return as a float, or 0.0 if no prior records exist in the DB.
    """
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))
    df = pd.read_sql(f"""select date, portfolio_size, equity from portfolio_state
                         where portfolio_name = '{portfolio}' order by date desc limit 1""", con)
    con.close()

    if len(df) == 0:
        return 0.
    return ((equity - df['equity'][0]) / df['equity'][0]) - \
           ((portfolio_size - df['portfolio_size'][0]) / df['equity'][0])


def calculate_total_return(type, name, todays_return, date, period):
    """Compute the compounded total return over a given period.

    Args:
        type: One of 'portfolio', 'strategy', or 'symbol'.
        name: Name of the entity, or 'whole' for the aggregate portfolio.
        todays_return: Today's return to append to the historical series.
        date: Today's date.
        period: Lookback period string: '1w', '1m', '3m', or 'overall'.

    Returns:
        Compounded total return as a float.
    """
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))

    if period == '1w':
        period_start = date - timedelta(weeks=1)
    elif period == '1m':
        period_start = date - timedelta(days=30)
    elif period == '3m':
        period_start = date - timedelta(days=90)
    elif period == 'overall':
        period_start = date - timedelta(weeks=10_000)

    period_start = period_start.strftime("%Y-%m-%d")

    if type == 'portfolio':
        if name == 'whole':
            df = pd.read_sql(f"select date, daily_return from whole_portfolio_state where date >= '{period_start}'", con)
        else:
            df = pd.read_sql(f"select date, daily_return from portfolio_state where portfolio_name = '{name}' and date >= '{period_start}'", con)
    elif type == 'symbol':
        df = pd.read_sql(f"select date, daily_return from symbol_state where symbol = '{name}' and date >= '{period_start}'", con)
    elif type == 'strategy':
        df = pd.read_sql(f"select date, daily_return from strategy_state where date >= '{period_start}' and strategy = '{name}'", con)
    con.close()

    df.sort_values('date', inplace=True)
    s = df.set_index('date')['daily_return']
    s = pd.concat([s, pd.Series(todays_return, index=[date])])
    return (s + 1).prod() - 1


def calculate_absolute_return(type, name, date, closed_trades_pl, open_trades_pl, period):
    """Compute absolute P&L (dollar return) over a given period.

    Calculated as: (current closed P&L - starting closed P&L) + current open P&L.

    Args:
        type: One of 'portfolio', 'strategy', or 'symbol'.
        name: Name of the entity, or 'whole' for the aggregate portfolio.
        date: Today's date.
        closed_trades_pl: Current cumulative closed-trade P&L.
        open_trades_pl: Current unrealized open-trade P&L.
        period: Lookback period string: '1w', '1m', '3m', or 'overall'.

    Returns:
        Absolute dollar return as a float, or NaN if no historical data exists.
    """
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))

    if period == '1w':
        period_start = date - timedelta(weeks=1)
    elif period == '1m':
        period_start = date - timedelta(days=30)
    elif period == '3m':
        period_start = date - timedelta(days=90)
    elif period == 'overall':
        period_start = date - timedelta(weeks=10_000)

    period_start = period_start.strftime("%Y-%m-%d")

    if type == 'portfolio':
        if name == 'whole':
            df = pd.read_sql(f"select date, closed_trades_PL from whole_portfolio_state where date >= '{period_start}'", con)
        else:
            df = pd.read_sql(f"select date, closed_trades_PL from portfolio_state where portfolio_name = '{name}' and date >= '{period_start}'", con)
    elif type == 'symbol':
        df = pd.read_sql(f"select date, closed_trades_PL from symbol_state where symbol = '{name}' and date >= '{period_start}'", con)
    elif type == 'strategy':
        df = pd.read_sql(f"select date, closed_trades_PL from strategy_state where date >= '{period_start}' and strategy = '{name}'", con)
    con.close()

    df.sort_values('date', inplace=True)
    s = df.set_index('date')['closed_trades_PL']

    if len(s) == 0:
        return np.nan

    return closed_trades_pl - s[0] + open_trades_pl


def calculate_drawdown(type, name, date, todays_return):
    """Compute the maximum drawdown and its duration for a given entity.

    Args:
        type: One of 'portfolio', 'strategy', or 'symbol'.
        name: Name of the entity, or 'whole' for the aggregate portfolio.
        date: Today's date (used to append today's return to the series).
        todays_return: Today's return value.

    Returns:
        Tuple of (max_drawdown, max_drawdown_duration):
            - max_drawdown (float): Maximum drawdown fraction (negative value).
            - max_drawdown_duration (int): Length of the longest drawdown in days.
    """
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))

    if type == 'portfolio':
        if name == 'whole':
            df = pd.read_sql("select date, daily_return from whole_portfolio_state", con)
        else:
            df = pd.read_sql(f"select date, daily_return from portfolio_state where portfolio_name = '{name}'", con)
    elif type == 'symbol':
        df = pd.read_sql(f"select date, daily_return from symbol_state where symbol = '{name}'", con)
    elif type == 'strategy':
        df = pd.read_sql(f"select date, daily_return from strategy_state where strategy = '{name}'", con)
    con.close()

    df.sort_values('date', inplace=True)
    s = df.set_index('date')['daily_return']
    s = pd.concat([s, pd.Series(todays_return, index=[date])])

    max_drawdown = qs.stats.max_drawdown(s)
    cummax = (1 + s).cumprod().cummax()
    max_drawdown_duration = cummax.value_counts().head(1).iloc[0]

    return max_drawdown, max_drawdown_duration


def calculate_calmar_ratio(type, name, date, max_drawdown, todays_return, trading_period=252):
    """Compute the Calmar ratio (CAGR / max drawdown) for a given entity.

    Args:
        type: One of 'portfolio', 'strategy', or 'symbol'.
        name: Name of the entity, or 'whole' for the aggregate portfolio.
        date: Today's date.
        max_drawdown: Pre-computed maximum drawdown (negative float).
        todays_return: Today's return to append to the historical series.
        trading_period: Trading days per year used to compute CAGR (default 252).

    Returns:
        Calmar ratio as a float, or None if computation fails.
    """
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))

    if type == 'portfolio':
        if name == 'whole':
            df = pd.read_sql("select date, daily_return from whole_portfolio_state", con)
        else:
            df = pd.read_sql(f"select date, daily_return from portfolio_state where portfolio_name = '{name}'", con)
    elif type == 'symbol':
        df = pd.read_sql(f"select date, daily_return from symbol_state where symbol = '{name}'", con)
    elif type == 'strategy':
        df = pd.read_sql(f"select date, daily_return from strategy_state where strategy = '{name}'", con)
    con.close()

    df.sort_values('date', inplace=True)
    daily_returns = df.set_index('date')['daily_return']
    daily_returns = pd.concat([daily_returns, pd.Series(todays_return, index=[date])])

    investment_period_years = len(daily_returns) / trading_period
    cagr = (1 + daily_returns).prod() ** (1 / investment_period_years) - 1

    try:
        return cagr / abs(max_drawdown)
    except Exception:
        logger.warning(f"{type} - {name} - unable to calculate calmar ratio")
        return None


def calculate_sortino_ratio(type, name, date, todays_return, trading_period=252):
    """Compute the annualised Sortino ratio for a given entity.

    Args:
        type: One of 'portfolio', 'strategy', or 'symbol'.
        name: Name of the entity, or 'whole' for the aggregate portfolio.
        date: Today's date.
        todays_return: Today's return to append to the historical series.
        trading_period: Trading days per year for annualisation (default 252).

    Returns:
        Sortino ratio as a float, or NaN if fewer than 2 non-null observations exist.
    """
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))

    if type == 'portfolio':
        if name == 'whole':
            df = pd.read_sql("select date, daily_return from whole_portfolio_state", con)
        else:
            df = pd.read_sql(f"select date, daily_return from portfolio_state where portfolio_name = '{name}'", con)
    elif type == 'symbol':
        df = pd.read_sql(f"select date, daily_return from symbol_state where symbol = '{name}'", con)
    elif type == 'strategy':
        df = pd.read_sql(f"select date, daily_return from strategy_state where strategy = '{name}'", con)
    con.close()

    df.sort_values('date', inplace=True)
    daily_returns = df.set_index('date')['daily_return']
    daily_returns = pd.concat([daily_returns, pd.Series(todays_return, index=[date])])

    if daily_returns.notna().sum() > 1:
        return qs.stats.sortino(daily_returns, annualize=True, periods=trading_period)
    return np.nan


def update_portfolio_state(portfolio, portfolio_size, symbols, run_id, timestamp, trades):
    """Compute all portfolio-level metrics and write a state snapshot to the DB.

    Args:
        portfolio: Portfolio name string.
        portfolio_size: Configured dollar size of the portfolio.
        symbols: List of all symbols in the portfolio.
        run_id: Unique run identifier string.
        timestamp: datetime of the current run.
        trades: Dict mapping symbol → action ('open', 'close', 'no_change').
    """
    logger.info(f"Updating state of portfolio - {portfolio}")
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))
    date = timestamp.date()

    result_closed_trades = calculate_closed_trades_stats(symbols)
    result_open_trades = calculate_open_trades_stats(symbols)

    # available_cash = portfolio_size + closed P&L - open cost basis
    available_cash = portfolio_size + result_closed_trades['pl'] - result_open_trades['cost_basis']
    # equity = available_cash + open cost basis + open P&L
    equity = available_cash + result_open_trades['cost_basis'] + result_open_trades['pl']

    todays_return = calculate_todays_return(portfolio, equity, portfolio_size)
    sharpe_ratio = calculate_sharpe_ratio('portfolio', portfolio, todays_return, date, 'overall')
    total_return = calculate_total_return('portfolio', portfolio, todays_return, date, 'overall')
    absolute_return = calculate_absolute_return('portfolio', portfolio, date, result_closed_trades['pl'], result_open_trades['pl'], 'overall')
    max_drawdown, max_drawdown_duration = calculate_drawdown('portfolio', portfolio, date, todays_return)
    calmar_ratio = calculate_calmar_ratio('portfolio', portfolio, date, max_drawdown, todays_return)
    sortino_ratio = calculate_sortino_ratio('portfolio', portfolio, date, todays_return)
    symbols_to_open_cnt = len([key for key, value in trades.items() if value == 'open'])
    symbols_to_close_cnt = len([key for key, value in trades.items() if value == 'close'])

    data = (timestamp, date, run_id, portfolio, portfolio_size,
            float(available_cash), float(equity),
            result_open_trades['trades_cnt'], str(result_open_trades['symbols']),
            float(result_open_trades['pl']), result_open_trades['cost_basis'],
            int(result_closed_trades['trades_cnt']), float(result_closed_trades['pl']),
            float(result_closed_trades['win_rate']), float(sharpe_ratio),
            calmar_ratio, sortino_ratio, float(total_return),
            float(max_drawdown), int(max_drawdown_duration),
            float(todays_return), float(absolute_return),
            int(result_closed_trades['symbols_with_zero_trades_cnt']),
            len(symbols), symbols_to_open_cnt, symbols_to_close_cnt)
    con.execute("""INSERT INTO portfolio_state VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
    con.commit()
    con.close()


def update_whole_portfolio_state(run_id, timestamp, config):
    """Compute account-level metrics and write an aggregate portfolio snapshot to the DB.

    Fetches live account data from Alpaca and aggregates stats across all
    sub-portfolios defined in the config.

    Args:
        run_id: Unique run identifier string.
        timestamp: datetime of the current run.
        config: Full portfolio config dict (all sub-portfolios).
    """
    logger.info("Updating whole portfolio state")
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))
    date = timestamp.date()
    trading_client = create_trading_client()
    account_info = dict(trading_client.get_account())

    url = "https://paper-api.alpaca.markets/v2/account/activities/TRANS"
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": keys['paper_key'],
        "APCA-API-SECRET-KEY": keys['paper_secret']
    }
    response = requests.get(url, headers=headers)
    # TODO: parse deposits_withdrawals from transactions when switching to live account
    deposits_withdrawals = 0

    equity = float(account_info['equity'])
    last_equity = float(account_info['last_equity'])
    cash = float(account_info['cash'])
    long_mk_value = float(account_info['long_market_value'])
    short_mk_value = float(account_info['short_market_value'])
    non_marg_buying_power = float(account_info['non_marginable_buying_power'])
    subportfolios_cnt = len(config.keys())
    subportfolios_allocation = sum([config[portfolio]['portfolio_size'] for portfolio in config.keys()])

    symbols = [config[portfolio]['symbols'].keys() for portfolio in config.keys()]
    symbols = [item for sublist in symbols for item in sublist]
    open_trades_stats = calculate_open_trades_stats(symbols)
    closed_trades_stats = calculate_closed_trades_stats(symbols)

    todays_return = ((equity - last_equity) / last_equity) - (deposits_withdrawals / last_equity)
    sharpe_ratio = calculate_sharpe_ratio('portfolio', 'whole', todays_return, date, 'overall')
    total_return = calculate_total_return('portfolio', 'whole', todays_return, date, 'overall')
    absolute_return = calculate_absolute_return('portfolio', 'whole', date, closed_trades_stats['pl'], open_trades_stats['pl'], 'overall')
    max_drawdown, max_drawdown_duration = calculate_drawdown('portfolio', 'whole', date, todays_return)
    calmar_ratio = calculate_calmar_ratio('portfolio', 'whole', date, max_drawdown, todays_return)
    sortino_ratio = calculate_sortino_ratio('portfolio', 'whole', date, todays_return)

    data = (timestamp, date, run_id, equity, last_equity, cash, long_mk_value, short_mk_value,
            non_marg_buying_power, deposits_withdrawals, subportfolios_cnt, float(subportfolios_allocation),
            int(open_trades_stats['trades_cnt']), str(open_trades_stats['symbols']),
            float(open_trades_stats['pl']), float(open_trades_stats['cost_basis']),
            float(closed_trades_stats['trades_cnt']), float(closed_trades_stats['pl']),
            float(closed_trades_stats['win_rate']), float(sharpe_ratio),
            calmar_ratio, sortino_ratio, float(total_return),
            float(max_drawdown), int(max_drawdown_duration),
            float(todays_return), float(absolute_return))
    con.execute("""INSERT INTO whole_portfolio_state VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
    con.commit()
    con.close()


def update_strategy_state(run_id, timestamp, config, trades):
    """Compute per-strategy metrics and write state snapshots to the DB.

    Groups symbols by strategy across all sub-portfolios and writes one row
    per unique strategy to the `strategy_state` table.

    Args:
        run_id: Unique run identifier string.
        timestamp: datetime of the current run.
        config: Full portfolio config dict (all sub-portfolios).
        trades: List of per-portfolio trade dicts mapping symbol → action.
    """
    logger.info("Updating state of strategies")
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))
    date = timestamp.date()

    symbol_strategy_pairs = pd.Series({
        symbol: list(config[portfolio]['symbols'][symbol].keys())[0]
        for portfolio in config.keys()
        for symbol in config[portfolio]['symbols'].keys()
    })
    unique_strategies = symbol_strategy_pairs.unique()

    for strategy in unique_strategies:
        symbols = symbol_strategy_pairs[symbol_strategy_pairs == strategy].index.tolist()
        result_closed_trades = calculate_closed_trades_stats(symbols)
        result_open_trades = calculate_open_trades_stats(symbols)
        df_open = result_open_trades['df_stats']

        long_positions_cnt = (df_open['side'] == 'LONG').sum()
        short_positions_cnt = (df_open['side'] == 'SHORT').sum()

        todays_return = strategy_todays_return(result_open_trades['symbols'], result_open_trades['market_value'])
        sharpe_ratio = calculate_sharpe_ratio('strategy', strategy, todays_return, date, 'overall')
        total_return = calculate_total_return('strategy', strategy, todays_return, date, 'overall')
        absolute_return = calculate_absolute_return('strategy', strategy, date, result_closed_trades['pl'], result_open_trades['pl'], 'overall')
        max_drawdown, max_drawdown_duration = calculate_drawdown('strategy', strategy, date, todays_return)
        calmar_ratio = calculate_calmar_ratio('strategy', strategy, date, max_drawdown, todays_return)
        sortino_ratio = calculate_sortino_ratio('strategy', strategy, date, todays_return)
        symbols_to_open_cnt = sum(1 for entry in trades for symbol in symbols if entry.get(symbol) == 'open')
        symbols_to_close_cnt = sum(1 for entry in trades for symbol in symbols if entry.get(symbol) == 'close')

        data = (timestamp, date, run_id, strategy,
                float(result_open_trades['trades_cnt']), str(result_open_trades['symbols']),
                float(result_open_trades['pl']), float(result_open_trades['total_return']),
                float(result_open_trades['cost_basis']), float(result_open_trades['market_value']),
                float(long_positions_cnt), float(short_positions_cnt),
                float(todays_return), float(result_closed_trades['trades_cnt']),
                float(result_closed_trades['pl']), float(result_closed_trades['winning_trades_cnt']),
                float(result_closed_trades['win_rate']), float(sharpe_ratio),
                float(calmar_ratio), float(sortino_ratio), float(total_return),
                float(max_drawdown), float(max_drawdown_duration),
                float(absolute_return), float(result_closed_trades['symbols_with_zero_trades_cnt']),
                float(len(symbols)), float(symbols_to_open_cnt), float(symbols_to_close_cnt))
        con.execute("""INSERT INTO strategy_state VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
        con.commit()
        con.close()


def strategy_todays_return(open_symbols, open_trades_mk_value):
    """Compute today's return for a strategy based on market value change.

    Excludes crypto positions that were opened today (no prior-day benchmark).
    Formula: today's market value / (prior-day market value + today's new cost basis) - 1.

    Args:
        open_symbols: List of currently open Alpaca symbols (Alpaca format).
        open_trades_mk_value: Total current market value of open positions.

    Returns:
        Today's return as a float, or 0 if computation fails.
    """
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))
    df = pd.read_sql("select date, symbol, cost_basis, market_value, days_opened, trade_opened from symbol_state", con)
    con.close()

    df['date'] = pd.to_datetime(df['date'])
    df['trade_opened'] = pd.to_datetime(df['trade_opened'])

    # Exclude crypto positions opened today: they have no prior-day market value to compare against
    open_crypto_symbols = [symbol for symbol in crypto_map.values() if symbol in open_symbols]
    crypto_today_opened_mk_value = df.loc[
        (df['date'] == df['date'].max()) &
        (df['symbol'].isin(open_crypto_symbols)) &
        (df['trade_opened'] == df['date'].max()), 'market_value'
    ].sum()
    open_trades_mk_value = open_trades_mk_value - crypto_today_opened_mk_value

    mk_value = df.loc[
        (df['symbol'].isin(open_symbols)) & (df['date'] == (df['date'].max() - timedelta(days=1))), 'market_value'
    ].sum()
    cost_basis = df.loc[
        (df['symbol'].isin(open_symbols)) & (df['date'] == df['date'].max()) & (df['days_opened'] == 1), 'cost_basis'
    ].sum()

    try:
        return (float(open_trades_mk_value) / float(mk_value + cost_basis)) - 1
    except Exception:
        return 0


def update_symbol_state(run_id, timestamp, symbols, config):
    """Compute per-symbol metrics and write state snapshots to the DB.

    Args:
        run_id: Unique run identifier string.
        timestamp: datetime of the current run.
        symbols: List of ticker symbols (config format).
        config: Full portfolio config dict used to look up each symbol's strategy.
    """
    logger.info("Updating state of symbols")
    con = sqlite3.connect(str(ROOT_DIR / 'db/calpha.db'))
    date = timestamp.date()

    result_closed_trades = calculate_closed_trades_stats(symbols)
    result_open_trades = calculate_open_trades_stats(symbols)
    df_open = result_open_trades['df_stats']
    df_closed = result_closed_trades['df_stats']

    for symbol in symbols:
        logger.info(f"Updating symbol stats - {symbol}")
        for portfolio, data in config.items():
            if symbol in data['symbols']:
                strategy = list(data['symbols'][symbol].keys())[0]
                break
        if symbol in crypto_map.keys():
            symbol = crypto_map[symbol]

        is_open = 'Y' if symbol in result_open_trades['symbols'] else 'N'

        open_trade_pl = df_open.loc[symbol, 'unrealized_pl']
        open_trade_total_return = df_open.loc[symbol, 'unrealized_plpc']
        open_trade_cost_basis = df_open.loc[symbol, 'cost_basis']
        open_trade_daily_return = df_open.loc[symbol, 'change_today']
        open_trade_last_day_close = df_open.loc[symbol, 'lastday_price']
        open_trade_current_price = df_open.loc[symbol, 'current_price']
        open_trade_market_value = df_open.loc[symbol, 'market_value']
        open_trade_qty = df_open.loc[symbol, 'qty']
        open_trade_side = df_open.loc[symbol, 'side']
        open_trade_opened_at = df_open.loc[symbol, 'trade_opened_at']
        open_trade_days_since_open = df_open.loc[symbol, 'days_since_open']
        closed_trades_cnt = df_closed.loc[symbol, 'closed_trades_cnt']
        closed_trades_pl = df_closed.loc[symbol, 'closed_trades_pl']
        last_trade_closed_at = df_closed.loc[symbol, 'last_trade_closed_at']
        days_since_last_closed_trade = df_closed.loc[symbol, 'days_since_last_closed_trade']
        closed_winning_trades_cnt = df_closed.loc[symbol, 'closed_winning_trades_cnt']
        win_rate = df_closed.loc[symbol, 'win_rate']
        sharpe_ratio = calculate_sharpe_ratio('symbol', symbol, open_trade_daily_return, date, 'overall')
        sortino_ratio = calculate_sortino_ratio('symbol', symbol, date, open_trade_daily_return)
        total_return = calculate_total_return('symbol', symbol, open_trade_daily_return, date, 'overall')
        max_drawdown, max_d_period = calculate_drawdown('symbol', symbol, date, open_trade_daily_return)
        calmar_ratio = calculate_calmar_ratio('symbol', symbol, date, max_drawdown, open_trade_daily_return)
        absolute_return = calculate_absolute_return('symbol', symbol, date,
                                                    df_closed.loc[symbol, 'closed_trades_pl'],
                                                    df_open.loc[symbol, 'unrealized_pl'], 'overall')

        data = (timestamp, date, run_id, symbol, portfolio, strategy, is_open,
                float(open_trade_pl), float(open_trade_total_return), float(open_trade_cost_basis),
                float(open_trade_daily_return), float(open_trade_last_day_close),
                float(open_trade_current_price), float(open_trade_market_value),
                float(open_trade_qty), open_trade_side, open_trade_opened_at,
                float(open_trade_days_since_open), int(closed_trades_cnt),
                float(closed_trades_pl), last_trade_closed_at,
                int(days_since_last_closed_trade), int(closed_winning_trades_cnt),
                float(win_rate), float(sharpe_ratio), float(calmar_ratio),
                float(sortino_ratio), float(total_return), float(max_drawdown),
                int(max_d_period), float(absolute_return))
        con.execute("""INSERT INTO symbol_state VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
        con.commit()
    con.close()


def generate_id():
    """Generate a unique run identifier using UUID4.

    Returns:
        UUID4 string.
    """
    return str(uuid.uuid4())


def strategy_data_prep(strategy, symbol, data_preference, start, end):
    """Load and prepare symbol data for signal generation.

    For HHHL ML1, computes all pandas-ta technical indicators and drops
    columns that cause issues (e.g. SSF, TOS_STDEVALL variants that return
    inconsistent shapes across symbols).

    Args:
        strategy: Strategy name string ('hhhl' or 'hhhl_ml1').
        symbol: Ticker symbol.
        data_preference: Data source preference passed to data_load.
        start: Start date for data loading.
        end: End date for data loading.

    Returns:
        Tuple of (df_symbol, close_price):
            - df_symbol: DataFrame of OHLCV plus indicators (for ML1) or
              raw OHLCV (for HHHL).
            - close_price: Series of close prices.
    """
    if strategy == 'hhhl':
        df_symbol = data_load(symbol, data_preference, start, end)
        close_price = df_symbol['close']
    elif strategy == 'hhhl_ml1':
        df_symbol = data_load(symbol, data_preference, start, end)
        df_symbol.ta.strategy('All')
        close_price = df_symbol['close']
        df_symbol.drop(columns=['adj close'], inplace=True)
        df_symbol.ta.strategy('All')
        # These columns produce inconsistent output shapes across symbols
        df_symbol.drop(columns=['SSF_10_2', 'TOS_STDEVALL_LR', 'TOS_STDEVALL_L_1',
                                 'TOS_STDEVALL_U_1', 'TOS_STDEVALL_L_2', 'TOS_STDEVALL_U_2',
                                 'TOS_STDEVALL_L_3', 'TOS_STDEVALL_U_3'], inplace=True)

    return df_symbol, close_price


def save_entries_exits(symbol, entries, exits, timestamp):
    """Persist today's entry and exit signals to CSV files in run_data/.

    Files are saved under `run_data/<YYYY-MM-DD>/<symbol>_entries_<date>.csv`
    and the corresponding exits file.

    Args:
        symbol: Ticker symbol (used in the file name).
        entries: Boolean Series of entry signals.
        exits: Boolean Series of exit signals.
        timestamp: datetime of the current run (determines the date folder).
    """
    logger.info("Saving run files - entries & exits")
    date_str = timestamp.strftime("%Y-%m-%d")
    folder_path = str(ROOT_DIR / f'run_data/{date_str}')
    os.makedirs(folder_path, exist_ok=True)

    entries_file = f"{folder_path}/{symbol}_entries_{date_str}.csv"
    exits_file = f"{folder_path}/{symbol}_exits_{date_str}.csv"

    entries.to_frame(name="entry").to_csv(entries_file, index=True)
    exits.to_frame(name="exit").to_csv(exits_file, index=True)
