import pandas as pd
import json
import os
import time
from datetime import datetime

# ======================================
# 基本設定
# ======================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

RAW_DB_PATH = os.path.join(
    BASE_DIR, "database", "papers_raw.csv"
)

FILTERED_DB_PATH = os.path.join(
    BASE_DIR, "database", "papers_filtered.csv"
)

# ======================================
# 檢查 Gemini API Key
# ======================================

API_KEY = os.getenv("GEMINI_API_KEY")
USE_LLM = False

if API_KEY:
    try:
        import google.genai as genai
        client = genai.Client(api_key=API_KEY)
        USE_LLM = True
        print("✅ 偵測到 Gemini API Key，優先使用 LLM 分類\n")
    except ImportError:
        print("⚠️ google-genai 未安裝，將使用關鍵字分類\n")
    except Exception as e:
        print(f"⚠️ Gemini API 初始化失敗，將使用關鍵字分類\n")
else:
    print("ℹ️ 未找到 Gemini API Key，使用分級關鍵字分類\n")

# ======================================
# 分級關鍵字定義（基於分層邏輯）
# ======================================

# 最高優先級：核心關鍵字（直接命中）
CORE_KEYWORDS = {
    "theorem proving", "theorem prover", "formal proof", "formalization",
    "autoformalization", "proof assistant", "lean 4", "lean theorem",
    "coq", "isabelle", "alphageometry", "alphaproof", "deepseek-prover",
    "neural theorem prover", "automated theorem proving", "atp"
}

# 高度相關關鍵字（強相關）
HIGH_RELEVANCE_KEYWORDS = {
    "mathematical reasoning", "formal verification", "proof generation",
    "proof search", "geometry solving", "sat solver", "smt solver",
    "large language model", "neuro-symbolic", "reinforcement learning",
    "math problem solving", "symbolic reasoning", "logical reasoning"
}

# AI/LLM 相關（中度相關）
AI_KEYWORDS = {
    "language model", "llm", "gpt", "transformer", "neural network",
    "deep learning", "machine learning", "ai", "artificial intelligence",
    "generative", "prompt"
}

# 數學領域關鍵字（基礎相關）
MATH_KEYWORDS = {
    "math", "mathematics", "theorem", "lemma", "conjecture",
    "proof", "logical", "algebra", "geometry", "number theory",
    "combinatorics", "optimization"
}

# 噪音過濾：明顯無關的領域
NOISE_KEYWORDS = {
    "medical", "healthcare", "disease", "drug discovery",
    "portfolio", "trading", "autonomous driving", "vehicle",
    "cybersecurity", "attack", "smart contract", "blockchain",
    "software repair", "bug", "video search", "image",
    "speech", "nlp", "translation", "sentiment", "recommendation",
    "job shop", "scheduling", "supply chain"
}

# ======================================
# 第一層：關鍵字篩選（過濾明顯無關的論文）
# ======================================

def keyword_filter(paper):
    """快速篩選：至少要有基本的數學或 AI 相關關鍵字"""
    
    text = (
        paper['title'] + " " + 
        paper['summary']
    ).lower()
    
    # 如果有核心關鍵字，肯定保留
    if any(k in text for k in CORE_KEYWORDS):
        return True
    
    # 如果有噪音關鍵字，除非同時有核心關鍵字，否則過濾掉
    if any(k in text for k in NOISE_KEYWORDS):
        return False
    
    # 必須至少有「數學」或「AI」相關的內容
    has_math = any(k in text for k in MATH_KEYWORDS)
    has_ai = any(k in text for k in AI_KEYWORDS)
    
    return has_math or has_ai

# ======================================
# 第二層：評分型分類（基於分級邏輯）
# ======================================

