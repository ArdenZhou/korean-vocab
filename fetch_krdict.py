#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用韩国国立国语院「韩国语基础词典」Open API 获取：
1. 发音标注（pronunciation，如 독일 -> 도길）
2. 真人发音音频（MP3）

数据来源：https://krdict.korean.go.kr
Open API 文档：https://krdict.korean.go.kr/chn/openApi/openApiInfo

需要免费认证密钥（32 位十六进制）：
  优先读环境变量 KRDICT_KEY；否则读项目根目录 krdict_key.txt（第一行）。

用法：
  KRDICT_KEY=你的密钥 python3 fetch_krdict.py

输出：
  krdict_pron.json     发音标注映射 { word_hash: {"word":.., "pron":.., "target_code":..} }
  audio_krdict/*.mp3   真人发音音频（文件名 = MD5(word)，与 Yuna 音频一致）
"""

import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build import load_words, load_yonsei, CSV_PATH, YONSEI_PATH, word_id

API_SEARCH = "https://krdict.korean.go.kr/api/search"
API_VIEW = "https://krdict.korean.go.kr/api/view"
AUDIO_DIR = os.path.join(HERE, "audio_krdict")
PRON_PATH = os.path.join(HERE, "krdict_pron.json")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"

MAX_WORKERS = 6  # 并发线程数


def get_key():
    k = os.environ.get("KRDICT_KEY", "").strip()
    if not k:
        p = os.path.join(HERE, "krdict_key.txt")
        if os.path.exists(p):
            k = open(p, encoding="utf-8").read().strip()
    return k


def http_get(url):
    r = subprocess.run(
        ["curl", "-sL", "--max-time", "30", "-A", UA, url],
        capture_output=True,
    )
    return r.stdout.decode("utf-8", "ignore")


def strip_tag(xml, tag):
    m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), xml, re.S)
    return m.group(1).strip() if m else ""


def collect_words():
    seen = {}
    if os.path.exists(CSV_PATH):
        for w in load_words(CSV_PATH):
            seen[w["word"]] = True
    if os.path.exists(YONSEI_PATH):
        for w in load_yonsei(YONSEI_PATH):
            seen[w["word"]] = True
    return list(seen.keys())


def search_word(key, word):
    """搜索词，返回 (target_code, pronunciation)。"""
    url = API_SEARCH + "?" + urllib.parse.urlencode({
        "key": key, "q": word, "num": 10, "part": "word",
    })
    xml = http_get(url)
    if "<error>" in xml:
        code = strip_tag(xml, "error_code")
        msg = strip_tag(xml, "message")
        raise RuntimeError("API错误 %s: %s" % (code, msg))
    first_item = re.search(r"<item>(.*?)</item>", xml, re.S)
    if not first_item:
        return None, ""
    item = first_item.group(1)
    target_code = strip_tag(item, "target_code")
    pronunciation = strip_tag(item, "pronunciation")
    return target_code, pronunciation


def view_audio_url(key, target_code):
    """用 view API 获取发音音频 URL（需再解析 searchResultView 页面）。"""
    url = API_VIEW + "?" + urllib.parse.urlencode({
        "key": key, "method": "target_code", "q": target_code,
    })
    try:
        xml = http_get(url)
    except Exception:
        return ""
    if "<error>" in xml:
        return ""
    for pi in re.finditer(r"<pronunciation_info>(.*?)</pronunciation_info>", xml, re.S):
        link = strip_tag(pi.group(1), "link")
        if "searchResultView" in link:
            resolved = resolve_mp3_url(link)
            if resolved:
                return resolved
    return ""


def resolve_mp3_url(page_url):
    """访问发音查看页，解析出真实 mp3 URL。"""
    try:
        html = http_get(page_url)
        m = re.search(r"fnCmdPlaywer\([^,]*,\s*['\"]([^'\"]*\.mp3)['\"]", html)
        if m:
            return "https://krdicmedia.korean.go.kr/multimedia/multimedia_files" + m.group(1)
        m2 = re.search(r"(/convert/[^'\"]*SND[0-9]+\.mp3)", html)
        if m2:
            return "https://krdicmedia.korean.go.kr/multimedia/multimedia_files" + m2.group(1)
    except Exception:
        pass
    return ""


def download(url, out_path):
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "60", "-A", UA, "-o", out_path, url],
            capture_output=True,
        )
        return os.path.exists(out_path) and os.path.getsize(out_path) >= 1000
    except Exception:
        return False


def process_word(key, word):
    """处理单个词：search 拿发音标注，再下载真人音频。返回 (wid, result)。"""
    wid = word_id(word)
    try:
        target_code, pronunciation = search_word(key, word)
    except Exception:
        return wid, {"word": word, "pron": "", "target_code": "", "error": True}
    if not target_code:
        return wid, {"word": word, "pron": "", "target_code": "", "notfound": True}

    result = {"word": word, "pron": pronunciation or "", "target_code": target_code}

    # 下载真人音频
    mp3_path = os.path.join(AUDIO_DIR, "%s.mp3" % wid)
    if not os.path.exists(mp3_path):
        try:
            audio_url = view_audio_url(key, target_code)
            if audio_url:
                download(audio_url, mp3_path)
        except Exception:
            pass
    return wid, result


def main():
    key = get_key()
    if not key:
        print("错误：未找到 API 密钥。")
        print("请先到 https://krdict.korean.go.kr 申请免费的开放API认证密钥，")
        print("然后二选一：")
        print("  1) 命令行：KRDICT_KEY=你的密钥 python3 fetch_krdict.py")
        print("  2) 在本目录建 krdict_key.txt，第一行写密钥")
        sys.exit(1)

    words = collect_words()
    os.makedirs(AUDIO_DIR, exist_ok=True)

    # 断点续传：读已有结果
    pron = {}
    if os.path.exists(PRON_PATH):
        try:
            pron = json.load(open(PRON_PATH, encoding="utf-8"))
        except Exception:
            pron = {}

    # 已查过且有结果的词跳过；但音频缺失的仍需补（本轮一并处理）
    done_ids = set(pron.keys())
    todo = [w for w in words if word_id(w) not in done_ids]

    total = len(words)
    print("共 %d 个单词，本轮待查 %d 个，%d 并发..." % (total, len(todo), MAX_WORKERS))

    lock = threading.Lock()
    counters = {"done": 0, "pron": 0, "audio": 0, "notfound": 0, "error": 0}

    def save():
        # 调用处保证线程安全（循环内已在 lock 中，末尾无并发）
        json.dump(pron, open(PRON_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    results = {}
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_word, key, w): w for w in todo}
        for fut in concurrent.futures.as_completed(futures):
            wid, res = fut.result()
            with lock:
                pron[wid] = res  # 直接合并进 pron（断点续传用）
                counters["done"] += 1
                if res.get("pron"):
                    counters["pron"] += 1
                if os.path.exists(os.path.join(AUDIO_DIR, wid + ".mp3")):
                    counters["audio"] += 1
                if res.get("notfound"):
                    counters["notfound"] += 1
                if res.get("error"):
                    counters["error"] += 1
                n = counters["done"]
                if n % 50 == 0:
                    elapsed = time.time() - start
                    rate = n / elapsed if elapsed > 0 else 0
                    print("  进度：%d / %d（%.1f 个/秒）发音 %d，音频 %d，无词条 %d，失败 %d"
                          % (n, len(todo), rate, counters["pron"], counters["audio"],
                             counters["notfound"], counters["error"]))
                    save()

    # 最终保存
    save()

    print("\n完成！")
    print("  处理 %d 个词，耗时 %.1f 分钟" % (len(todo), (time.time() - start) / 60))
    print("  发音标注：%d 个" % counters["pron"])
    print("  真人音频：%d 个" % counters["audio"])
    print("  未找到词条：%d 个" % counters["notfound"])
    print("  失败：%d 个" % counters["error"])
    print("  发音标注已保存：%s" % PRON_PATH)
    print("  真人音频目录：%s" % AUDIO_DIR)


if __name__ == "__main__":
    main()
