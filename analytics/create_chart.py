import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
import shutil
from datetime import datetime

# ======================================
# 基本設定
# ======================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

FILTERED_DB_PATH = os.path.join(
    BASE_DIR, "database", "papers_filtered.csv"
)

CHARTS_BASE_DIR = os.path.join(
    BASE_DIR, "database", "charts"
)

KEEP_RUNS = 10  # 保留最近幾次的資料夾

# ======================================
# 版本資料夾管理
# ======================================

def setup_run_dirs(base_dir, keep_runs=10):
    """
    建立本次執行的資料夾，更新 latest/，並刪除舊資料夾。
    回傳本次輸出目錄路徑。
    """

    os.makedirs(base_dir, exist_ok=True)

    # 本次執行的資料夾名稱，格式：2026-06-17_153045
    run_name = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = os.path.join(base_dir, run_name)
    os.makedirs(run_dir, exist_ok=True)
    print(f"📁 本次輸出目錄：{run_dir}")

    return run_dir, run_name


def update_latest(base_dir, run_dir):
    """把 latest/ 更新為本次結果的副本"""

    latest_dir = os.path.join(base_dir, "latest")

    # 先刪除舊的 latest/
    if os.path.exists(latest_dir):
        shutil.rmtree(latest_dir)

    shutil.copytree(run_dir, latest_dir)
    print(f"🔗 已更新 latest/ → {run_dir}")


def cleanup_old_runs(base_dir, keep_runs=10):
    """刪除超過 keep_runs 次的舊資料夾（排除 latest/）"""

    # 找出所有日期格式的資料夾（格式：YYYY-MM-DD_HHMMSS）
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}$")

    run_dirs = sorted([
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
        and date_pattern.match(d)
    ])

    # 超出保留數量的舊資料夾
    to_delete = run_dirs[:-keep_runs] if len(run_dirs) > keep_runs else []

    for old_dir in to_delete:
        old_path = os.path.join(base_dir, old_dir)
        shutil.rmtree(old_path)
        print(f"🗑️  已刪除舊資料夾：{old_dir}")

    if not to_delete:
        print(f"✅ 目前共 {len(run_dirs)} 次記錄，無需清理")


# ======================================
# 字體設定
# ======================================

import matplotlib.font_manager as fm

available_fonts = [f.name for f in fm.fontManager.ttflist]

font_options = [
    'Microsoft JhengHei',
    'SimHei',
    'Microsoft YaHei',
    'STHeiti',
    'WenQuanYi Micro Hei',
    'DejaVu Sans'
]

selected_font = 'DejaVu Sans'
for font in font_options:
    if font in available_fonts:
        selected_font = font
        print(f"✅ 偵測到字體：{font}")
        break

plt.rcParams['font.sans-serif'] = [selected_font, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", font=selected_font)

# ======================================
# 讀取資料
# ======================================

print("\n🎨 開始生成融合圖表...\n")

if not os.path.exists(FILTERED_DB_PATH):
    print(f"❌ 找不到必要的資料檔：{FILTERED_DB_PATH}")
    exit(1)

# ✅ filtered_df 本身已包含所有欄位，直接使用
df = pd.read_csv(FILTERED_DB_PATH)
filtered_df = df.copy()

print(f"📂 已讀取篩選資料：{len(df)} 篇\n")

# ======================================
# 建立本次執行目錄
# ======================================

run_dir, run_name = setup_run_dirs(CHARTS_BASE_DIR, KEEP_RUNS)

# ======================================
# 提取 math 分類
# ======================================

records = []

math_pattern = r"(math\.[A-Z]+)"

for _, row in df.iterrows():
    year = row.get('year')
    category = row.get('category')  # A/B/C

    if pd.notna(row.get('math_categories')):
        math_cats_str = str(row['math_categories'])
        math_cats = re.findall(math_pattern, math_cats_str)
        math_cats = sorted(set(math_cats))
    else:
        math_cats = []

    if not math_cats and pd.notna(row.get('primary_category')):
        primary = str(row.get('primary_category')).strip()
        if primary.startswith('math.'):
            math_cats = [primary]

    for math_cat in math_cats:
        records.append({
            'Year': year,
            'Math_Category': math_cat,
            'AI_Category': category,
            'ArxivID': row.get('arxiv_id')
        })

if records:
    math_df = pd.DataFrame(records)
    print(f"✅ 成功提取 {len(math_df):,} 筆 math 分類資料")
    print(f"   涵蓋 {math_df['Math_Category'].nunique()} 種 math 分類\n")
else:
    print("⚠️ 未找到任何 math 分類資料，將只顯示 A/B/C 分類圖表\n")
    math_df = None

# ======================================
# 分類標籤
# ======================================

category_labels_zh = {
    'A': 'A - AI直接完成證明',
    'B': 'B - AI協助人類',
    'C': 'C - AI增強工具'
}

category_colors = {
    'A': '#FF6B6B',
    'B': '#4ECDC4',
    'C': '#45B7D1'
}

# ======================================
# 圖 1：A/B/C 分類分布
# ======================================

print("生成圖 1：A/B/C 分類分布...")

fig, ax = plt.subplots(figsize=(10, 6))

category_count = filtered_df['category'].value_counts().sort_index()

labels = [category_labels_zh.get(cat, cat) for cat in category_count.index]
colors = [category_colors.get(cat, '#999999') for cat in category_count.index]

bars = ax.bar(
    range(len(category_count)),
    category_count.values,
    color=colors,
    edgecolor='black',
    linewidth=1.5,
    alpha=0.8
)

for bar in bars:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width()/2.,
        height,
        f'{int(height)}',
        ha='center',
        va='bottom',
        fontsize=12,
        fontweight='bold'
    )

