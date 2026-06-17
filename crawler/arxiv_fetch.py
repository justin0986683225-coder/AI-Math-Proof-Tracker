import arxiv
import pandas as pd
import re
import os
import time
import random
from datetime import datetime, timezone, timedelta

# ======================================
# 基本設定
# ======================================

DAYS_BACK = 14
TARGET_AMOUNT = 300  # 一次爬取數量（改小比較穩定）

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "database",
    "papers_raw.csv"
)

# ======================================
# 載入舊資料
# ======================================

if os.path.exists(DATABASE_PATH):

    old_df = pd.read_csv(DATABASE_PATH)

    existing_ids = set(
        old_df["arxiv_id"].astype(str)
    )

    print(
        f"✅ 已載入舊資料庫：{len(existing_ids)} 篇"
    )

else:

    old_df = pd.DataFrame()

    existing_ids = set()

    print("📝 建立新資料庫")

# ======================================
# 時間範圍
# ======================================

today = datetime.now(timezone.utc)

cutoff_date = today - timedelta(days=DAYS_BACK)

print(
    f"⏳ 搜尋範圍：{cutoff_date.date()} ~ {today.date()}"
)

# ======================================
# 搜尋設定
# ======================================

search = arxiv.Search(
    query="cat:math.*",
    max_results=TARGET_AMOUNT,
    sort_by=arxiv.SortCriterion.SubmittedDate
)

# 放慢腳步，減輕伺服器壓力
client = arxiv.Client(
    page_size=10,      # 一次只拿 10 篇（原本太多了）
    delay_seconds=10,  # 預設休息 10 秒
    num_retries=3      # 預設重試 3 次
)

records = []

print("\n🚀 開始執行改進版 arXiv 爬蟲...\n")

# ======================================
# 擷取論文（改用 next() 方式）
# ======================================

paper_generator = client.results(search)

max_attempts = 5  # 重試上限
attempt = 0       # 當前重試次數
paper_count = 0   # 已成功抓取的論文數

while paper_count < TARGET_AMOUNT:
    try:
        # 嘗試拿取下一篇論文
        paper = next(paper_generator)
        
        # ✅ 成功拿到一篇，重試次數歸零
        attempt = 0
        
        if paper.published < cutoff_date:
            print(f"\n🛑 已觸及 {DAYS_BACK} 天前的界線，停止抓取。")
            break

        arxiv_id = paper.entry_id.split("/")[-1]

        if arxiv_id in existing_ids:
            continue

        # -------------------------
        # 全部 Subjects
        # -------------------------

        all_subjects = "; ".join(
            paper.categories
        )

        # -------------------------
        # 所有 math.*
        # -------------------------

        math_categories = sorted(
            set(
                cat
                for cat in paper.categories
                if cat.startswith("math.")
            )
        )

        # 沒有數學分類直接跳過
        if len(math_categories) == 0:
            continue

        authors = ", ".join(
            author.name
            for author in paper.authors
        )

        records.append(
            {
                "arxiv_id": arxiv_id,

                "published":
                paper.published.strftime(
                    "%Y-%m-%d"
                ),

                "year":
                paper.published.year,

                "title":
                paper.title,

                "summary":
                paper.summary.replace(
                    "\n",
                    " "
                ),

                "authors":
                authors,

                "primary_category":
                paper.primary_category,

                "all_subjects":
                all_subjects,

                "math_categories":
                ";".join(math_categories),

                "url":
                paper.entry_id,

                "pdf_url":
                paper.pdf_url
            }
        )
        
        paper_count += 1
        
        # 每抓到 50 篇印出進度
        if paper_count % 50 == 0:
            print(f"  ✨ 已順利抓取 {paper_count} 篇新論文...")

    except StopIteration:
        # ✅ 已經抓完設定的數量
        print("\n✅ 已達設定的抓取上限。")
        break
        
    except Exception as e:
        # ⚠️ 攔截 Timeout 或其他網路錯誤，啟動指數退避
        attempt += 1
        
        if attempt > max_attempts:
            print(
                f"\n❌ 連續失敗超過 {max_attempts} 次，放棄本次抓取。"
            )
            print(f"最後錯誤：{e}")
            break
            
        # 計算等待時間：(2^attempt) * 10 + 隨機1~5秒
        wait_time = (2 ** attempt) * 10 + random.uniform(1, 5)
        
        print(
            f"⚠️ 伺服器繁忙 (連線失敗)！"
            f"啟動退避機制，等待 {wait_time:.1f} 秒後重試 "
            f"(第 {attempt}/{max_attempts} 次)..."
        )
        print(f"   錯誤詳情：{str(e)[:100]}")
        
        time.sleep(wait_time)
        # 重試時不 continue，而是回到 while 迴圈再試一次

# ======================================
# 儲存
# ======================================

new_df = pd.DataFrame(records)

print(
    f"\n📊 本次新增：{len(new_df)} 篇"
)

if len(new_df) > 0:

    final_df = pd.concat(
        [old_df, new_df],
        ignore_index=True
    )

    final_df = final_df.drop_duplicates(
        subset=["arxiv_id"]
    )

    final_df = final_df.sort_values(
        "published",
        ascending=False
    )

    try:
        final_df.to_csv(
            DATABASE_PATH,
            index=False,
            encoding="utf-8-sig"
        )

        print(
            f"💾 資料庫更新成功！總收錄：{len(final_df)} 篇"
        )

    except PermissionError:
        print(
            f"⚠️ 無法寫入 {DATABASE_PATH}，"
            f"檔案可能正被 Excel 或其他程式開啟"
        )
        # 存成備份檔
        backup_path = os.path.join(
            BASE_DIR,
            "database",
            "papers_raw_backup.csv"
        )
        final_df.to_csv(
            backup_path,
            index=False,
            encoding="utf-8-sig"
        )
        print(f"💾 資料已備份到：{backup_path}")

else:

    print("📭 沒有新增論文")

print("\n" + "="*50)
print("✨ 爬蟲任務完成！")
print("="*50)