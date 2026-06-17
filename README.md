# 📐 AI Math Proof Tracker

每週自動從 arXiv 爬取數學論文，依照 AI 與定理證明的相關程度分類，並產生視覺化圖表。

---

## 📁 專案結構

```
AI-Math-Proof-Tracker/
├── .github/
│   └── workflows/
│       └── weekly_tracker.yml   # GitHub Actions 自動排程
├── crawler/
│   └── arxiv_fetch.py           # 從 arXiv 爬取 math.* 論文
├── classifier/
│   └── paper_classifier.py      # LLM / 關鍵字分類器
├── analytics/
│   └── create_charts.py         # 產生圖表（含版本管理）
├── database/
│   ├── papers_raw.csv           # 爬蟲原始資料
│   ├── papers_filtered.csv      # 篩選 + 分類後的資料
│   └── charts/
│       ├── latest/              # 最新一次的圖表
│       └── 2026-06-17_100000/   # 歷史版本（保留最近 10 次）
└── requirements.txt
```

---

## 🏷️ 分類說明

| 類別 | 說明 | 例子 |
|------|------|------|
| **A** | AI 直接完成數學證明 | AlphaProof、DeepSeek-Prover |
| **B** | AI 協助人類完成證明 | LLM 輔助 Lean/Coq、數學推理研究 |
| **C** | AI 增強 Proof Assistant | 使用 LLM 加速定理求解、自動形式化 |

---

## 🚀 本地執行

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 爬取論文
python crawler/arxiv_fetch.py

# 3. 分類（可選：設定 Gemini API Key 使用 LLM 分類）
export GEMINI_API_KEY=your_key_here
python classifier/paper_classifier.py

# 4. 產生圖表
python analytics/create_charts.py
```

---

## ⚙️ GitHub Actions 自動化

每週一 UTC 00:00（台灣時間早上 8:00）自動執行完整流程，結果會自動 commit 回此 repo。

如需使用 Gemini LLM 分類，請在 GitHub → Settings → Secrets → Actions 新增：

```
GEMINI_API_KEY = your_gemini_api_key
```

不設定也沒關係，會自動降級為關鍵字規則分類。

---

## 📊 最新圖表

圖表存放於 `database/charts/latest/`，每次執行後自動更新。
