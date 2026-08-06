"""
一次性腳本：批次解析既有 JSON 中的 Google News 短網址，替換為 TinyURL 短網址。

使用方式：
    pip install googlenewsdecoder requests
    python fix_existing_urls.py

會掃描 data/ 目錄下所有 YYYY-MM-DD.json，將 summary 中的
https://news.google.com/rss/articles/... 連結解碼為原始網址再轉 TinyURL。
"""

import json
import os
import re
import time
import requests
from googlenewsdecoder import new_decoderv1

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# 匹配 Markdown 連結中的 Google News URL
MARKDOWN_LINK_RE = re.compile(
    r'\[([^\]]+)\]\((https://news\.google\.com/rss/articles/[^\s)]+)\)'
)

# 匹配純文字中的 Google News URL
PLAIN_URL_RE = re.compile(
    r'(https://news\.google\.com/rss/articles/[^\s)]+)'
)


def decode_google_news_url(google_url):
    """使用 googlenewsdecoder 解碼 Google News URL 取得原始連結。"""
    try:
        result = new_decoderv1(google_url)
        if result and result.get("status"):
            return result["decoded_url"]
        return None
    except Exception as e:
        print(f"    解碼失敗: {e}")
        return None


def shorten_with_tinyurl(long_url, timeout=15):
    """透過 TinyURL 將長網址轉短網址。"""
    try:
        api_url = f"https://tinyurl.com/api-create.php?url={long_url}"
        res = requests.get(api_url, timeout=timeout)
        if res.status_code == 200 and res.text.startswith("https://"):
            return res.text.strip()
        return None
    except Exception as e:
        print(f"    TinyURL 失敗: {e}")
        return None


def process_url(google_url):
    """完整流程：Google News URL → 解碼原始連結 → TinyURL。"""
    print(f"  解碼: {google_url[:80]}...")

    real_url = decode_google_news_url(google_url)
    if not real_url:
        print(f"    ⚠️ 無法解碼，保留原始連結")
        return google_url

    print(f"    原始: {real_url[:80]}...")

    short_url = shorten_with_tinyurl(real_url)
    if not short_url:
        print(f"    ⚠️ TinyURL 失敗，使用原始連結")
        return real_url

    print(f"    短網址: {short_url}")
    # 避免 API rate limit
    time.sleep(1.5)
    return short_url


def fix_json_file(filepath):
    """修正單一 JSON 檔案中的 Google News 連結。"""
    print(f"\n處理: {os.path.basename(filepath)}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", "")
    if not summary:
        print("  （無 summary 內容，跳過）")
        return False

    # 收集所有需要替換的 Google News URL
    google_urls = set()

    for match in MARKDOWN_LINK_RE.finditer(summary):
        google_urls.add(match.group(2))

    for match in PLAIN_URL_RE.finditer(summary):
        google_urls.add(match.group(1))

    if not google_urls:
        print("  （無 Google News 連結，跳過）")
        return False

    print(f"  發現 {len(google_urls)} 個 Google News 連結")

    # 逐一解碼並替換
    modified = False
    for url in google_urls:
        new_url = process_url(url)
        if new_url != url:
            summary = summary.replace(url, new_url)
            modified = True

    if modified:
        data["summary"] = summary
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 已更新")
    else:
        print(f"  （無變更）")

    return modified


def main():
    print("=" * 60)
    print("批次修正既有 JSON 中的 Google News 短網址")
    print("=" * 60)

    if not os.path.isdir(DATA_DIR):
        print(f"找不到 data 目錄: {DATA_DIR}")
        return

    json_files = sorted(
        [f for f in os.listdir(DATA_DIR) if re.match(r'\d{4}-\d{2}-\d{2}\.json', f)],
        reverse=True
    )

    if not json_files:
        print("data/ 目錄中無日報 JSON 檔案")
        return

    print(f"\n找到 {len(json_files)} 個日報檔案")

    updated_count = 0
    for filename in json_files:
        filepath = os.path.join(DATA_DIR, filename)
        if fix_json_file(filepath):
            updated_count += 1

    print(f"\n{'=' * 60}")
    print(f"完成！共更新 {updated_count}/{len(json_files)} 個檔案")
    print("=" * 60)


if __name__ == "__main__":
    main()
