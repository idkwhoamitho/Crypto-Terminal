from openbb import obb 
from enum import Enum

class PriceType(Enum):
    CLOSE = 0
    OPEN = 1
    HIGH = 2
    LOW = 3
    VOLUME = 4

class Data:
    def __init__(self,symbol,price_provider,news_provider):
        self.price_provider = price_provider
        self.news_provider = news_provider
        self.symbol = symbol

    def get_news(self,symbol):
        try:
            news_data = obb.news.company(
                symbol=symbol,
                provider=self.news_provider,
                limit=10,
                sort="created",
                order="desc"
            ).to_df()
            # Kembalikan DataFrame utuh, jangan di-tolist() di sini
            return news_data 
        except Exception as e:
            print(f"Error fetching news: {e}")
            return None

    
    def get_historical_data(self,start_date,end_date,interval,price_type=PriceType.CLOSE):
        try:

            if start_date == None or end_date == None:
                historical = obb.crypto(self.symbol,interval='1h')

            else:
                historical = obb.crypto.historical(symbol= self.symbol,
                                                start_date=start_date,
                                                end_date=end_date,
                                                interval=interval)
                
            df_price = historical.to_df()
            mapping = {
                PriceType.CLOSE: 'close',
                PriceType.OPEN: 'open',
                PriceType.HIGH: 'high',
                PriceType.LOW: 'low',
                PriceType.VOLUME: 'volume'
            }
            if price_type not in mapping:
                raise ValueError(f"Invalid PriceType: {price_type}. Expected one of {list(mapping.keys())}")
            
            return df_price[mapping[price_type]]
         
            
        except Exception as e:
            print(f"[Error] Failed to fetch data for {self.symbol}: {e}")
            return None 