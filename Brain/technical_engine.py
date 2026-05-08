import numpy as np
import pandas as pd
from scipy.optimize import minimize


class TechincalEngine:
    def __init__(self):
        self.df = None 

    def set_df(self,df):
        self.df = df

    def get_sma(self,N=30):
        if self.df is None or self.df.empty:
            return None
        
        return self.df['close'].rolling(window=N).mean()

    def get_MSE(self):
        price = self.df['close']
        SMA = sum(price)*1/len(price)

        return SMA 
    def get_EMA(self,alpha,N):
        price = self.df['close']
        if N > 0 :

            EMA = alpha * price[N]  + (1-alpha) * self.get_EMA(alpha,N)
            N-=1
        if N < 0:
            return EMA 
    
    def get_RSI(self,N=30):
        '''
        For calculating an RSI indicator which using close price
        N: How days for calculating the datasets default 30
        
        output
        RSI: float
        
        '''
        price_close = self.df['close'].iloc[-N:]
        delta = price_close.diff()

        gains = delta.where(delta > 0, 0)
        loss = -delta.where(-delta < 0, 0)
        
        up_avg = 1/N * np.sum(gains)
        down_avg = 1/N * np.sum(loss)

        RS = up_avg/down_avg

        if down_avg == 0:
            return 100.0
        if up_avg == 0:
            return 0.0

        RSI = 100 - (100/(1+RS))
        
        return RSI 
    
    def get_ATR(self,N=14):
        '''
        calculating the ATR indicator using 
        N: how many days for calculating the inde default 14

        Output:
        ATR: Float
        '''
        TRs = []
        for i in range(1,N+1):
            today_High_price = self.df['high'].iloc[-i]
            today_Low_price = self.df['low'].iloc[-i]
            yesterday_close = self.df['close'].iloc[-i-1]

            h_pc = abs(today_High_price- yesterday_close)
            l_pc = abs(today_Low_price - yesterday_close)

            tr = max((abs(today_High_price-today_Low_price),np.maximum(h_pc,l_pc)))
            TRs.append(tr)

        ATR = sum(TRs) / N

        return ATR
    
    def calculate_strat_return(self,df):
        df['sma'] = self.get_sma()
        df['sig_trend'] = np.where(df['close'] > df['sma'],1,-1)

        delta = df['close'].diff()
        gain = (delta.where(delta > 0,0)).rolling(window=30).mean()
        loss = (delta.where(delta < 0,0)).rolling(window=30).mean()

        rs = gain / loss

        df['rsi'] = 100 - (100 / (1 + rs))
        df['sig_mom'] = np.where(df['rsi'] > 50, 1, -1) 



        df['asset_ret'] = np.log(df['close']/df['close'].shift(1))

        df['ret_trend'] = df['sig_trend'].shift(1) * df['asset_ret']
        df['mom_trend'] = df['sig_mom'].shift(1) * df['asset_ret']

        result = df[['ret_trend', 'mom_trend']].dropna()

        if result.empty:
        # Return empty Series so the unpacking doesn't crash, 
        # or handle the logic in optimal_weight
            return pd.Series(dtype='float64'), pd.Series(dtype='float64')

        return df[['ret_trend', 'mom_trend']].dropna()