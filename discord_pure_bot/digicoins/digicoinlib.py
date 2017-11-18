import digicoins.libs.bittrex_api_copy as bittrex
import gdax
import bitfinex
import copy
from datetime import datetime
from digicoins.entity import Coin,Market,Ticker,OrderBookEntry,OrderBook


class BasePublicClient:

    def __init__(self):
        self.name = None
        self.market_names = {}
        self.markets = {}
        self.__init_child__()
        self.cache_markets()

    def __init_child__(self):
        raise NotImplementedError

    def __read_markets__(self,market_method,response_validation,content_getter,market_checker,market_builder):
        response = market_method()
        if not response_validation(response):
            raise BaseException("Unable to init {} client".format(self.name))
        markets = content_getter(response)
        for market in markets:
            if not market_checker(market):
                continue

            market = market_builder(market)
            self.market_names[market] = market.market_name
            self.markets[market.market_name] = market

    def cache_markets(self):
        raise NotImplementedError

    def get_markets(self,filter=None):
        markets = {}
        for market,market_name in self.market_names.items():
            if filter is not None:
                if not filter(market):
                    continue
            markets[market] = self.market_names[market]
        return markets

    def __specify_market__(self,market):
        market_name = None
        if type(market) == Market:
            if market in self.market_names:
                market_name = self.market_names[market]
        if market_name is None:
            return None

        market = self.markets[self.market_names[market]]
        return copy.copy(market)

    def __get_ticker__(self, market,ticker_method,response_validation,content_getter,ticker_builder):

        market = self.__specify_market__(market)
        if market is None:
            return None
        response = ticker_method(market.market_name)
        if not response_validation(response):
            raise BaseException("Unable to get ticker {} from {}".format(market.market_name, self.name))

        ticker = content_getter(response)
        return ticker_builder(market,ticker)

    def get_ticker(self,market):
        raise NotImplementedError

    def __get_order_book__(self,market,depth,order_book_method,response_validation,ask_getter,bid_getter,book_entry_builder,timestamp_getter):
        market = self.__specify_market__(market)
        if market is None:
            return None
        response = order_book_method(market.market_name,depth)
        if not response_validation(response):
            raise BaseException("Unable to get order book {} from {}".format(market.market_name, self.name))

        raw_book = {
            "bids":bid_getter(response),
            "asks":ask_getter(response)
        }
        book = {
            "bids":[],
            "asks":[]
        }
        for side in raw_book:
            for raw_entry in raw_book[side]:
                orderBookEntry = book_entry_builder(market,side,raw_entry)

                book[side].append(orderBookEntry)

        orderBook = OrderBook(market,book["asks"],book["bids"],timestamp=timestamp_getter(response))

        return orderBook

    def get_order_book(self,market):
        raise NotImplementedError


class BittrexPublicClient(BasePublicClient):

    def __init__(self):
        super().__init__()

    def __init_child__(self):
        self.name = "Bittrex"
        self.client = bittrex.Bittrex('key', 'value')

    @staticmethod
    def __default_response_validator__(response):
        return response['success']

    @staticmethod
    def __default_content_getter__(response):
        return response['result']

    def cache_markets(self):
        self.__read_markets__(
            market_method=self.client.get_markets,
            response_validation=BittrexPublicClient.__default_response_validator__,
            content_getter=BittrexPublicClient.__default_content_getter__,
            market_checker=lambda market: market['IsActive'],
            market_builder=lambda market: Market(Coin(market['BaseCurrency']),Coin(market['MarketCurrency']),market['MarketName'],self.name),
        )

    def get_ticker(self,market):
        return self.__get_ticker__(
            market=market,
            ticker_method=self.client.get_ticker,
            response_validation=BittrexPublicClient.__default_response_validator__,
            content_getter=BittrexPublicClient.__default_content_getter__,
            ticker_builder= lambda market,ticker: Ticker(market,ticker['Ask'],ticker['Bid'],ticker['Last'])
        )

    def get_order_book(self,market,depth=50):
        return self.__get_order_book__(
            market=market,
            depth=depth,
            order_book_method=lambda market,depth:self.client.get_orderbook(market,depth_type="both"),
            response_validation=BittrexPublicClient.__default_response_validator__,
            ask_getter=lambda response: response['result']['sell'],
            bid_getter=lambda response:response['result']['buy'],
            book_entry_builder=lambda market,side,raw_entry : OrderBookEntry(market,side,raw_entry['Quantity'],raw_entry['Rate']),
            timestamp_getter=lambda response: None
        )


class GdaxPublicClient(BasePublicClient):

    def __init__(self):
        super().__init__()

    def __init_child__(self):
        self.name = "Gdax"
        self.client = gdax.PublicClient()

    def cache_markets(self):
        self.__read_markets__(
            market_method=self.client.get_products,
            response_validation=lambda response: type(response) == list,
            content_getter=lambda response: response,
            market_checker=lambda market: True,
            market_builder=lambda market: Market( Coin(market['quote_currency']),Coin(market['base_currency']),market['id'], self.name)
        )

    def get_ticker(self,market):
        return self.__get_ticker__(
            market=market,
            ticker_method=self.client.get_product_ticker,
            response_validation=lambda response: type(response) == dict,
            content_getter=lambda response: response,
            ticker_builder= lambda market,ticker: Ticker(market,float(ticker['ask']),float(ticker['bid']),float(ticker['price']),
                                    timestamp=datetime.strptime(ticker['time'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp())
        )

    def get_order_book(self,market,depth=50):
        return self.__get_order_book__(
            market=market,
            depth=depth,
            order_book_method=lambda market,depth:self.client.get_product_order_book(market,level=(3 if depth > 50 else 2)),
            response_validation=lambda response: type(response) == dict,
            ask_getter=lambda response: response['asks'],
            bid_getter=lambda response:response['bids'],
            book_entry_builder=lambda market,side,raw_entry : OrderBookEntry(market,side,float(raw_entry[1]),float(raw_entry[0])),
            timestamp_getter=lambda response: None
        )


class BitfinexClientExt(bitfinex.Client):
    def tickers(self):
        url = self.url_for("tickers")
        return self._get(url)

class BitfinexPublicClient(BasePublicClient):
    def __init__(self):
        super().__init__()

    def __init_child__(self):
        self.name = "Bitfinex"
        self.client = BitfinexClientExt()

    def cache_markets(self):
        self.__read_markets__(
            market_method=self.client.tickers,
            response_validation=lambda response: type(response) == list,
            content_getter=lambda response: response,
            market_checker=lambda market: True,
            market_builder=lambda market: Market(Coin(market['pair'][3:]),Coin(market['pair'][:3]),market['pair'],self.name)
        )

    def get_ticker(self,market):
        return self.__get_ticker__(
            market=market,
            ticker_method=self.client.ticker,
            response_validation=lambda response: type(response) == dict,
            content_getter=lambda response: response,
            ticker_builder= lambda market,ticker: Ticker(market,ticker['ask'],ticker['bid'],ticker['last_price'],timestamp=ticker['timestamp'])
        )

    def get_order_book(self,market,depth=50):
        return self.__get_order_book__(
            market=market,
            depth=depth,
            order_book_method=lambda market,depth:self.client.order_book(market,parameters={"limit_bids":depth,"limit_asks":depth}),
            response_validation=lambda response: type(response) == dict,
            ask_getter=lambda response: response['asks'],
            bid_getter=lambda response:response['bids'],
            book_entry_builder=lambda market,side,raw_entry : OrderBookEntry(market,side,raw_entry['amount'],raw_entry['price']),
            timestamp_getter=lambda response: response['bids'][0]['timestamp']
        )