def rule_based_classify(paper):
    """
    基於分級邏輯的分類
    返回：(category, confidence, reason)
    """
    
    text = (
        paper['title'] + " " + 
        paper['summary']
    ).lower()
    
    # ===== 計算關鍵字匹配 =====
    core_matches = sum(1 for k in CORE_KEYWORDS if k in text)
    high_matches = sum(1 for k in HIGH_RELEVANCE_KEYWORDS if k in text)
    ai_matches = sum(1 for k in AI_KEYWORDS if k in text)
    
    # ===== 分類邏輯 =====
    
    # 優先級 1：有核心關鍵字 → A 或 B 類
    if core_matches > 0:
        # 檢查是否偏向「增強工具」(lean/coq/isabelle)
        if any(k in text for k in ["lean", "coq", "isabelle", "proof assistant"]):
            confidence = min(0.5 + core_matches * 0.2, 0.95)
            return {
                "category": "C",
                "confidence": confidence,
                "reason": f"包含 Proof Assistant 核心關鍵字（{core_matches} 個）"
            }
        
        # 檢查是否偏向「AI 證明」
        if any(k in text for k in ["neural", "deepseek", "alpha", "llm proof"]):
            confidence = min(0.6 + core_matches * 0.2, 0.95)
            return {
                "category": "A",
                "confidence": confidence,
                "reason": f"包含 AI 證明核心關鍵字（{core_matches} 個）"
            }
        
        # 預設當有核心關鍵字時為 B 類（協助/混合應用）
        confidence = min(0.5 + core_matches * 0.15, 0.90)
        return {
            "category": "B",
            "confidence": confidence,
            "reason": f"包含定理證明核心關鍵字（{core_matches} 個）"
        }
    
    # 優先級 2：有高度相關關鍵字 + AI 相關 → B 類
    if high_matches > 0 and ai_matches > 0:
        confidence = min(0.4 + high_matches * 0.15, 0.85)
        return {
            "category": "B",
            "confidence": confidence,
            "reason": f"包含數學推理 + AI 關鍵字（推理{high_matches}個、AI{ai_matches}個）"
        }
    
    # 優先級 3：只有高度相關關鍵字 → B 類（數學推理）
    if high_matches >= 2:
        confidence = min(0.3 + high_matches * 0.15, 0.80)
        return {
            "category": "B",
            "confidence": confidence,
            "reason": f"包含數學推理關鍵字（{high_matches} 個）"
        }
    
    # 優先級 4：有 AI + 數學 但不強 → C 類
    if ai_matches > 1:
        confidence = min(0.3 + ai_matches * 0.1, 0.70)
        return {
            "category": "C",
            "confidence": confidence,
            "reason": f"包含 AI 和數學相關詞彙（{ai_matches} 個）"
        }
    
    # 默認：只有很弱的相關性 → C 類
    total_matches = core_matches + high_matches + ai_matches
    if total_matches > 0:
        confidence = min(0.2 + total_matches * 0.05, 0.50)
        return {
            "category": "C",
            "confidence": confidence,
            "reason": "弱相關（基礎數學或 AI 詞彙）"
        }
    
    # 都沒中（理論上不會發生，因為前面已篩選過）
    return {
        "category": "C",
        "confidence": 0.1,
        "reason": "最小相關性"
    }

# ======================================
# LLM 分類（如果有 API Key）
# ======================================

CLASSIFICATION_PROMPT = """
請詳細分析以下學術論文，並判斷其分類。

【論文資訊】
標題：{title}
摘要：{summary}

【分類標準】
請根據以下定義判斷此論文屬於哪一類：

A. AI 直接完成數學證明
   - AI/機器學習模型能獨立生成有效的數學證明
   - 例：Neural Theorem Prover, AlphaProof, DeepSeek-Prover

B. AI 協助人類完成數學證明
   - AI 工具幫助人類數學家驗證或優化證明
   - 例：LLM 輔助 Lean/Coq 程式設計、數學推理研究

C. AI 增強 Proof Assistant
   - 改進 Lean、Coq、Isabelle 等形式化系統
   - 例：使用 LLM 加速定理求解、自動形式化

【你的判斷】
請以 JSON 格式回覆，包含：
- category: A|B|C
- confidence: 0.0-1.0 (信心度)
- reason: 簡短理由 (1-2 句)

【JSON 格式示例】
{{
  "category": "A",
  "confidence": 0.95,
  "reason": "論文提出新的神經定理證明器架構"
}}

只回覆 JSON，不要任何其他文字。
"""

def llm_classify(paper):
    """用 Gemini 進行分類"""
    
    try:
        prompt = CLASSIFICATION_PROMPT.format(
            title=paper['title'],
            summary=paper['summary'][:1500]
        )
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=200
            ),
        )
        
        response_text = response.text.strip()
        
        # 移除可能的 markdown
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        response_text = response_text.strip()
        result = json.loads(response_text)
        
        return {
            "category": result.get("category", "C"),
            "confidence": float(result.get("confidence", 0.5)),
            "reason": result.get("reason", "")
        }
        
    except json.JSONDecodeError:
        print(f"⚠️ JSON 解析失敗（{paper['arxiv_id']}），降級到關鍵字分類")
        return rule_based_classify(paper)
        
    except Exception as e:
        error_msg = str(e)
        
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print(f"\n⚠️ Gemini API 配額已用完，降級到關鍵字分類\n")
            global USE_LLM
            USE_LLM = False
            return rule_based_classify(paper)
        
        print(f"⚠️ Gemini API 錯誤，降級到關鍵字分類")
        return rule_based_classify(paper)

