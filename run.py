from main import StockPriceEngine
from ui import StockApp

def main():
    engine = StockPriceEngine()
    app = StockApp(engine)
    app.mainloop()

if __name__ == "__main__":
    main()
