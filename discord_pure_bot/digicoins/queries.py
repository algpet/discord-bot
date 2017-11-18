from digicoins.digicoinlib import BittrexPublicClient,BitfinexPublicClient,GdaxPublicClient

class OrderBookQuery:
    def __init__(self,exchange,market,depth):
        self.exchange = exchange
        self.market = market
        self.depth = depth

class TickerQuery:
    def __init__(self,exchange,market):
        self.exchange = exchange
        self.market = market


class PublicClientQueryExecutor:
    def __init__(self):
        self.clients = {
            "GDAX" : GdaxPublicClient(),
            "BITFINEX" : BitfinexPublicClient(),
            "BITTREX" : BittrexPublicClient()
        }

    def get_ticker(self,tickerQuery):
        return self.clients[tickerQuery.exchange].get_ticker(tickerQuery.market)

    def get_order_book(self, orderBookQuery,cut=False):
        orderBook = self.clients[orderBookQuery.exchange].get_order_book(orderBookQuery.market, orderBookQuery.depth)
        if orderBook is None:
            return None
        if cut:
            orderBook = orderBook.cut(orderBookQuery.depth)
        return orderBook