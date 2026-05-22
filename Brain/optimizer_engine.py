from pypfopt import EfficientFrontier, risk_models, expected_returns
from data.get_data import Data
import pandas as pd
from Brain.sentiment_engine import SentimentEngine
from Brain.technical_engine import TechincalEngine
import numpy as np
from scipy.optimize import minimize
from data import get_data
from openbb import obb


class OptimizerEngine:
    '''
    THE CLASS INPUT SHOULD BE JSON:
    {
        "Symbol" : "BTC",
        "Signal" : 0.5 (1 = strong buy, 0 = strong sell),
        "Sentiment" : 0.56
    }

    '''

    def __init__(self):
        self.sentiments_eng = SentimentEngine()
        self.technical = TechincalEngine()
        self.tickers = None
        self.prices = pd.DataFrame()
        

    def fetch_live_tickers(self,limit=5):
        """Mengambil top koin berdasarkan volume/mcap agar tidak hard-coded"""
        try:
            # Mengambil data harga terbaru untuk beberapa koin populer
            # Kamu bisa mengganti ini dengan fungsi screener jika tersedia di provider-mu
            symbols = obb.crypto.discovery.trending(provide='yfinance')
            
            # Opsi lain: Gunakan koin yang sedang 'trending' atau aktif di provider
            # Untuk sekarang, kita gunakan list yang divalidasi oleh API
            return symbols 
        except Exception:
            return ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "AVAX-USD", "DOT-USD","USDT-USD"] # Fallback jika API mati
        



  
    def get_best_coin(self):
        '''
        returns:
        [{
            'Symbol' = 'BTC',
        }]
        '''
        self.tickers = self.fetch_live_tickers()

        rank = []
        for tick in self.tickers:
            hist = obb.crypto.price.historical(tick,provider='yfinance',limit=1).to_df()

            if not hist.empty and len(hist) >= 2:
                if hist['volume'].iloc[-1] > 100000:
                    rank.append({
                        "symbol":tick,
                    })
        
        return rank
    

    def objective(self,weights,returns):
        port_return = np.sum(returns.mean() * weights)*252
        port_vol = np.sqrt(np.dot(weights.T,np.dot(returns.cov() *252,weights)))
        if port_vol == 1e-9:
            return 0
        
        sharpe = port_return/port_vol
        return -sharpe
    
    def optimal_weight(self,df):
        data = self.technical.calculate_strat_return(df)
        data = data.rename(columns={'ret_trend': 'trend', 'mom_trend': 'momentum'})

        data = data.fillna(0)
        

        if len(data) < 5: # Not enough data to optimize
            return np.array([0.5, 0.5])
        
        init_guess = [0.5,0.5]
        bounds = ((0,1),(0,1))

        constraint = ({
            'type':'eq',
            'fun': lambda x : np.sum(x) - 1.0
        })
        result = minimize(
            self.objective,
            init_guess,
            args=(data,),
            method='SLSQP',
            bounds=bounds,
            constraints=constraint
        )
        
        return result.x
    
    def combine_signal(self,current_price, prices_df):
        weights = self.optimal_weight(prices_df)

        strat_df = self.technical.calculate_strat_return(prices_df)

        latest_signal = strat_df.iloc[-1]

        combined = (weights[0] * latest_signal['ret_trend']) + (weights[1] * latest_signal['mom_trend'])

        return combined 
    
    
    def combine_data(self):
        combine_datas = []
        all_prices = {}     # Untuk menampung harga semua koin
        ranks = self.get_best_coin()


        for rank in ranks:
            news = obb.news.company(symbol=rank['symbol'],provider='yfinance').to_df()
            prices_df = obb.crypto.price.historical(symbol=rank['symbol'],provider='yfinance').to_df()
            
            prices_df = prices_df.dropna()

            self.technical.set_df(prices_df)

            sentiments_score = 0
            current_price = prices_df['close'].iloc[-1]
            signal = self.combine_signal(current_price, prices_df)           
            sent_score = []
            titles = news['title'].dropna().tolist()

            for title in titles:
                score = self.sentiments_eng.predict_sentiment(title) 
                sent_score.append(score)

            if len(sent_score) > 0:
                sentiments_score = sum(sent_score) / len(sent_score)
            else:
                sentiments_score = 0            


            all_prices[rank['symbol']] = prices_df['close']

            combine_datas.append({

                'symbol' : rank['symbol'],
                'sentiment': sentiments_score,
                'signal' : signal
            })
        self.prices = pd.DataFrame(all_prices).dropna()
        return combine_datas            



    def optimize(self, combined_data,risk_free_rate=0.02):
        try:
            if self.prices.empty:
                raise ValueError("Price DataFrame is empty")

            mu = expected_returns.mean_historical_return(self.prices)
            s = risk_models.sample_cov(self.prices,frequency=365)
            
            
            for item in combined_data:
                symbol = item['symbol']
                if symbol in mu.index:
                    sent_val = float(item['sentiment'])
                    sig_val = float(item['signal'])
                    
                    sentiment_tilt = (sent_val - 0.5) * 0.01
                    signal_tilt = sig_val * 0.5

                    mu[symbol] += (sentiment_tilt + signal_tilt)
                    
            if (mu <= risk_free_rate).all():
                    ef = EfficientFrontier(mu, s, weight_bounds=(0, 0.4))
                    if "BTC" in mu.index:
                        btc_index = mu.index.get_loc("BTC")
                        ef.add_constraint(lambda w: w[btc_index] >= 0.10)
                    
                    ef.min_volatility()
                    return dict(ef.clean_weights())

            ef = EfficientFrontier(mu, s, weight_bounds=(0, 0.4))

            if "BTC" in mu.index:
                btc_index = mu.index.get_loc("BTC")
                # This creates a constraint: Weight of BTC >= 10%
                ef.add_constraint(lambda w: w[btc_index] >= 0.10)

            max_return = mu.max()
            min_return = mu.min()

            dynamic_target = min_return + 0.7 * (max_return - min_return)
            dynamic_target = max(0, dynamic_target)
            
            try:
                ef.efficient_return(target_return=dynamic_target)
            except:
            # Fallback: If target is too aggressive for the solver, 
            # find the Max Sharpe portfolio instead.
                ef = EfficientFrontier(mu, s, weight_bounds=(0, 0.4))
                ef.max_sharpe()
            

            cleaned_weight = ef.clean_weights()
            return dict(cleaned_weight)

        except Exception as e:
            # This is why you see 12.5% (1/8)
            # It hits this line whenever the math above fails
            print(f"Optimizer Error: {e}") 
            num_assets = len(combined_data) if combined_data else 1
            raise ValueError(f"portofoilo {str(e)}")
    


