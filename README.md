Stock Price Consensus Engine (Python)

A lightweight yet reliable Python-based stock price fetching system that collects data from multiple sources, validates it, removes outliers, and displays the final consensus price in a clean desktop UI built with Tkinter.

This project is designed to demonstrate **real-world data validation**, **error handling**, and **clean software architecture**, rather than just basic API usage.



Project Overview

Most stock price projects rely on a single data source, which can fail, lag, or return unreliable values.
This application solves that problem by using **multiple independent data sources** and calculating a **consensus price** based on statistical validation.

The engine and the UI are fully separated, making the project easy to maintain and extend.



Key Features

* Multi-source stock price fetching
* Source-level failure detection
* Outlier removal using median deviation
* Consensus price calculation
* Confidence score based on data reliability
* Clean Tkinter desktop interface
* Background threading for smooth UI performance
* Transparent error reporting



Project Structure

```
PyStocker/
│
├── main.py        # Core consensus engine & data logic
├── ui.py          # Tkinter user interface
├── run.py         # Entry point to launch the UI
├── README.txt     # Project documentation
```

---

Supported Data Sources

* Yahoo Finance (public endpoint)
* Stooq (US market data)

The system is designed to easily support additional sources in the future.

---

Python Version

* **Python 3.13+** recommended

---

Required Packages

Only essential third-party packages are used.

Install them using:

```
pip install requests
```

All other modules (`tkinter`, `threading`, `statistics`, `datetime`, `logging`) are part of the Python standard library.


How to Run the Project

1. Clone the repository
2. Navigate to the project folder
3. Run the application:

```
python run.py
```

4. Enter a valid US stock symbol
   Example:

```
AAPL
MSFT
IBM
```

---


Sample Output (UI)

* Consensus stock price
* Market status (Open / Closed)
* Confidence score
* Source-wise status
* Last checked timestamp

Errors are shown in a clean, readable format instead of raw JSON.



Error Handling

The engine intelligently handles:

* Invalid symbols
* Network failures
* Partial source failures
* Price deviation beyond allowed limits

If sufficient reliable data is not available, the system clearly reports the reason.



Why This Project Stands Out

* Focuses on **data reliability**, not just fetching
* Clean separation of engine and UI
* Enterprise-style validation and logging
* Recruiter and MNC-friendly architecture
* Easy to extend for web or API usage



Future Enhancements

* Add more data sources
* Support international exchanges
* Export results to CSV / Excel
* Web dashboard using Flask or FastAPI
* Symbol autocomplete and validation



Disclaimer

This project is for **educational and demonstration purposes only**.
It is not intended for real-time trading or financial decision-making.



Author

Developed by:- Bibhash Kumar Haldar | Freelancer
