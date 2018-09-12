import pandas as pd
import numpy as np
import sqlite3
import datetime
import json
import hmac
import hashlib
import time
import requests
import base64
from time import sleep




#####################
#
# BFX API Wrapper
#
########


def get_cp_map():
    '''
    keeping polo's naming convention for db reasons. updating can be done by hardcoding
    here or by using the update method (though it's best to just hardcode it)
    '''
    
    cp_dict = {
        
        'USDT_BTC':  'tBTCUSD', 'USDT_BCH':  'tBCHUSD', 'USDT_LTC':  'tLTCUSD',
        'USDT_ETH':  'tETHUSD', 'USDT_ETC':  'tETCUSD', 'USDT_ZEC':  'tZECUSD',
        'USDT_XMR':  'tXMRUSD', 'USDT_DASH': 'tDSHUSD', 'USDT_SAN':  'tSANUSD',
        'USDT_NEO':  'tNEOUSD', 'USDT_IOTA': 'tIOTUSD', 'USDT_OMG':  'tOMGUSD',
        'USDT_QTUM': 'tQTMUSD', 'USDT_ZRX': 'tZRXUSD', 'USDT_BAT': 'tBATUSD',
        'USDT_BTG': 'tBTGUSD', 'USDT_SNT': 'tSNTUSD', 'USDT_GNT': 'tGNTUSD',
        'USDT_FUN': 'tFUNUSD', 'USDT_AVT': 'tAVTUSD', 'USDT_SPANK': 'tSPKUSD',
        'USDT_EDO': 'tEDOUSD', 'USDT_QASH': 'tQSHUSD', 'USDT_EOS': 'tEOSUSD',
        'USDT_XRP': 'tXRPUSD', 'USDT_REP': 'tREPUSD', 'USDT_ELF': 'tELFUSD',
        'USDT_TRX': 'tTRXUSD', 'USDT_RCN': 'tRCNUSD', 'USDT_SNG': 'tSNGUSD',
        'USDT_RLC': 'tRLCUSD', 'USDT_AID': 'tAIDUSD'
    }

    # map cp for easy indexing
    cp_map = Mapping()
    for cp in cp_dict:
        cp_map[str(cp)] = str(cp_dict[cp])
    
    return cp_map


# two way dictionary / map for currency pairs
class Mapping(dict):
    def __setitem__(self, key, value):
        # Remove any previous connections with these values
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)

    def __len__(self):
        return dict.__len__(self) // 2


