import tkinter as tk
from tkinter import ttk
import threading
import json
import logging
# --- 1. Import the StockPriceEngine from main.py ---
try:
    from main import StockPriceEngine  
except ImportError:
    # Fallback/Error handling if main.py is missing or named differently
    logging.error("Could not import StockPriceEngine. Make sure your consensus logic is in 'main.py'.")
    StockPriceEngine = None

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ---------------- UI APP ---------------- #

class StockApp(tk.Tk):
    def __init__(self, engine):
        super().__init__()

        # Ensure the engine was successfully imported/passed
        if engine is None:
            raise RuntimeError("StockPriceEngine is required but was not initialized.")
            
        self.engine = engine
        self.title("Stock Price Consensus Engine")
        self.geometry("600x400")
        self.minsize(500, 350)

        self._configure_grid()
        self._create_widgets()

    def _configure_grid(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def _create_widgets(self):
        # --- Top Input Frame ---
        input_frame = ttk.Frame(self, padding=10)
        input_frame.grid(row=0, column=0, sticky="ew")
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Stock Symbol:").grid(row=0, column=0, sticky="w")
        self.symbol_entry = ttk.Entry(input_frame)
        self.symbol_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.symbol_entry.insert(0, "AAPL")

        # Disable button while fetching
        self.fetch_btn = ttk.Button(input_frame, text="Fetch Price", command=self.fetch_price)
        self.fetch_btn.grid(row=0, column=2)

        # --- Output Frame ---
        output_frame = ttk.LabelFrame(self, text="Result (JSON Output)", padding=10)
        output_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(
            output_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 11)
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(output_frame, command=self.output_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.output_text["yscrollcommand"] = scrollbar.set

        # --- Status Bar ---
        self.status = ttk.Label(self, text="Ready", anchor="w")
        self.status.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

    # ---------------- LOGIC ---------------- #

    def fetch_price(self):
        symbol = self.symbol_entry.get().strip().upper()
        if not symbol:
            self._update_status("Please enter a stock symbol.", "warning")
            return

        self.fetch_btn.config(state="disabled") # Disable button during fetch
        self._update_status(f"Fetching price for {symbol}...", "info")
        
        # Start the network request in a separate thread
        threading.Thread(target=self._fetch_async, args=(symbol,), daemon=True).start()

    def _fetch_async(self, symbol):
        """Runs the blocking I/O operation (API calls) in a background thread."""
        try:
            # --- 2. Call the Engine's method directly ---
            result = self.engine.fetch_price(symbol)
        except Exception as e:
            # Catch any unexpected errors from the engine itself
            result = {"error": "ENGINE_EXCEPTION", "message": str(e), "scraped_at": self.engine.utc_now()}
            logging.error(f"Engine Exception: {e}")

        # Use self.after to safely pass the result back to the main GUI thread
        self.after(0, self._display_result, result)

    def _display_result(self, result):
        """Called on the main thread to update the UI."""

        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)

        # ---------- ERROR DISPLAY ----------
        if "error" in result:
            display = (
                "STATUS : DATA UNAVAILABLE\n"
                "----------------------------------\n"
                f"Error Code   : {result.get('error')}\n"
                f"Message      : {result.get('message')}\n"
                f"Checked At   : {result.get('scraped_at')}\n\n"
                "Source Status:\n"
            )

            for src, status in result.get("source_prices", {}).items():
                display += f"  • {src:<15} : {status}\n"

            self._update_status("Error – No reliable market data", "error")

        # ---------- SUCCESS DISPLAY ----------
        else:
            display = (
                "STATUS : PRICE FETCHED SUCCESSFULLY\n"
                "----------------------------------\n"
                f"Symbol        : {result.get('symbol')}\n"
                f"Price         : {result.get('price')}\n"
                f"Confidence    : {int(result.get('confidence', 0) * 100)}%\n"
                f"Market State  : {result.get('market_state')}\n"
                f"Price Type    : {result.get('price_type')}\n"
                f"Fetched At    : {result.get('scraped_at')}\n\n"
                "Sources:\n"
            )

            for src, price in result.get("source_prices", {}).items():
                display += f"  • {src:<15} : {price}\n"

            self._update_status(
                f"Success | {result.get('symbol')} @ {result.get('price')}",
                "success"
            )

        self.output_text.insert(tk.END, display)
        self.output_text.config(state="disabled")
        self.fetch_btn.config(state="normal")

    # Helper function remains the same:
    def _update_output(self, message):
        """Helper to safely write to the disabled Text widget."""
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, message)
        self.output_text.config(state="disabled")

    def _update_status(self, message, level="info"):
        """Helper to update the status bar with color indication (optional)."""
        color_map = {"info": "black", "success": "green", "error": "red", "warning": "orange"}
        self.status.config(text=message, foreground=color_map.get(level, "black"))
