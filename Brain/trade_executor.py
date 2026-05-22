
import ccxt   


class TradeExecutor:
    def __init__(self,api_key,secret,app_reference):
        self.exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options':{
                'defaultType':'Spot'
            }
        })
        self.portofolio_total_value = 0
        self.buy = []
        self.sell = []
        self.app = app_reference

    def Execute(self, weights:dict,base_currenct="USDT"):
       try:
            execution_lines = []
            self.exchange.load_markets()
            balance = self.exchange.fetch_balance()
            total_usdt_balance = balance['total'].get(base_currenct,0.0)
            portofolio_total_value = total_usdt_balance

            current_position = {}
            prices = {}

            for symbol in weights.keys():
                trading_pair = f"{symbol}/{base_currenct}"
                if trading_pair not in self.exchange.markets:
                   continue
               
                ticker = self.exchange.tickers(trading_pair)
                amount_owned = ticker['last']
                current_position[symbol] = amount_owned

                self.portofolio_total_value += (amount_owned * prices[symbol])


            self.app.query_one("#total-portfolio-value").update(f"Total Value: ${self.portfolio_total_value:,.2f}")



            for symbol,weight in weights.items():
                trading_pair = f"{symbol}/{base_currenct}"
                if trading_pair not in self.exchange.markets:
                    continue

                current_price = prices[symbol]
                currwnt_qty = current_position.get(symbol,0.0)

                target_value = portofolio_total_value * weight
                current_value = currwnt_qty * current_price

                value_diff = target_value - current_value
                raw_trade_amount = abs(value_diff) / current_price
                preccission_amount = float(self.exchange.amount_to_precision(trading_pair,raw_trade_amount))

                if value_diff < 0:
                    self.sells.append((trading_pair,preccission_amount,symbol))
                elif value_diff > 0:
                    self.buys.append((trading_pair,preccission_amount,symbol))

            for trading_pair, amount, symbol in self.sells:
                if amount > 0:                     
                    try:
                        order = self.exchange.create_market_sell_order(trading_pair, amount)  
                        execution_lines.append(f"✅ SOLD {amount} {symbol} (ID: {order['id'][:8]})")                        
                    except Exception as e:
                        BaseException(f"[TradeExecutor] Failed to execute the sell({symbol}): {e}")
                
            for trading_pair, amount, symbol in self.buys:
                if amount > 0:                    
                    try:
                        order = self.exchange.create_market_buy_order(trading_pair, amount)    
                        execution_lines.append(f"✅ BOUGHT {amount} {symbol} (ID: {order['id'][:8]})")            
                    except Exception as e:
                        BaseException(f"[TradeExecutor] Failed to buy {symbol}: {e}")

            if execution_lines:
                log_output = "\n".join(execution_lines)
                self.app.query_one("#execution-display").update(log_output)
            else:
                self.app.query_one("#execution-display").update("Awaiting trade signal... (Portfolio Balanced)")

       except Exception as e:
           BaseException(f"[TradeExecutor] Something went wrong: {e}")

