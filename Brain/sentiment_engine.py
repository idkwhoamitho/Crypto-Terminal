from openbb import obb
from transformers import pipeline
import torch 


class SentimentEngine:
    def __init__(self):
        device = 0 if torch.cuda.is_available() else -1   
        self.fin_pipe = pipeline(
                    "text-classification", 
                    model="ProsusAI/finbert", 
                    return_all_scores=True, # This ensures you get the full distribution
                    device=device, # CPU
                    low_cpu_mem_usage=True 
                )
        self.crypt_pipe = pipeline(
            "text-classification",
            model="ElKulako/cryptobert",
            top_k=None,
            device=device,
            model_kwargs={"torch_dtype": torch.float16} if device == 0 else {}
        )

       
    
    def get_news(self,symbol,provider):
        news_data = obb.news.company(symbol=symbol,provider=provider,limit=10).to_df()
        headlines = news_data['title'].tolist()

        return headlines


    def predict_sentiment(self,text,w_fin=0.3,w_cryp=0.7):

        f_raw = self.fin_pipe(text)[0]
        c_raw = self.crypt_pipe(text)[0]

        f_score = self.get_standart_score(f_raw, "finbert")
        c_score = self.get_standart_score(c_raw, "cryptobert")
        

        combined = (f_score * w_fin) + (c_score * w_cryp)

        return float(combined)


    
    def get_standart_score(self,pipe_out,model_type="finbert"):
        if isinstance(pipe_out, dict):
            pipe_out = [pipe_out]
        scores = {item['label']: item['score'] for item in pipe_out}

        if model_type == "finbert":
            pos = scores.get('positive',0)
            neg = scores.get('negatives',0)

            return pos - neg 

        elif model_type == 'cryptobert':
            pos = scores.get('Bullish',scores.get('LABEL_1',0))
            neg = scores.get('Bearish',scores.get('LABEL_0',0)) 
            
            return pos - neg 

    
    
    




