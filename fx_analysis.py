from pathlib import Path
import time
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

OUT = Path(__file__).resolve().parent / 'outputs'
OUT.mkdir(exist_ok=True)
SYMBOLS = {
    'EURUSD': ('EURUSD=X', 'USD per EUR'),
    'GBPUSD': ('GBPUSD=X', 'USD per GBP'),
    'USDJPY': ('JPY=X', 'JPY per USD'),
    'USDCNY': ('CNY=X', 'CNY per USD'),
    'GOLD_FUTURES': ('GC=F', 'USD per troy oz, front-month futures'),
    'US10Y_YIELD': ('^TNX', 'US 10-year Treasury yield, percent'),
}

def fetch(ticker):
    for attempt in range(2):
        try:
            data = yf.download(ticker, period='1y', interval='1d', auto_adjust=True,
                               progress=False, threads=False, timeout=15)
            if data is None or data.empty:
                raise ValueError('Empty response')
            close = data['Close']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = pd.to_numeric(close, errors='coerce').dropna()
            close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
            close = close[~close.index.duplicated(keep='last')].sort_index()
            if len(close) < 20:
                raise ValueError('Fewer than 20 observations')
            return close
        except Exception as exc:
            print(f'WARNING {ticker}: attempt {attempt+1} failed: {exc}')
            if attempt == 0:
                time.sleep(2)
    return None

def main():
    summaries = []
    for name, (ticker, units) in SYMBOLS.items():
        print(f'Fetching {name} ({ticker})...', flush=True)
        s = fetch(ticker)
        if s is None:
            summaries.append({'series':name, 'ticker':ticker, 'status':'FAILED', 'units':units})
            continue
        s.rename('value').to_csv(OUT / f'{name}_history.csv', index_label='date')
        last, first = float(s.iloc[-1]), float(s.iloc[0])
        change = (last / first - 1) * 100 if first else float('nan')
        summaries.append({'series':name, 'ticker':ticker, 'status':'OK', 'units':units,
                          'first_date':s.index[0].date().isoformat(),
                          'last_date':s.index[-1].date().isoformat(),
                          'observations':len(s), 'first_value':first,
                          'last_value':last, 'period_change_pct':change})
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(s.index, s.values, linewidth=1.5)
        ax.set_title(f'{name}: {units} | {s.index[0].date()} to {s.index[-1].date()}')
        ax.set_ylabel(units)
        ax.grid(alpha=0.25)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(OUT / f'{name}_trend.png', dpi=160)
        plt.close(fig)
        print(f'  OK: {len(s)} observations, latest {last:.4f} ({s.index[-1].date()})', flush=True)
    pd.DataFrame(summaries).to_csv(OUT / 'market_summary.csv', index=False)
    print(f'Finished. Outputs saved to: {OUT}')
    print('NOTE: Each series may have a different latest trading date. Gold is futures, not spot.')

if __name__ == '__main__':
    main()