ax.set_xticks(range(len(category_count)))
ax.set_xticklabels(labels, fontsize=11)
ax.set_ylabel('論文數量', fontsize=12, fontweight='bold')
ax.set_title('AI 數學證明論文 - A/B/C 分類分布', fontsize=14, fontweight='bold', pad=20)
ax.grid(axis='y', alpha=0.3, linestyle='--')

plt.tight_layout()
chart_1_path = os.path.join(run_dir, '1_abc_distribution.png')
plt.savefig(chart_1_path, dpi=300, bbox_inches='tight')
print(f"✅ 已保存：{chart_1_path}\n")
plt.close()

# ======================================
# 若有 math 分類，生成額外圖表
# ======================================

if math_df is not None and len(math_df) > 0:

    # ======== 圖 2：歷年 Math 分類總量 ========

    print("生成圖 2：歷年 Math 分類總量...")

    fig, ax = plt.subplots(figsize=(12, 6))

    yearly_counts = math_df.groupby('Year').size().sort_index()

    sns.barplot(
        x=yearly_counts.index,
        y=yearly_counts.values,
        palette='Blues_d',
        ax=ax
    )

    ax.set_title('歷年數學分類總量', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('年份', fontsize=12, fontweight='bold')
    ax.set_ylabel('分類出現次數', fontsize=12, fontweight='bold')

    for i, v in enumerate(yearly_counts.values):
        ax.text(i, v + 0.5, str(v), ha='center', fontweight='bold')

    plt.tight_layout()
    chart_2_path = os.path.join(run_dir, '2_yearly_math_total.png')
    plt.savefig(chart_2_path, dpi=300, bbox_inches='tight')
    print(f"✅ 已保存：{chart_2_path}\n")
    plt.close()

    # ======== 圖 3：Top 10 Math 分類趨勢 ========

    print("生成圖 3：Top 10 Math 分類趨勢...")

    fig, ax = plt.subplots(figsize=(14, 7))

    top10_categories = math_df['Math_Category'].value_counts().head(10).index
    math_top10 = math_df[math_df['Math_Category'].isin(top10_categories)]
    ct = math_top10.groupby(['Year', 'Math_Category']).size().unstack(fill_value=0)

    for cat in ct.columns:
        ax.plot(
            ct.index,
            ct[cat],
            marker='o',
            linewidth=2.5,
            markersize=6,
            label=cat
        )

    ax.set_title('Top 10 數學領域年度趨勢', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('年份', fontsize=12, fontweight='bold')
    ax.set_ylabel('出現次數', fontsize=12, fontweight='bold')
    ax.set_xticks(ct.index)
    ax.grid(True, alpha=0.3)

    ax.legend(
        title='Math Category',
        bbox_to_anchor=(1.02, 1),
        loc='upper left',
        fontsize=10
    )

    plt.tight_layout()
    chart_3_path = os.path.join(run_dir, '3_math_trends.png')
    plt.savefig(chart_3_path, dpi=300, bbox_inches='tight')
    print(f"✅ 已保存：{chart_3_path}\n")
    plt.close()

    # ======== 圖 4：Top 6 Math 分類百分比堆疊 ========

    print("生成圖 4：Top 6 Math 分類比例變化...")

    fig, ax = plt.subplots(figsize=(14, 7))

    top6_categories = math_df['Math_Category'].value_counts().head(6).index

    math_df['Display_Category'] = math_df['Math_Category'].apply(
        lambda x: x if x in top6_categories else 'Other'
    )

    ct_display = math_df.groupby(['Year', 'Display_Category']).size().unstack(fill_value=0)
    ct_pct = ct_display.div(ct_display.sum(axis=1), axis=0) * 100

    ct_pct.plot(
        kind='bar',
        stacked=True,
        cmap='tab20',
        ax=ax,
        width=0.7
    )

    ax.set_title('Top 6 數學領域比例變化', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('年份', fontsize=12, fontweight='bold')
    ax.set_ylabel('比例 (%)', fontsize=12, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

    ax.legend(
        title='Math Category',
        bbox_to_anchor=(1.02, 1),
        loc='upper left',
        fontsize=10
    )

    plt.tight_layout()
    chart_4_path = os.path.join(run_dir, '4_math_percentage.png')
    plt.savefig(chart_4_path, dpi=300, bbox_inches='tight')
    print(f"✅ 已保存：{chart_4_path}\n")
    plt.close()

    # ======== 圖 5：Math 分類 × A/B/C 分類熱力圖 ========

    print("生成圖 5：Math 分類 × A/B/C 分類熱力圖...")

    fig, ax = plt.subplots(figsize=(10, 12))

    top15_math = math_df['Math_Category'].value_counts().head(15).index
    math_df_top = math_df[math_df['Math_Category'].isin(top15_math)]

    crosstab = pd.crosstab(
        math_df_top['Math_Category'],
        math_df_top['AI_Category'],
        margins=True
    )

    sns.heatmap(
        crosstab.iloc[:-1, :-1],
        annot=True,
        fmt='d',
        cmap='YlOrRd',
        cbar_kws={'label': '論文數量'},
        ax=ax,
        linewidths=0.5
    )

    ax.set_title('Math 分類 × A/B/C 分類分布 (Top 15)', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('AI 分類', fontsize=12, fontweight='bold')
    ax.set_ylabel('Math 分類', fontsize=12, fontweight='bold')

    plt.tight_layout()
    chart_5_path = os.path.join(run_dir, '5_math_abc_heatmap.png')
    plt.savefig(chart_5_path, dpi=300, bbox_inches='tight')
    print(f"✅ 已保存：{chart_5_path}\n")
    plt.close()

    # ======== 圖 6：按年份的 Math 分類分布 ========

    print("生成圖 6：按年份的 Math 分類分布...")

    fig, ax = plt.subplots(figsize=(14, 7))

    yearly_math = math_df.groupby(['Year', 'Math_Category']).size().reset_index(name='Count')

    recent_years = (
        sorted(yearly_math['Year'].unique())[-5:]
        if len(yearly_math['Year'].unique()) > 5
        else sorted(yearly_math['Year'].unique())
    )

    yearly_math_recent = yearly_math[yearly_math['Year'].isin(recent_years)]

    top_per_year = yearly_math_recent.groupby('Year').apply(
        lambda x: x.nlargest(8, 'Count')
    ).reset_index(drop=True)

    pivot_data = top_per_year.pivot_table(
        index='Math_Category',
        columns='Year',
        values='Count',
        fill_value=0
    )

    pivot_data.plot(
        kind='bar',
        ax=ax,
        width=0.8
    )

    ax.set_title('近年 Top Math 分類年度變化', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Math 分類', fontsize=12, fontweight='bold')
    ax.set_ylabel('論文數量', fontsize=12, fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    ax.legend(title='Year', fontsize=10)

    plt.tight_layout()
    chart_6_path = os.path.join(run_dir, '6_yearly_math_comparison.png')
    plt.savefig(chart_6_path, dpi=300, bbox_inches='tight')
    print(f"✅ 已保存：{chart_6_path}\n")
    plt.close()

# ======================================
# 更新 latest/ 並清理舊資料夾
# ======================================

update_latest(CHARTS_BASE_DIR, run_dir)
cleanup_old_runs(CHARTS_BASE_DIR, KEEP_RUNS)

# ======================================
# 統計摘要
# ======================================

print("\n" + "="*60)
print("📊 詳細統計摘要")
print("="*60)

print(f"\n【A/B/C 分類統計】")
for cat in ['A', 'B', 'C']:
    count = len(filtered_df[filtered_df['category'] == cat])
    if count > 0:
        pct = (count / len(filtered_df)) * 100
        print(f"  {category_labels_zh.get(cat, cat)}: {count} 篇 ({pct:.1f}%)")

if math_df is not None and len(math_df) > 0:
    print(f"\n【Math 分類統計】")
    print(f"  總分類記錄數：{len(math_df)}")
    print(f"  獨特 Math 分類：{math_df['Math_Category'].nunique()}")
    print(f"\n  Top 10 Math 分類：")
    top_math = math_df['Math_Category'].value_counts().head(10)
    for math_cat, count in top_math.items():
        pct = (count / len(math_df)) * 100
        print(f"    {math_cat}: {count} ({pct:.1f}%)")

print(f"\n【生成信息】")
print(f"  本次執行：{run_name}")
print(f"  圖表位置：{run_dir}")
print(f"  使用字體：{selected_font}")

print("\n" + "="*60)
print("✨ 融合圖表生成完成！")
print("="*60)