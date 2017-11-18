import time

class Coin:

    coin_synonims = {
        "USDT":"USD"
    }

    coin_symbols = {
        "USD": "$",
        "BTC": "฿",
        "ETH": "Ξ",
        "LTC": "Ł"
    }

    def __init__(self, coin):
        self.coin = coin.upper()
        if self.coin in Coin.coin_synonims:
            self.coin = Coin.coin_synonims[self.coin]

        self.symbol = self.coin
        if self.coin in Coin.coin_symbols:
            self.symbol = Coin.coin_symbols[self.coin]

    def __hash__(self):
        return hash(self.coin)

    def __eq__(self, other):
        return self.coin == other.coin

    def __str__(self):
        return "[Coin:{}]".format(self.coin)

class Market:
    def __init__(self,base_coin : Coin, traded_coin : Coin,market_name=None ,exchange_name=None):

        self.base_coin = base_coin
        self.traded_coin = traded_coin
        self.market_name = market_name
        self.exchange_name = exchange_name

    def __hash__(self):
        return self.base_coin.__hash__() * self.traded_coin.__hash__()

    def __eq__(self, other):
        return (self.base_coin == other.base_coin and self.traded_coin == other.traded_coin) or \
               (self.base_coin == other.traded_coin and self.traded_coin == other.base_coin)

    def __str__(self):
        return "[Market {}-{} as {} at {}]".format(self.base_coin,self.traded_coin,self.market_name,self.exchange_name)

    def __repr__(self):
        return self.__str__()

    def __copy__(self):
        return Market(self.base_coin,self.traded_coin,self.market_name,self.exchange_name)

class Ticker:
    def __init__(self,market,ask,bid,last,timestamp=None,reversed=False):
        self.market = market

        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

        if reversed:
            self.ask = 1 / ask
            self.bid = 1 / bid
            self.last = 1 / last
            self.r_ask = ask
            self.r_bid = bid
            self.r_last = last
        else:
            self.ask  = ask
            self.bid  = bid
            self.last = last
            self.r_ask = 1 / ask
            self.r_bid = 1 / bid
            self.r_last = 1 / last

    def __str__(self):
        return "[Ticker ask:{} bid:{} last:{} market:{} timestamp:{}]".format(self.ask,self.bid,self.last,self.market,self.timestamp)

class OrderBookEntry:
    def __init__(self,market,side,quantity,rate):
        self.market = market
        self.side = side
        self.base_quantity   = quantity * rate
        self.traded_quantity = quantity
        self.rate = rate

    def __str__(self):
        return "[OrderBookEntry side:{} rate:{:8.08f} base_quantity {} {} traded_quantity {} {} market:{}"\
            .format(self.side,self.rate,self.base_quantity,self.market.base_coin.coin,self.traded_quantity,self.market.traded_coin.coin,self.market)

class OrderBook:

    def __init__(self,market,asks,bids,timestamp=None,full=False):
        self.market = market
        self.asks = asks
        self.bids = bids
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
        self.full = full

        self.deals = {
            "asks": self.asks,
            "bids": self.bids,
        }

    def cut(self,size):
        return OrderBook(self.market,self.asks[:size],self.bids[:size],self.timestamp,self.full)

    def __str__(self):
        return "[OrderBook asks:{} {} bids:{} {}]".format(len(self.asks),self.asks[0],len(self.bids),self.bids[0])

    def __repr__(self):
        return self.__str__()



