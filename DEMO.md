# 使用合成資料啟動 Bikeshare

以下命令在專案根目錄執行，適用於 macOS／Linux。需要 Python 3.12 和可執行專案 Vite 版本的 Node.js／npm。若尚未安裝專案依賴：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-api.txt
npm --prefix frontend ci
```

## 產生資料並啟動

```sh
.venv/bin/python -B generate_demo_db.py
BIKESHARE_DB=demo.sqlite3 .venv/bin/python -B -m uvicorn app:app --host 127.0.0.1 --port 8000
```

產生器固定寫入 41 筆人工設計的合成旅次，旅次 ID 以 `synthetic-demo-` 開頭。輸出 `demo.sqlite3` 已被 Git 忽略。可用 `--output demo-run-2.sqlite3` 產生另一份相同資料。目標必須是父目錄已存在的新 `.sqlite3` 路徑。程式拒絕既有檔案、符號連結與保留檔名 `bikeshare.sqlite3`。

在第二個終端機啟動 React：

```sh
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

開啟 [React 頁面](http://127.0.0.1:5173/) 或 [FastAPI 文件](http://127.0.0.1:8000/docs)。

## 預期結果

以下數字均為合成資料。日期是 `2025-01-14`，借出與歸還依各自的時間統計。

| 站點 | 借出 | 歸還 | 淨借出 | 總活動量 | 失衡率 |
|---|---:|---:|---:|---:|---:|
| 31600 | 25 | 10 | +15 | 35 | 42.86% |
| 31601 | 8 | 25 | −17 | 33 | 51.52% |
| 31633 | 6 | 4 | +2 | 10 | 20.00% |

- 預設時段查詢 `31600` 的 `08:00–09:00` 會得到借出 12、歸還 5、淨借出 +7。
- 單站趨勢使用 `31600`、`2025-01-14`。00:00 有 1 次歸還，08:00 有 12 次借出與 5 次歸還，10:00 兩項皆為 0。次日 00:00，`31601` 有 1 次借出與 1 次歸還。
- 失衡排行榜用預設門檻 20，依序應為 `31601`、`31600`。改用門檻 1，`31633` 排第三。

```sh
curl -fsS 'http://127.0.0.1:5173/stations/31600/activity?start=2025-01-14T08:00:00&end=2025-01-14T09:00:00'
curl -fsS 'http://127.0.0.1:5173/stations/31600/hourly-activity?date=2025-01-14'
curl -fsS 'http://127.0.0.1:5173/stations/imbalance?date=2025-01-14&min_activity=20'
```

驗收後在兩個終端機按 Ctrl+C 停止服務。確認 `./demo.sqlite3` 是本次建立的合成資料庫後，可用 `rm -i -- ./demo.sqlite3` 清除，或保留它並用另一個輸出路徑重跑。
