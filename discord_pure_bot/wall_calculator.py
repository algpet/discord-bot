from digicoins.entity import Coin,Market
from digicoins.queries import OrderBookQuery,TickerQuery,PublicClientQueryExecutor


class WallCommandInterpreter:

    def __init__(self):

        self.exchanges = ["GDAX","BITFINEX","BITTREX"]

        self.usd = Coin("USD")
        self.btc = Coin("BTC")
        self.eth = Coin("ETH")
        self.ltc = Coin("LTC")

        self.coin_default_markets = {
            "BTC": Market(self.usd, self.btc),
            "ETH": Market(self.usd,self.eth),
            "LTC": Market(self.usd,self.ltc)
        }
        self.market_default_exchanges = {
            Market(self.usd, self.btc):"BITFINEX",
            Market(self.usd, self.eth):"GDAX",
            Market(self.usd, self.ltc):"GDAX",
        }

    def get_params(self,command_params):
        command_params = [x.upper() for x in command_params]
        market = self.get_ticker_from_params(command_params)
        depth = self.get_depth_from_params(command_params)
        exchange = self.get_exchange_from_params(command_params,market)
        return OrderBookQuery(exchange, market, depth),TickerQuery(exchange,market)

    def is_help(self,command_params):
        if command_params[0].upper() == "HELP":
            return True

    def get_ticker_from_params(self,params):
        coin = params[0]
        if coin.find("-") > -1:
            c1 = coin.split("-")[0]
            c2 = coin.split("-")[1]
            market = Market(Coin(c1),Coin(c2))
        else:
            if coin in self.coin_default_markets:
                market = self.coin_default_markets[coin]
            else:
                market = Market(self.btc,Coin(coin))
        return market

    def get_depth_from_params(self,params):
        for param in params[1:]:
            try:
                depth = int(param)
            except Exception:
                continue

            if depth > 500:
                depth = 500
            if depth < 10:
                depth = 10
            return depth
        return 50

    def get_exchange_from_params(self,params,market):
        for param in params[1:]:
            if param in self.exchanges:
                return param

        if market in self.market_default_exchanges:
            return self.market_default_exchanges[market]
        return "BITTREX"

"""
print(123)
commandProcessor = WallQueryCommandProcessor()

tests = [["doge"], ["stArt"],['eth'],['ltc'],['btC'],['doge','125'],['btc','66'],['doge','gdax'],['ltc','bitfinex','60']]
for test in tests:
    print("command", test, commandProcessor.process(test))
print()
tests2 = [['btc-doge'],['start-btc'],['usd-btc'],['btc-usd'],['eth-usd'],['usD-ltc','55'],['eth-usd','bitfinex']]
for test in tests2:
    print("command", test, commandProcessor.process(test))
print()
tests3 = [['btc-eth']]
for test in tests3:
    print("command", test, commandProcessor.process(test))
quit()
"""


class WallCalculator:

    def __init__(self):
        self.publicClientQueryExecutor = PublicClientQueryExecutor()
        self.wallCommandInterpreter = WallCommandInterpreter()
        self.presets = {
            "top_book_limit":50,
            "wall_min_volume":0.04,
            "wall_max_total_volume":0.75,
            "wall_max_count":10
        }

    def walls(self,message):
        command = message.content.split(" ")[1:]

        if self.wallCommandInterpreter.is_help(command):
            return self.help()

        order_book_query,ticker_query = self.wallCommandInterpreter.get_params(command)
        order_book = self.publicClientQueryExecutor.get_order_book(order_book_query,cut=True)
        ticker = self.publicClientQueryExecutor.get_ticker(ticker_query)
        if order_book is not None and ticker is not None:
            model = self.calculate_walls_model(order_book,ticker)
            if model is not None:
                view = model.view()
                return view

    def calculate_walls_model(self, order_book,ticker):
        model = WallModel()
        model.book = order_book
        model.ticker = ticker
        model.is_usd = order_book.market.base_coin.coin == "USD" or order_book.market.traded_coin.coin == "USD"

        model.bid_grand_volume = sum(bid.traded_quantity for bid in order_book.bids)
        model.ask_grand_volume = sum(ask.traded_quantity for ask in order_book.asks)
        model.book_grand_volume = model.bid_grand_volume + model.ask_grand_volume

        model.bid_grand_volume_in_base_coin = model.bid_grand_volume * ticker.last
        model.ask_grand_volume_in_base_coin = model.ask_grand_volume * ticker.last

        model.resistance = 100 * model.ask_grand_volume / model.bid_grand_volume

        bookEntries = sorted(order_book.bids + order_book.asks,key=lambda orderBookEntry: orderBookEntry.traded_quantity, reverse=True)
        bookEntries = bookEntries[:self.presets["wall_max_count"]]
        total_wall_size = 0.0

        walls = []
        for orderBookEntry in bookEntries:
            wall_size = orderBookEntry.traded_quantity / model.book_grand_volume
            if wall_size < self.presets["wall_min_volume"]:
                break
            total_wall_size += wall_size
            walls.append(WallEntry(orderBookEntry,wall_size))
            if total_wall_size > self.presets["wall_max_total_volume"]:
                break

        model.walls = sorted(walls, key=lambda wallEntry: wallEntry.orderBookEntry.rate,reverse=True)
        return model

    def help(self):
        return '''```
 [HELP]
-------------------------------------------
To use the bot, use the following syntax:
!walls [coin] [number of orders] [exchange]
        ```'''

