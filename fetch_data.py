"""
fetch_data.py — 抓取 ETF 歷史價格並寫入 data.json（只用 Python 內建模組，不需要 pip install）

用法（在放有 data.json 的資料夾執行）：
    python fetch_data.py

做了什麼：
1. 向 Yahoo Finance 公開的 chart 介面要每檔近 2 年的日收盤價
2. 抓得到的檔案就更新；抓不到的檔案保留 data.json 裡原本的資料
3. 寫回 data.json，網頁（index.html）會讀這個檔案

注意：
- 價格是各檔每日收盤價（未還原股利），不是逐筆即時報價。
- Yahoo 這個介面不是官方保證的服務，可能改版或限流；失敗時請看終端機訊息。
- 本程式為課堂報告示範，不是投資建議。
"""
import json
import pathlib
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = pathlib.Path(__file__).parent
OUT = HERE / "data.json"
TICKERS = {
    "0050": "0050.TW", "006208": "006208.TW", "VT": "VT",
    "00719B": "00719B.TWO", "00864B": "00864B.TWO", "00865B": "00865B.TW",
    "00856B": "00856B.TWO", "00720B": "00720B.TWO",
}
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=2y&interval=1d&includePrePost=false"
UA = {"User-Agent": "Mozilla/5.0 (compatible; class-project-fetch/1.0)"}


def fetch_one(sym, tries=3):
    last_err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(URL.format(sym=sym), headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.load(r)
            res = j["chart"]["result"][0]
            offset = res["meta"].get("gmtoffset", 0)
            ts = res["timestamp"]
            closes = res["indicators"]["quote"][0]["close"]
            dates, vals = [], []
            for t, c in zip(ts, closes):
                if c is None:
                    continue
                d = (datetime.fromtimestamp(t, timezone.utc) + timedelta(seconds=offset)).strftime("%Y-%m-%d")
                if dates and dates[-1] == d:      # 同一天只留最後一筆
                    vals[-1] = round(float(c), 4)
                else:
                    dates.append(d)
                    vals.append(round(float(c), 4))
            if len(vals) < 2:
                raise ValueError("資料筆數太少")
            return {"dates": dates, "close": vals, "currency": res["meta"].get("currency")}
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(last_err)


def main():
    data = {"series": {}}
    if OUT.exists():
        try:
            data = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    data.setdefault("series", {})
    ok, fail = [], []
    for code, sym in TICKERS.items():
        try:
            data["series"][code] = fetch_one(sym)
            ok.append(code)
            print(f"[成功] {code:7s} {sym:11s} {len(data['series'][code]['close'])} 筆，最新 {data['series'][code]['dates'][-1]}")
        except Exception as e:  # noqa: BLE001
            fail.append(code)
            print(f"[失敗] {code:7s} {sym:11s} {e}", file=sys.stderr)
        time.sleep(0.6)
    tw = timezone(timedelta(hours=8))
    if ok:
        data["updated"] = datetime.now(tw).strftime("%Y-%m-%d %H:%M:%S")
        data["source"] = "Yahoo Finance chart API（日收盤價，未還原股利）"
        data["failed"] = fail
        OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"\n已寫入 {OUT.name}（成功 {len(ok)} 檔，失敗 {len(fail)} 檔）")
    else:
        print("\n全部失敗，未改動 data.json。請檢查網路。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