class BFXClient(object):
    
    def __init__(self, key, secret, *args, **kwargs):
        '''
        Stores the username, key, and secret which is used when making POST
        requests to Bitfinex.
        '''
        
        self.BASE_URL = "https://api.bitfinex.com"
        self.KEY = key
        self.SECRET = secret
        self.cp_map = get_cp_map()
        
    
    def _nonce(self):
        '''
        Used in authentication. Returns a nonce that always needs to be
        increasing (essentially a unix timestamp)
        '''
        return str(int(round(time.time() * 1000)))
    
    
    def _verbose(self, **kwargs):
        '''
        Helper method to print the endpoint and payload
        '''
        path = kwargs['path']
        payload = kwargs['payload']
        
        print('\nEndpoint:')
        print(self.BASE_URL + path)
        print('\nPayload:')
        print(payload)
    
    
    def _headers(self, path, nonce, body):
        
        # create signature
        signature = "/api" + path + nonce + body
        
        # byte encode secret and sig
        h = hmac.new(self.SECRET.encode(), signature.encode(), hashlib.sha384)
        signature = h.hexdigest()

        return {
            "bfx-nonce": nonce,
            "bfx-apikey": self.KEY,
            "bfx-signature": signature,
            "content-type": "application/json"
        }
    
    
    def _post(self, **kwargs):
        
        # init args
        path = kwargs['path']
        verbose = kwargs['verbose']
        
        # build request
        nonce = self._nonce()
        body = {}
        rawBody = json.dumps(body)
        headers = self._headers(path, nonce, rawBody)
        
        # print payload for debugging
        if verbose:
            print('\nEndpoint:')
            print(self.BASE_URL + path)
            print('\nPayload:')
            print("{"+self.BASE_URL + path + ", headers=" + str(headers) + ", data=" + rawBody + ", verify=True)}")
        
        # post request
        r = requests.post(self.BASE_URL + path, headers = headers, data = rawBody, verify = True)
        
        # print status
        if r.status_code == 200:
            print('\nSuccess!\n')
            return r.json()
        else:
            print(r.status_code)
            print(r)
            return None
    
    
    def add_cp_mapping(self, standard_naming_key, bfx_naming_value):
        '''
        Add a new k/v to the bfx symbol map
        '''
        self.cp_map[standard_naming_key] = bfx_naming_value
        print('Successfully added', standard_naming_key)
    
    
    def v1_payload(self, payload):
        '''
        Used to build / pack the payload for Version 1 (v1) of the API.
        v1 is usually used when an action requires the use of the websocket on v2.
        '''
        
        # sign & pack payload
        j = json.dumps(payload)
        b = bytes(j, 'utf-8')
        data = base64.standard_b64encode(b)
        h = hmac.new(self.SECRET.encode(), data, hashlib.sha384)
        signature = h.hexdigest()
        
        packed = {
            "X-BFX-APIKEY": self.KEY,
            "X-BFX-SIGNATURE": signature,
            "X-BFX-PAYLOAD": data
        }

        return packed
    
    
    def v1_post(self, path, payload, verify = True):
        '''
        POST helper for v1 of the API
        '''
        
        # pack & sign
        signed_payload = self.v1_payload(payload)
        
        # post request
        r = requests.post(self.BASE_URL + path,
                          headers = signed_payload,
                          verify = verify
                         )
        response = r.json()
        
        return response
    
    
    #########
    # API Actions
    ###
    
    def active_orders(self, verbose = False):
        '''
        Get the active orders for the current user.
        '''
        return self._post(path = '/v2/auth/r/orders', verbose = verbose)
    
    
    def new_order_v1(self, amount, price, side, order_type, symbol,
                     exchange = 'bitfinex', verbose = False):
        '''
        Uses v1 API endpoint.
        Create a new order for a specified asset.
        '''
        # set path and build payload
        path = '/v1/order/new'
        payload = {
            "request": path,
            "nonce": self._nonce(),
            "symbol": symbol,
            "amount": amount,
            "price": price,
            "exchange": exchange,
            "side": side,
            "type": order_type
        }
        
        # post order
        response = self.v1_post(path, payload)
        if verbose: self._verbose(path, payload)

        return response
    
    
    def new_order(self):
        '''
        Uses v2 web socket API.
        Create a new order for a specified asset.
        '''
        pass
    
    
    def get_tickers(self, currency_pairs, use_cp_map = True):
        '''
        Get latest ticker for a specified currency pair.
        '''
        # format symbol for api
        symbol_str = ''
        for cp in currency_pairs:
            if use_cp_map:
                symbol_str += '%s,' % self.cp_map[cp]
            else:
                symbol_str += '%s,' % cp
        symbol_str = symbol_str[:-1]
        
        # call api and add results to df
        path = '/v2/tickers?symbols=%s' % symbol_str
        endpoint = self.BASE_URL + path
        ticker_df = pd.read_json(endpoint)
        ticker_cols = ['symbol', 'bid', 'bid_size', 'ask',
                       'ask_size', 'daily_change', 'daily_change_perc',
                       'last_price', 'volume', 'high', 'low'
                      ]
        ticker_df.columns = ticker_cols
        
        # add standard symbol to index
        if use_cp_map:
            ticker_df.index = currency_pairs
        else:
            ticker_df.index = [self.cp_map[cp] for cp in currency_pairs]
        
        return ticker_df
    
    
    def get_last_price(self, currency_pairs):
        '''
        Get a Series of last prices for a list of currencies
        '''
        return self.get_tickers(currency_pairs).last_price
    
    
    def get_balances(self, wallet = 'exchange', verbose = False):
        '''
        Get the current balances for each asset owned.
        
        Wallet Names:
         - Exchange: 'exchange'
         - Margin: 'trading'
         - Funding: 'deposit'
        
        '''
        # set path and payload
        path = '/v1/balances'
        payload = {
            "request": path,
            "nonce": self._nonce()
        }
        
        # post order
        response = self.v1_post(path, payload)
        if verbose: self._verbose(path = path, payload = payload)
        
        # add to df and filter to wallet type
        balances = pd.DataFrame(response)
        balances = balances[balances.type == wallet][['currency', 'amount', 'available']]
        balances.index = balances.currency.str.upper()
        balances = balances.drop('currency', 1)
        
        return balances
    
    
    def get_wallet_value(self, wallet = 'exchange'):
        '''
        Return the USD value of the specified wallet. Based on the
        last price each asset was traded at.
        '''
        # get current balances for specified wallet
        balances = self.get_balances(wallet = wallet).amount
        
        # return a balance of 0 if there are no assets in the wallet
        if len(balances) == 0 or balances.values.astype('float').sum() < 1:
            return 0.0
        
        # format symbol naming for bfx and joining
        portfolio_bfx_symbols = ['t' + asset.upper() + 'USD' for asset in balances.index]
        balances.index = portfolio_bfx_symbols
        
        # exception for not having USDT in balance
        try: portfolio_bfx_symbols.remove('tUSDUSD')
        except: pass

        # get the ticker for each pair
        last_price = self.get_tickers(portfolio_bfx_symbols, use_cp_map = False)[['symbol', 'last_price']].copy()
        
        # join data
        last_price.index = last_price.symbol
        last_price = last_price.drop('symbol', 1)
        last_price['balances'] = balances
        
        # calc value of crypto holdings
        crypto_value = last_price.last_price.astype('float') * last_price.balances.astype('float')
        
        # and then add tether (it's dropped when joining with last_price so you have to add it here/now)
        try: wallet_value = float(crypto_value.sum() + float(balances['tUSDUSD']))
        except: wallet_value = float(crypto_value.sum())
        
        return wallet_value
    
    
    def get_account_value(self):
        '''
        Return the total USDT value of the account
        '''
        wallet_types = {'exchange': 'exchange', 'margin': 'trading', 'funding': 'deposit'}
        account_values = {}
        for k in wallet_types:
            print('Fetching', k)
            account_values[k] = float(self.get_wallet_value(wallet_types[k]))
        
        account_values = pd.DataFrame([account_values])
        account_values['total'] = float(account_values.values.sum())
        account_values = account_values.T.copy()
        account_values.columns = ['USD']
        
        return account_values
            
    
    def transfer_between_wallets(self, amount, currency, from_wallet, to_wallet, verbose = False):
        '''
        Transfer funds from one wallet to another (i.e. Funding to Margin)
        Wallet types: 'exchange', 'trading', 'deposit'
        
        PAYLOAD EXAMPLE:
        amount: "1.0"
        currency: "BTC"
        walletfrom: "trading"
        walletto: "exchange"
        
        '''
        # set path and build payload
        path = '/v1/transfer'
        payload = {
            "request": path,
            "nonce": self._nonce(),
            "amount": amount,
            "currency": currency,
            "walletfrom": from_wallet,
            "walletto": to_wallet
        }
        
        # post transfer
        response = self.v1_post(path, payload)
        #if verbose: self._verbose(path, payload)
        
        print(response)
        return None



