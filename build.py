#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩语记单词 - 数据更新脚本
读取「单词.csv」，把数据内联更新进 index.html

用法：双击「更新单词.command」，或命令行运行 python3 build.py
"""

import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "单词.csv")
HTML_PATH = os.path.join(HERE, "index.html")
WORDSJS_PATH = os.path.join(HERE, "words.js")

BEGIN = "// ===WORDS_DATA_BEGIN==="
END = "// ===WORDS_DATA_END==="


def load_words(csv_path):
    words = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 兼容列名带 BOM 或空格
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
                "lesson": lesson,
                "word": word,
                "explain": col("解释"),
                "pos": col("词性"),
                "note": col("备注"),
            })

    # 按课时排序，课时内保持原顺序
    words.sort(key=lambda w: w["lesson"])
    return words


def build(words):
    # 给每个单词加索引，与 audio/ 目录下的音频文件名一一对应
    for i, w in enumerate(words):
        w["idx"] = i

    data_js = json.dumps(words, ensure_ascii=False, indent=2)
    words_js = (
        "// 韩语单词数据 - 自动从 Excel 生成\n"
        "// 共 %d 个单词\n"
        "window.WORDS = %s;\n" % (len(words), data_js)
    )

    # 更新 index.html 内联数据
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    pattern = re.compile(
        re.escape(BEGIN) + r"[\s\S]*?" + re.escape(END)
    )
    if not pattern.search(html):
        print("错误：index.html 中找不到数据标记，请确认文件未被改动。")
        sys.exit(1)

    new_block = BEGIN + "\n" + words_js + END
    html = pattern.sub(lambda m: new_block, html, count=1)

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    # 同步更新 words.js（备份/源数据文件）
    with open(WORDSJS_PATH, "w", encoding="utf-8") as f:
        f.write(words_js)

    return len(words)


def main():
    if not os.path.exists(CSV_PATH):
        print("错误：找不到「单词.csv」")
        print("请把 Excel 另存为 CSV（UTF-8 编码）放到本目录，文件名必须是：单词.csv")
        print("列名必须是：课时,单词,解释,词性,备注")
        sys.exit(1)

    words = load_words(CSV_PATH)
    n = build(words)

    # 统计每课数量
    from collections import Counter
    c = Counter(w["lesson"] for w in words)
    print("✅ 更新完成！共 %d 个单词，%d 课" % (n, len(c)))
    for k in sorted(c):
        print("   第 %d 课：%d 个" % (k, c[k]))
    print("\n刷新浏览器即可看到新单词。")


if __name__ == "__main__":
    main()