class WallEntry:
    def __init__(self,orderBookEntry,size):
        self.orderBookEntry = orderBookEntry
        self.size = size

class WallModel:

    def __init__(self):
        self.book = None
        self.ticker = None
        self.is_usd = None
        self.bid_grand_volume = None
        self.ask_grand_volume = None
        self.bid_grand_volume_in_base_coin = None
        self.ask_grand_volume_in_base_coin = None
        self.resistance = None
        self.book_grand_volume = None
        self.walls = None

        self.deal_des = {
            "asks": "In {} Asks",
            "bids": "In {} Bids"
        }
        self.strike_line = "======================================================"

    def view(self):

        message = "```\n"
        message += "[Wall report from {}]\n\n".format(self.book.market.exchange_name)
        if self.is_usd:
            message += "[Last Price]\n{}\n  {} {:2.02f}\n".format(self.strike_line,self.book.market.base_coin.symbol,self.ticker.last)
        else:
            message += "[Last Price]\n{}\n  {} {:2.08f}\n".format(self.strike_line,self.book.market.base_coin.symbol,self.ticker.last)

        for side in ["asks","bids"]:
            deal_title = self.deal_des[side].format(len(self.book.deals[side]))
            message += "\n[{}] {}\n{}\n" \
                .format(self.ticker.market.market_name, deal_title,self.strike_line)

            for wallEntry in self.walls:
                if wallEntry.orderBookEntry.side == side:
                    if self.is_usd:
                        message += "  {} {:8.02f}  -  {:12.02f} {} {}\n" \
                            .format(self.book.market.base_coin.symbol, wallEntry.orderBookEntry.rate, wallEntry.orderBookEntry.traded_quantity,
                                    self.book.market.traded_coin.coin, "█" * int(wallEntry.size * 100))
                    else:
                        message += "  {} {:8.08f}  -  {:8.02f} {} {}\n" \
                            .format(self.book.market.base_coin.symbol,wallEntry.orderBookEntry.rate, wallEntry.orderBookEntry.base_quantity,
                                    self.book.market.base_coin.coin, "█" * int(wallEntry.size * 100))
            message += "\n"

        if self.is_usd:
            resistance_params = (self.ask_grand_volume, self.book.market.traded_coin.coin,
                        self.bid_grand_volume, self.book.market.traded_coin.coin,
                        self.resistance)
        else:
            resistance_params = (self.ask_grand_volume_in_base_coin, self.book.market.base_coin.coin,
                        self.bid_grand_volume_in_base_coin, self.book.market.base_coin.coin,
                        self.resistance)
        message += "====> Summary : Total Resistance / Support : {:.02f} {} / {:.02f} {} === {:.02f}% Resistance\n"\
            .format(*resistance_params)
        message += "```"

        return message

"""

class Dummy:
    def __init__(self,content):
        self.content = content

wallCalc = WallCalculator()
wallCalc.walls(Dummy("walls btc bittrex"))

"""