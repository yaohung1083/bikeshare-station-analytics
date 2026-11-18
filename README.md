# Bikeshare 站點活動查詢｜MVP V1.0

用 React 查詢 Capital Bikeshare 站點在指定時段的借出、歸還與淨借出量。預設範例是站點 `31600` 在 2025 年 1 月 14 日 08:00 至 09:00 的活動。頁面會顯示查詢中、結果或 HTTP／網路錯誤。

## 架構

```text
官方旅次 ZIP → import_trips.py → 本機 SQLite
                                    ↑ 唯讀查詢
React → Vite 開發代理 → FastAPI /stations/{station_id}/activity
```

## 資料來源與授權

- [Capital Bikeshare System Data](https://capitalbikeshare.com/system-data)
- [Capital Bikeshare Data License Agreement](https://capitalbikeshare.com/data-license-agreement)
- [2025 年 1 月官方 ZIP](https://s3.amazonaws.com/capitalbikeshare-data/202501-capitalbikeshare-tripdata.zip)

官方條款限制將資料作為獨立資料集重新散布。請從官方下載並在本機重建資料庫。作品集初版的公開範圍為程式碼與文件，原始 ZIP、SQLite、Notebook 與分析輸出留在本機。本專案是獨立作品，未經資料提供者背書。

## 本機安裝與資料匯入

以下指令適用於 macOS／Linux，請在專案根目錄執行。已使用 Python 3.12.1、Node.js 26.13.1 與 npm 11.20.0 驗證既有本機環境。建議使用相同版本重現。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-api.txt
npm --prefix frontend ci

mkdir -p data/raw
curl -fL 'https://s3.amazonaws.com/capitalbikeshare-data/202501-capitalbikeshare-tripdata.zip' \
  -o data/raw/202501-capitalbikeshare-tripdata.zip
.venv/bin/python import_trips.py --db data/bikeshare.sqlite3 \
  data/raw/202501-capitalbikeshare-tripdata.zip
```

SQLite 檔案由匯入腳本建立，API 以唯讀模式開啟它。由全新環境重跑安裝、下載、匯入的完整流程仍待驗證。

## 啟動前後端

在兩個終端機中分別從專案根目錄執行。

```sh
.venv/bin/python -B -m uvicorn app:app --host 127.0.0.1 --port 8000
```

```sh
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

瀏覽器開啟 [React 查詢頁](http://127.0.0.1:5173/) 或 [FastAPI 互動文件](http://127.0.0.1:8000/docs)。Vite 將 `/stations/` 轉送到 FastAPI。

## 建置與測試

```sh
npm --prefix frontend run build
.venv/bin/python -m pip install pytest==9.2.0 httpx==0.28.1
.venv/bin/python -B -m pytest -p no:cacheprovider -q test_station_practice.py
```

pytest 使用 TestClient 驗證 [獨立練習 API](station_practice.py)，包含站點、時間分界與錯誤回應。正式查詢路由目前以本機 HTTP 串接驗證，完整自動測試仍待補齊。前後端都啟動後，可經 Vite 代理查詢正式 API。

```sh
curl --fail-with-body 'http://127.0.0.1:5173/stations/31600/activity?start=2025-01-14T08%3A00%3A00&end=2025-01-14T09%3A00%3A00'
```

使用上述月檔時，預期回傳借出 `15`、歸還 `1`、淨借出 `14`。本機已驗證 Vite 建置、練習測試及正式路由經代理的 HTTP 200、422、503。瀏覽器操作仍待人工驗收。

## MVP 限制

- 範例資料為 2025 年 1 月旅次，查詢結果反映匯入的資料範圍與站點 ID 完整度。
- 起訖時間採資料集的本地時間，不帶時區偏移。區間包含起點，排除終點。
- 無匹配事件的計數為零，未知站點也可能回傳三個零值。無效時間回傳 HTTP 422，資料庫不可用回傳 HTTP 503。
- 淨借出等於借出減歸還。負數表示歸還較多，這些計數無法直接判斷即時庫存、缺車或調度原因。
- Vite 代理是本機開發設定。MVP 尚未部署。
