import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime
from time import sleep

from online import Online
import six
import local_tools
from algo import Algo
from cvxopt import solvers, matrix
solvers.options['show_progress'] = False
from sklearn.preprocessing import MinMaxScaler

import sys
sys.path.append('REDACTED/rltrader/pytrade_env/pytrade_env/database')
import trade_history
from trade_history import TradeHistory


def just_update_trade_history(currency_pairs, verbose = True):
    history = TradeHistory(currency_pairs = currency_pairs,
                           time_period = '30min',
                           data_dir = 'REDACTED',
                           verbose = verbose)
    history.update_trade_history(currency_pairs = currency_pairs, reset_period_end = True)
    history.add_raw_trade_history_to_processed_db()
    
    return 'success'

def get_online_weights(currency_pairs, time_period = '24h', verbose = True):
    
    history = TradeHistory(currency_pairs = currency_pairs,
                           time_period = time_period,
                           data_dir = 'REDACTED',
                           verbose = verbose)
    history.update_trade_history(currency_pairs = currency_pairs, reset_period_end = True)
    history.add_raw_trade_history_to_processed_db()
    
    price_df = history.reformat_for_online_algo(df = history.get_processed_charts_from_db(),
                                                cols_to_include = ['close'])
    
    scaler = MinMaxScaler(feature_range = (0.5, 1.5))
    scaled_prices = scaler.fit_transform(price_df).copy()
    scaled_prices = pd.DataFrame(scaled_prices)
    scaled_prices.columns = [col for col in price_df.columns.tolist()]

    # run algo
    algo = Online()
    algo = algo.run(scaled_prices)
    online_weights = algo.weights
    online_weights.columns = [col.replace('usdt', 'usdt_').replace('_close','').upper() for
                              col in online_weights.columns.tolist()]
    
    return online_weights