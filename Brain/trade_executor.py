
import ccxt   


class TradeExecutor:
    def __init__(self,api_key,secret):
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options':{
                'defaultType':'Spot'
            }
        })

    def Execute(self, weights:dict,base_currenct="USDT"):
        self.exchange.load_markets()

        balance = self.exchange.fetch_balance()

        total_base = balance['total'].get(base_currenct)

        for symbol,weight in weights.items():
            trading_pair = f"{symbol}/{base_currenct}"

            ticker = self.exchange.fetch_ticker(trading_pair)
            price = ticker['last']

            target_value = total_base * weight 
            raw_amount = target_value / price 

            amount = float(self.exchange.amount_to_precision(trading_pair,raw_amount))

            if amount > 0:
                try:
                    order = self.exchange.create_market_buy_order(trading_pair,amount)
                except Exception as e:
                    ValueError("Error while executing order")

