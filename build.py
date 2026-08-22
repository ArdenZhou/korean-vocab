#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩语记单词 - 数据更新脚本
读取「单词.csv」（首尔大学韩国语）和「yonsei_words.json」（延世韩国语），
把两套教材的数据内联更新进 index.html，支持多教材切换。

用法：双击「更新单词.command」，或命令行运行 python3 build.py
"""

import csv
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "单词.csv")
YONSEI_PATH = os.path.join(HERE, "yonsei_words.json")
HTML_PATH = os.path.join(HERE, "index.html")
WORDSJS_PATH = os.path.join(HERE, "words.js")

BEGIN = "// ===WORDS_DATA_BEGIN==="
END = "// ===WORDS_DATA_END==="

BOOK_SNU = "snu"
BOOK_YONSEI = "yonsei"
BOOK_NAMES = {
    BOOK_SNU: "首尔大学韩国语",
    BOOK_YONSEI: "延世韩国语",
}


def word_id(word):
    """用单词内容生成稳定的唯一 ID，作为音频文件名。
    这样无论在哪里插入、删除、排序，音频都跟着单词走，不会错位。"""
    return hashlib.md5(word.encode("utf-8")).hexdigest()


def norm_ko(s):
    """归一化韩文词，用于跨教材匹配（去掉标点、空格、非韩文字符）。"""
    return re.sub(r"[^가-힣]", "", s or "")


def load_words(csv_path):
    """读取首尔大学韩国语词表（单词.csv）。"""
    words = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            def col(*names):
                for n in names:
                    if n in row and row[n] is not None:
                        return str(row[n]).strip()
                return ""

            lesson = col("课时")
            word = col("单词")
            if not lesson or not word:
                continue
            try:
                lesson = int(float(lesson))
            except (ValueError, TypeError):
                continue

            words.append({
                "volume": None,  # 首尔大不分册
                "lesson": lesson,
                "word": word,
                "explain": col("解释"),
                "pos": col("词性"),
                "note": col("备注"),
                "origin": "",
                "originDetail": "",
                "english": "",
            })

    words.sort(key=lambda w: w["lesson"])
    return words


def load_yonsei(json_path):
    """读取延世韩国语词库（yonsei_words.json）。"""
    if not os.path.exists(json_path):
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    words = []
    for w in data:
        words.append({
            "volume": w.get("volume"),
            "lesson": w.get("lesson", 1),
            "word": w.get("word", ""),
            "explain": w.get("explain", ""),
            "pos": w.get("pos", ""),
            "note": w.get("note", ""),
            "origin": w.get("origin", ""),
            "originDetail": w.get("originDetail", ""),
            "english": w.get("english", ""),
        })
    return words


def enrich_snu(snu_words, yonsei_words):
    """给首尔大词表补充词源、词源详解、英文（按韩文词匹配延世词库）。"""
    # 建立归一化韩文 -> 延世信息 的映射（取第一个，优先有词源的）
    ymap = {}
    for y in yonsei_words:
        key = norm_ko(y["word"])
        if not key:
            continue
        if key not in ymap:
            ymap[key] = y
        else:
            # 已有条目但无词源，当前条目有词源，则替换
            existing = ymap[key]
            if not existing["origin"] and y["origin"]:
                ymap[key] = y

    matched = 0
    for w in snu_words:
        key = norm_ko(w["word"])
        if key in ymap:
            y = ymap[key]
            if y["origin"] and not w["origin"]:
                w["origin"] = y["origin"]
            if y["originDetail"] and not w["originDetail"]:
                w["originDetail"] = y["originDetail"]
            if y["english"] and not w["english"]:
                w["english"] = y["english"]
            matched += 1
    return matched


def build(snu_words, yonsei_words):
    books = []

    # 首尔大
    snu = []
    for i, w in enumerate(snu_words):
        w["idx"] = i
        w["id"] = word_id(w["word"])
        w["book"] = BOOK_SNU
        snu.append(w)
    books.append({"id": BOOK_SNU, "name": BOOK_NAMES[BOOK_SNU], "words": snu})

    # 延世
    yonsei = []
    for i, w in enumerate(yonsei_words):
        w["idx"] = i
        w["id"] = word_id(w["word"])
        w["book"] = BOOK_YONSEI
        yonsei.append(w)
    books.append({"id": BOOK_YONSEI, "name": BOOK_NAMES[BOOK_YONSEI], "words": yonsei})

    data_js = json.dumps(books, ensure_ascii=False, indent=2)
    total = len(snu) + len(yonsei)
    words_js = (
        "// 韩语单词数据 - 自动生成，支持多教材\n"
        "// 首尔大学韩国语 %d 词 + 延世韩国语 %d 词 = 共 %d 词\n"
        "window.BOOKS = %s;\n" % (len(snu), len(yonsei), total, data_js)
    )

    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    pattern = re.compile(re.escape(BEGIN) + r"[\s\S]*?" + re.escape(END))
    if not pattern.search(html):
        print("错误：index.html 中找不到数据标记，请确认文件未被改动。")
        sys.exit(1)

    new_block = BEGIN + "\n" + words_js + END
    html = pattern.sub(lambda m: new_block, html, count=1)

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    with open(WORDSJS_PATH, "w", encoding="utf-8") as f:
        f.write(words_js)

    return len(snu), len(yonsei)


def main():
    if not os.path.exists(CSV_PATH):
        print("错误：找不到「单词.csv」")
        print("请把 Excel 另存为 CSV（UTF-8 编码）放到本目录，文件名必须是：单词.csv")
        print("列名必须是：课时,单词,解释,词性,备注")
        sys.exit(1)

    snu_words = load_words(CSV_PATH)
    yonsei_words = load_yonsei(YONSEI_PATH)

    matched = enrich_snu(snu_words, yonsei_words)

    snu_n, yonsei_n = build(snu_words, yonsei_words)

    from collections import Counter
    c = Counter(w["lesson"] for w in snu_words)
    print("✅ 更新完成！")
    print("   首尔大学韩国语：%d 个单词，%d 课" % (snu_n, len(c)))
    for k in sorted(c):
        print("       第 %d 课：%d 个" % (k, c[k]))
    if yonsei_n:
        yc = Counter((w["volume"], w["lesson"]) for w in yonsei_words)
        print("   延世韩国语：%d 个单词，%d 册" % (yonsei_n, len(set(v for v, _ in yc))))
    print("   首尔大词表已补充词源：%d 个匹配上延世词库" % matched)
    print("\n刷新浏览器即可看到更新。")


if __name__ == "__main__":
    main()