#############
#
# Actual trader which specifically handles the balancing of the portfolio
#
########

class Trader(BFXClient):
    
    def __init__(self, account = 'p', ks_path = 'bfx_utils.csv'):

        # set account
        print('Account:', account)
        u = pd.read_csv('bfx_utils.csv')
        u.index = u['type']
        u = u.drop('type', 1)
        ks_dict = u[account].to_dict()
        key, secret = ks_dict['k'], ks_dict['s']
        
        super(Trader, self).__init__(key, secret)
        
        # # abnormal tickers that are shortened by bfx
        # self.abnormal_tickers = {
        #     'DASH': 'DSH',
        #     'IOTA': 'IOT'
        # }

        # map cp for easy indexing
        self.abnormal_tickers = Mapping()
        self.abnormal_tickers['DASH'] = 'DSH'
        self.abnormal_tickers['IOTA'] = 'IOT'

    
    # a somewhat specific helper to convert a dict with currency
    # pairs as keys into a dict with the *BFX* ticker symbol
    def _pair_dict_to_ticker_dict(self, pair_dict, ext_ticker_map = {}):

        # edit keys in target balance so that they match the index of current balance
        for k in pair_dict:
            pair_dict[k.replace('USDT_', '')] = pair_dict.pop(k)

        # some symbols are greater than three chars and bfx shortens them, fix that here :)
        if len(ext_ticker_map) > 0:
            for k in ext_ticker_map:
                pair_dict[ext_ticker_map[k]] = pair_dict.pop(k)

        return pair_dict

    # add buffer to small/zero weights
    def _non_zero_weights(self, weights, threshold = 0.00001):
    
        weights_dict = weights.to_dict()
        for k, v in weights_dict.items():
        	if v < threshold:
        		weights_dict[k] += threshold
        
        return pd.Series(weights_dict)

    def get_new_portfolio(self, capital, asset_weights, trading_fee = 0.003):
        '''
        capital: amount of capital to be invested
        asset_weights: Series; currency pair index, and weight / allocation per asset
        '''
        
        capital_per_asset = asset_weights * capital
        capital_per_asset *= (1 - trading_fee)
        last_price = self.get_last_price(asset_weights.index.tolist())

        # and get the quantity of each asset
        porfolio = capital_per_asset / last_price

        # return all :D
        return porfolio, capital_per_asset, last_price

    # calculate how much of each coin we need to buy / sell to balance portfolio
    def needed_to_balance(self, target_balance, additional_cp_mapping = {}):
        
        current_balance = self.get_balances()
        
        # check if all owned assets are available
        if (current_balance.amount.astype('float') -
            current_balance.available.astype('float')
           ).sum() > 0:
            print('Available Balance does not equal Total Balance. Please close Open Orders before proceeding.')
            return None

        # convert pairs into bfx-client-friendly symbols
        target_balance = self._pair_dict_to_ticker_dict(target_balance, additional_cp_mapping)

        # add to df
        current_balance['target_balance'] = pd.Series(target_balance)
        balances = current_balance.copy()
        balances = balances.astype('float')
        del current_balance, target_balance

        # add delta
        balances['assets_needed'] = (balances.target_balance - balances.available).round(4)

        return balances
    
    def calculate_rebalance(self, asset_weights):

        self.abnormal_tickers = {k: self.abnormal_tickers[k] for k in
                                 [t for t in self.abnormal_tickers if t in
                                  [cp.replace('USDT_', '') for cp in asset_weights.index.tolist()]
                                 ]
                                }
        
        # get the number of each coin needed and the amount of capital for each asset
        portfolio, capital_per_asset, last_price = self.get_new_portfolio(capital = self.get_wallet_value(),
                                                                          asset_weights = asset_weights)
        
        # get a df of assets needed and sort by cost
        assets_needed = self.needed_to_balance(target_balance = dict(portfolio.round(4).to_dict()),
                                               additional_cp_mapping = self.abnormal_tickers)
        
        # add to df
        assets_needed['price'] = pd.Series(self._pair_dict_to_ticker_dict(dict(last_price.to_dict()),
                                                                          self.abnormal_tickers))
        assets_needed['order_cost'] = assets_needed.assets_needed * assets_needed.price
        assets_needed = assets_needed.sort_values('order_cost')
        
        return assets_needed
    
    
    def rebalance_portfolio(self, asset_weights,
                            fill_order_premium = 0.0,     # a premium on price paid in order to get order filled quicker
                            order_minimum = 25,           # minimum order value (USD) to be submitted
                            order_attempts = 50,          # decreasing a maximum of ~5% from original amount (as default)
                            sleep_interval = 3,           # sleep duration between orders (ensures subsequent orders will go through because actual cost is lower than est cost)
                            print_api_response = False):
        
        # calculate what is needed per asset
        asset_weights = self._non_zero_weights(asset_weights).copy()
        asset_balance_df = self.calculate_rebalance(asset_weights).copy()

        # drop any orders that are for less than minimum
        asset_balance_df = asset_balance_df[abs(asset_balance_df.order_cost) >= order_minimum].copy()

        print('Balancing the following assets:', asset_balance_df.index.tolist())

        # loop through each currency and create an order
        for asset in asset_balance_df.index:
            
            print('Balancing', asset)
            
            a = asset_balance_df.loc[asset]
            pair = asset.lower() + 'usd'
            amount = str(abs(a.assets_needed))
            
            if a.assets_needed < 0:
                side = 'sell'
                price = str(a.price * (1 - fill_order_premium))
            
            if a.assets_needed > 0:
                side = 'buy'
                price = str(a.price * (1 + fill_order_premium))
            

            for i in range(order_attempts):

                r = self.new_order_v1(amount = amount,
                                      price = price,
                                      side = side,
                                      order_type = 'exchange limit',
                                      symbol = pair,
                                      exchange = 'bitfinex',
                                      verbose = False)
                
                try:
                    r['order_id']
                    print('Success!')
                    break
                
                except:
                    if float(amount)*float(price) < 100:
                        print(float(amount)*float(price), 'is less than min cost of 100, so this is going to break.')
                        break
                    print('Order was not completed, reducing quantity and trying again.')
                    amount = str(float(amount) * 0.999)
                    print('New Amount:', amount)
                    sleep(0.5)

            sleep(sleep_interval)

        print('\nSuccessfully balanced portfolio\n\n')


