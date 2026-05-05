## 🛠️ Requirements

- Python 3.10+
- See `requirements.txt` for package dependencies

## 🚀 Quick Start

Clone the repository:
```bash
git clone git@github.com:QJ-SB/quant_start.git
cd quant_start
```

Set up virtual environment and install dependencies:
```bash
python -m venv .venv
.\.venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt
```

Run the demo:
```bash
python ma_cross.py
```

The script will:
1. Fetch the past year's daily data of stock `000001` (Pingan Bank) from akshare
2. Cache the result locally as CSV (under `daily_data_cache/`)
3. Compute MA5 and MA20 moving averages
4. Detect golden cross and death cross signals
5. Generate a chart at `images/ma_cross_demo.png`

## 🧠 Core Logic

### Moving Average Cross Strategy

A **golden cross** occurs when the short-term MA crosses **above** the long-term MA — traditionally interpreted as a bullish signal. A **death cross** is the opposite.

The key insight: **a cross is a state change, not a state**. The detection compares today's relationship between MA5 and MA20 with yesterday's:

```python
df["golden_cross"] = (
    (short_ma > long_ma) &
    (short_ma.shift(1) <= long_ma.shift(1))
)
```

### Local Cache Layer

To decouple development from network dependency (especially across borders), the data fetching is wrapped in a cache layer:
- First run: fetches from akshare, saves to local CSV
- Subsequent runs: reads directly from CSV (no network needed)
- Use `force_refresh=True` to bypass cache

## ⚠️ Known Limitations

- **MA cross signals are weak indicators**. They generate frequent false signals in sideways markets and lag in trending markets. This project is for learning purposes — **do not use it for actual trading**.
- The data source `akshare` is suitable for personal research only. Production-grade quantitative systems use Wind, level-2 feeds, or proprietary data sources.
- Currently only supports a single stock at a time. Multi-stock and backtesting functionality are planned for future versions.

## 📝 License

MIT License (planned)

---

*This project is part of my learning journey into quantitative finance. Built in 2026.*