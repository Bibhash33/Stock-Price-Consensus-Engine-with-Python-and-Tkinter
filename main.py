import requests
import time
import statistics
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

# Set up basic logging for clear error reporting
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ---------------- CONFIG ---------------- #

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json"
}

REQUEST_TIMEOUT = 5
MIN_VALID_SOURCES = 1  # Increased for better reliability
MAX_PRICE_DEVIATION = 0.5  # % allowed deviation (Kept at 0.5%)

# Market Hours (Eastern Time, which is standard for US stock exchanges)
MARKET_OPEN_TIME = time.strptime("09:30:00", "%H:%M:%S").tm_hour
MARKET_CLOSE_TIME = time.strptime("16:00:00", "%H:%M:%S").tm_hour

# ---------------- UTILITIES ---------------- #

def utc_now() -> str:
    """Returns the current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()

def market_is_open() -> bool:
    """
    Checks if the US stock market is open (9:30 AM to 4:00 PM ET).
    Note: This is a basic check and ignores holidays/weekends.
    """
    # Define US Eastern Time (ET) offset as a rough estimate for market hours check
    # UTC-5 for EST, UTC-4 for EDT (currently assuming standard for simplicity)
    # A more robust solution would use a dedicated library like 'pytz'
    ET_OFFSET = timedelta(hours=-5) 
    
    now_et = datetime.now(timezone.utc) + ET_OFFSET
    current_hour = now_et.hour
    current_minute = now_et.minute

    # Check for market hours (9:30 to 16:00 ET)
    is_open = (current_hour > MARKET_OPEN_TIME or 
               (current_hour == MARKET_OPEN_TIME and current_minute >= 30)) and \
              current_hour < MARKET_CLOSE_TIME

    # Simple check to exclude weekends (Sat=5, Sun=6)
    is_weekend = now_et.weekday() >= 5
    
    return is_open and not is_weekend

# ---------------- SOURCE SCRAPERS ---------------- #

class PriceSource:
    """Base class for all price sources."""
    name: str

    def fetch(self, symbol: str) -> Optional[float]:
        raise NotImplementedError

class YahooSource(PriceSource):
    name = "YahooFinance"

    def fetch(self, symbol: str) -> Optional[float]:
        try:
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status() # Raise exception for 4xx or 5xx status codes
            
            # Check for empty result list (symbol not found)
            result = r.json()["quoteResponse"]["result"]
            if not result:
                logging.warning(f"{self.name}: Symbol {symbol} not found.")
                return None
                
            # Use 'postMarketPrice' or 'preMarketPrice' if available outside regular hours
            data = result[0]
            price = data.get("regularMarketPrice")

            # Fallback for market close: use the latest available price (if applicable)
            if price is None:
                price = data.get("postMarketPrice") or data.get("preMarketPrice")

            return float(price)
        except requests.exceptions.RequestException as e:
            logging.error(f"{self.name} Request Failed: {e}")
            return None
        except (KeyError, TypeError, IndexError) as e:
            logging.error(f"{self.name} Parsing Failed: {e}")
            return None
        except Exception:
            logging.error(f"{self.name} Unknown Error during fetch.")
            return None

class StooqSource(PriceSource):
    name = "Stooq"

    def fetch(self, symbol: str) -> Optional[float]:
        try:
            stooq_symbol = f"{symbol.upper()}.US"
            url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=json"

            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()

            json_data = r.json()

            # ✅ CORRECT KEY: "symbols"
            symbols = json_data.get("symbols")
            if not symbols:
                logging.warning(f"{self.name}: No symbols found for {symbol}")
                return None

            close_price = symbols[0].get("close")
            if close_price in (None, "N/A"):
                logging.warning(f"{self.name}: Close price unavailable for {symbol}")
                return None

            return float(close_price)

        except requests.exceptions.RequestException as e:
            logging.error(f"{self.name} Request Failed: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"{self.name} Parsing Failed: {e}")
            return None
        except Exception as e:
            logging.error(f"{self.name} Unknown Error: {e}")
            return None

# ---------------- VALIDATION ---------------- #

def is_valid_price(price: Optional[float]) -> bool:
    """Ensures price is a non-None, positive number."""
    return price is not None and price > 0

# ---------------- CONSENSUS ENGINE ---------------- #

def consensus_price(prices: List[float]) -> Optional[float]:
    """
    Calculates the consensus price by removing outliers.
    """
    if len(prices) < MIN_VALID_SOURCES:
        return None

    median_price = statistics.median(prices)
    
    # Filter out prices that deviate more than the MAX_PRICE_DEVIATION from the median
    filtered = [
        p for p in prices
        if abs(p - median_price) / median_price * 100 <= MAX_PRICE_DEVIATION
    ]

    # Re-check reliability after filtering outliers
    if len(filtered) < MIN_VALID_SOURCES:
        logging.warning(
            f"Consensus failed: Filtered sources ({len(filtered)}) are less than required ({MIN_VALID_SOURCES})."
        )
        return None

    # Calculate the mean of the remaining reliable prices
    return round(statistics.mean(filtered), 2)

# ---------------- CONFIDENCE SCORING ---------------- #

def confidence_score(valid_count: int, total_sources: int, final_price_exists: bool) -> float:
    """
    Calculates confidence based on the ratio of successful sources.
    Confidence should be zero if a consensus price could not be established.
    """
    if not final_price_exists:
        return 0.0

    # Base confidence is the ratio of successful sources
    base_confidence = valid_count / total_sources
    
    # Simple bonus for success, capped at 1.0
    return round(min(1.0, base_confidence + 0.1), 2)

# ---------------- CORE ENGINE ---------------- #

class StockPriceEngine:

    def __init__(self):
        # Using a list of instantiated sources
        self.sources = [
            YahooSource(),
            StooqSource()
        ]
        self.total_sources = len(self.sources)

    def fetch_price(self, symbol: str) -> Dict:
        
        # Determine market state based on current time
        market_state = "OPEN" if market_is_open() else "CLOSED"
        
        raw_prices = []
        source_map = {}
        valid_count = 0

        # --- Data Gathering Phase ---
        for source in self.sources:
            price = source.fetch(symbol)
            if is_valid_price(price):
                raw_prices.append(price)
                source_map[source.name] = price
                valid_count += 1
            else:
                 # Record failed sources for transparency
                 source_map[source.name] = "FAILED" 
            
            time.sleep(0.3)  # ethical pacing

        logging.info(f"Scraped prices for {symbol}: {raw_prices}")

        # --- Validation Phase 1: Source Count ---
        if valid_count < MIN_VALID_SOURCES:
            return self._error(
                "INSUFFICIENT_DATA",
                f"Requires {MIN_VALID_SOURCES} reliable sources, but only found {valid_count}",
                source_map=source_map
            )

        # --- Validation Phase 2: Consensus Check (Outlier Removal) ---
        final_price = consensus_price(raw_prices)

        if final_price is None:
            # This triggers if sources passed Phase 1 but failed the deviation check
            return self._error(
                "LOW_CONFIDENCE",
                f"Prices deviated by more than {MAX_PRICE_DEVIATION}%. Check raw prices.",
                source_map=source_map
            )

        # --- Success & Confidence Scoring ---
        confidence = confidence_score(valid_count, self.total_sources, final_price is not None)

        return {
            "symbol": symbol.upper(),
            "price": final_price,
            "confidence": confidence,
            "sources_used": list(k for k, v in source_map.items() if v != "FAILED"),
            "source_prices": source_map,
            "market_state": market_state,
            "scraped_at": utc_now(),
            "price_type": "LIVE"
        }

    def _error(self, code: str, message: str, source_map: Optional[Dict] = None) -> Dict:
        """Helper to create a standard error response."""
        return {
            "error": code,
            "message": message,
            "scraped_at": utc_now(),
            "source_prices": source_map if source_map else {}
        }

# ---------------- CLI ENTRY ---------------- #

if __name__ == "__main__":
    logging.info("--- Starting Price Engine Test ---")
    engine = StockPriceEngine()
    
    # Test a common ticker
    print("\n--- Fetching AAPL ---")
    result_aapl = engine.fetch_price("AAPL")
    import json
    print(json.dumps(result_aapl, indent=4))
    
    # Test an invalid ticker (should result in INSUFFICIENT_DATA or LOW_CONFIDENCE)
    print("\n--- Fetching BADDESIGNER ---")
    result_bad = engine.fetch_price("BADDESIGNER")
    print(json.dumps(result_bad, indent=4))