# ======================================
# 主流程
# ======================================

print("🚀 開始執行論文篩選與分類...\n")

# 1. 讀取原始資料
if not os.path.exists(RAW_DB_PATH):
    print(f"❌ 找不到原始資料：{RAW_DB_PATH}")
    exit(1)

raw_df = pd.read_csv(RAW_DB_PATH)
print(f"📂 已讀取 {len(raw_df)} 篇原始論文")

# 2. 第一層：快速篩選
print("\n第一層：快速篩選（過濾明顯無關的論文）...")
raw_df['passes_filter'] = raw_df.apply(
    keyword_filter, 
    axis=1
)

filtered_df = raw_df[raw_df['passes_filter']].copy()
removed_count = len(raw_df) - len(filtered_df)

print(f"✅ 通過篩選：{len(filtered_df)} 篇")
if removed_count > 0:
    print(f"   （過濾掉 {removed_count} 篇明顯無關的論文）")

# 3. 第二層：分類
print(f"\n第二層：{'LLM 分類' if USE_LLM else '分級關鍵字分類'}...\n")

classifications = []

for idx, (_, paper) in enumerate(filtered_df.iterrows()):
    print(
        f"  [{idx+1}/{len(filtered_df)}] "
        f"分類中：{paper['arxiv_id']}"
    )
    
    if USE_LLM:
        result = llm_classify(paper)
    else:
        result = rule_based_classify(paper)
    
    classifications.append(result)
    
    # 避免 API 限流
    if USE_LLM and (idx + 1) % 3 == 0:
        time.sleep(1)

# 4. 將結果加入 DataFrame
filtered_df[['category', 'confidence', 'reason']] = pd.DataFrame(
    classifications,
    index=filtered_df.index
)

# 5. 加入時間戳
filtered_df['classification_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
filtered_df['classification_method'] = 'LLM' if USE_LLM else '分級關鍵字'

# 6. 依照分類和信心度排序
filtered_df = filtered_df.sort_values(
    by=['category', 'confidence'],
    ascending=[True, False]
)

# 7. 保存結果
try:
    filtered_df.to_csv(
        FILTERED_DB_PATH,
        index=False,
        encoding="utf-8-sig"
    )
    print(f"\n💾 已保存到：{FILTERED_DB_PATH}")
    
except PermissionError:
    backup_path = os.path.join(
        BASE_DIR, "database", "papers_filtered_backup.csv"
    )
    filtered_df.to_csv(
        backup_path,
        index=False,
        encoding="utf-8-sig"
    )
    print(f"⚠️ 無法寫入主檔案，已備份到：{backup_path}")

# 8. 統計和報告
print("\n" + "="*50)
print("📊 分類統計：")
print("="*50)

for cat in ['A', 'B', 'C']:
    count = len(filtered_df[filtered_df['category'] == cat])
    avg_conf = filtered_df[filtered_df['category'] == cat]['confidence'].mean()
    if count > 0:
        print(f"  {cat} 類：{count:3d} 篇  (平均信心度：{avg_conf:.2f})")

print(f"\n總計：{len(filtered_df)} 篇有價值的論文")
print(f"過濾比率：{(1 - len(filtered_df)/len(raw_df))*100:.1f}%")
print(f"使用方法：{'LLM 分類 (高精度)' if USE_LLM else '分級關鍵字規則 (無需 API)'}")

print("\n" + "="*50)
print("✨ 分類完成！")
print("="*50)

# 9. 顯示前 5 篇高信心度論文
if len(filtered_df) > 0:
    print("\n🏆 信心度最高的 5 篇論文：")
    top_papers = filtered_df.nlargest(5, 'confidence')
    for idx, (_, paper) in enumerate(top_papers.iterrows(), 1):
        print(f"\n  {idx}. {paper['arxiv_id']}")
        print(f"     標題：{paper['title'][:70]}...")
        print(f"     分類：{paper['category']} 類")
        print(f"     信心度：{paper['confidence']:.2f}")
        print(f"     理由：{paper['reason']}")