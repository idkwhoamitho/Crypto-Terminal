import sys
import os

# Adds the root directory (Quant-Terminal) to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Brain.optimizer_engine import OptimizerEngine
from Brain.trade_executor import TradeExecutor
# ... other imports
from openbb import obb
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label, Static, Digits
from textual.containers import Container, Vertical, Horizontal
from textual_plotext import PlotextPlot
from textual import work
from Brain.optimizer_engine import OptimizerEngine
from data.get_data import Data
from dotenv import load_dotenv
import pandas as pd

class QuantTerminalApp(App):
    # This CSS defines the "Bento Box" style layout
    CSS_PATH = "style.tcss"

    def __init__(self):
        super().__init__()
        load_dotenv()
        self.data = Data("BTC-USD",'yfinance','yfinance')
        self.optimizerEng = OptimizerEngine()
        self.api_key = os.getenv("BITGET_API_KEY")
        self.secret  = os.getenv("BITGET_PRIVATE_KEY")
        self.trade = TradeExecutor(self.api_key,self.secret,app_reference=self)
        

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            # --- ROW 1 ---
            # Top-Left: Large Chart Panel
            with Vertical(id="chart-section"):
                yield PlotextPlot(id="main-chart")
            
            # Top-Right: Small Live Price Panel
            with Vertical(id="price-section"):
                yield Static("BTC LIVE", id="label")
                yield Digits("0.00", id="price-box")
            
            # --- ROW 2 (Now a full-width container split into 3 parts) ---
            with Horizontal(id="bottom-row-container"):
                
                # Column 1: Signal & Sentiment (Left)
                with Vertical(id="data-sentiment-column"):
                    yield Static("SIGNAL & SENTIMENT", classes="section-title")
                    yield Static("Loading data...", id="sentiment-display")
                
                # Column 2: Portfolio Allocations & Logs (Middle -> NOW IN THE CENTER)
                with Vertical(id="portfolio-section"):
                    with Horizontal(id="portfolio-header"):
                        yield Label("PORTFOLIO DESIGNER", id="portfolio-title")
                        yield Label("Total Value: $0.00", id="total-portfolio-value")
                    
                    # Back to side-by-side columns since we have tons of width now!
                    with Horizontal(id="portfolio-body"):
                        with Vertical(id="weights-column"):
                            yield Label("Target Weights", classes="column-header")
                            yield Static("BTC-USD: 40.00%\nBNB-USD: 20.00%\nUSDT-USD: 40.00%", id="weights-display")
                        
                        with Vertical(id="execution-column"):
                            yield Label("Live Execution Log (BITGET)", classes="column-header")
                            yield Static("Awaiting trade signal...", id="execution-display")

                # Column 3: Placeholder/News box to fill the remaining Right Corner
                with Vertical(id="news-section"):
                    yield Static("SYSTEM METRICS", classes="section-title")
                    yield Static("All execution pathways nominal.", id="news-display")
        yield Footer()


    def on_mount(self) -> None:
        # 1. Jalankan semua update sekali sekarang juga!
        self.update_price()
        # self.update_news()
        self.background_update()
        # 2. Baru pasang jadwal intervalnya
        self.set_interval(2.0, self.update_price)
        self.set_interval(60.0, self.update_chart)
        # self.set_interval(120.0, self.update_news)
        self.set_interval(60.0, self.update_sentiments_data)
        self.set_interval(3600.0, self.update_weight)


    @work(thread=True)
    def background_update(self):
        self.update_weight()
        self.update_sentiments_data()
        self.update_chart() 


    def update_price(self) -> None:
        try:
            data = obb.crypto.price.historical(symbol="BTC-USD", provider='yfinance', limit=1).to_df()
            price = data['close'].iloc[-1]
            self.query_one("#price-box", Digits).update(f"{price:.2f}")
        except:
            pass

    def update_chart(self) -> None:
        try:
            data = obb.crypto.price.historical(symbol="BTC-USD", provider='yfinance', limit=30, interval="1m").to_df()
            plt = self.query_one("#main-chart", PlotextPlot).plt
            plt.clear_data()
            plt.plot(data['close'].values, color="green")
            plt.title("Real-time Analysis")
            plt.theme("dark")
            self.query_one("#main-chart").refresh()
        except:
            pass
        
    @work(thread=True)
    def update_sentiments_data(self) -> None:
        try:
            datas = self.optimizerEng.combine_data()
            
            if not datas:
                self.query_one("#sentiment-display", Static).update("[yellow]Waiting for market data...[/]")
                return

            # Building the full list
            output_segments = []
            for data in datas:
                sent_score = data['sentiment'] * 100
                signal_score = data['signal']
                
                # Formatting logic
                color_sent = "green" if sent_score > 55 else "yellow" if sent_score > 45 else "red"
                color_sig = "bright_green" if signal_score > 0.1 else "red" if signal_score < -0.1 else "white"
                
                # Use a clean box-style separator for the 10 symbols
                block = (
                    f"[b cyan]{data['symbol']:<8}[/]\n"
                    f" [dim]├─[/] Sentiments: [{color_sent}]{sent_score:>6.2f}%[/]\n"
                    f" [dim]└─[/] Signal:     [{color_sig}]{signal_score:>6.4f}[/]\n"
                    f"[dim]──────────────────────────────[/]"
                )
                output_segments.append(block)

            # Join all blocks with a newline and update
            full_text = "\n".join(output_segments)
            self.query_one("#sentiment-display", Static).update(full_text)

        except Exception as e:
            self.query_one("#sentiment-display", Static).update(f"[red]Update Error:[/] {e}")

    def update_news(self) -> None:
        try:
            news_df = self.data.get_news('BTC-USD') 
            
            # Jika news_df ternyata list (karena tolist() tadi), 
            # buat proteksi sederhana agar tidak error
            if isinstance(news_df, list):
                news_text = "\n\n".join([f"[yellow]•[/] {t}" for t in news_df])
            else:
                if news_df.empty:
                    news_text = "No news found."
                else:
                    # Ambil kolom 'title' dari OpenBB news
                    news_text = ""
                    for _, row in news_df.head(10).iterrows():
                        # OpenBB provider biasanya menggunakan 'title'
                        title = row.get('title') or "Untitled"
                        news_text += f"[yellow]•[/] {title}\n\n"
            
            self.query_one("#news-display", Static).update(news_text)

        except Exception as e:
            self.query_one("#news-display", Static).update(f"[red]News Error:[/] {str(e)}")

    def update_weight(self):
        try:
            combined_data = self.optimizerEng.combine_data()
            weights = self.optimizerEng.optimize(combined_data)

            weights_text = ""
            if not weights:
                weights_text = "No symbol found"
            else:
                for symbol,weight in weights.items():
                    if weight > 0:
                        percentage = weight * 100

                        color = "green" if percentage > 20 else "white"
                        weights_text += f"{symbol}: [{color}]{percentage:.2f}%[/]\n"

                        self.query_one("#weights-display", Static).update(weights_text)
                
            self.trade.Execute(weights=weights)


        except Exception as e:
             self.query_one("#portofolio", Static).update(f"[red]Portofolio Error:[/] {str(e)}")
    
    
            


if __name__ == "__main__":
    QuantTerminalApp().run()