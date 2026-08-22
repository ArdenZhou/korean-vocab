#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
延世韩国语词库导入脚本
把《延世韩国语》1-6 册的 CSV 数据标准化成本项目可用的 yonsei_words.json。

数据来源：open-yonsei-korean-vocabulary（开源，CC BY-SA 3.0）
https://github.com/Amulopapa67/open-yonsei-korean-vocabulary

用法：python3 import_yonsei.py [csv目录]
  csv目录里放 vol-01.csv ~ vol-06.csv
  默认从 data/yonsei_csv/ 读取，输出到 yonsei_words.json
"""

import csv
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_DIR = os.path.join(HERE, "data", "yonsei_csv")
OUT_PATH = os.path.join(HERE, "yonsei_words.json")

# 词源类型 -> 中文标签
ORIGIN_MAP = {
    "native": "固有词",
    "hanja": "汉字词",
    "loanword": "外来词",
    "hybrid": "混合词",
    "expression": "表达",
    "grammar": "语法",
}


def word_id(word):
    """与 build.py 保持一致的稳定 ID（MD5 哈希），用于共享音频。"""
    return hashlib.md5(word.encode("utf-8")).hexdigest()


def load_volume(csv_path, volume):
    words = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            def col(*names):
                for n in names:
                    if n in row and row[n] is not None:
                        return str(row[n]).strip()
                return ""

            ko = col("korean")
            if not ko:
                continue
            try:
                chapter = int(float(col("chapter")))
            except (ValueError, TypeError):
                chapter = 1
            try:
                unit = int(float(col("unit")))
            except (ValueError, TypeError):
                unit = 1

            origin_en = col("origin_type")
            origin = ORIGIN_MAP.get(origin_en, origin_en or "")
            origin_detail = col("origin_detail")

            words.append({
                "volume": volume,
                "lesson": chapter,
                "unit": unit,
                "word": ko,
                "explain": col("chinese"),
                "english": col("english"),
                "pos": col("pos_zh"),
                "origin": origin,
                "originDetail": origin_detail,
                "note": "",
                "id": word_id(ko),
            })
    return words


def main():
    csv_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV_DIR
    if not os.path.isdir(csv_dir):
        print("错误：找不到 CSV 目录 %s" % csv_dir)
        sys.exit(1)

    all_words = []
    for vol in range(1, 7):
        path = os.path.join(csv_dir, "vol-%02d.csv" % vol)
        if not os.path.exists(path):
            print("跳过：找不到 %s" % path)
            continue
        w = load_volume(path, vol)
        all_words.extend(w)
        print("第 %d 册：%d 词" % (vol, len(w)))

    # 排序：册 -> 课 -> 单元 -> 原顺序
    # load_volume 已按原顺序，这里按 (volume, lesson, unit) 稳定排序
    all_words.sort(key=lambda x: (x["volume"], x["lesson"], x["unit"]))

    # 重新编号 idx
    for i, w in enumerate(all_words):
        w["idx"] = i

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_words, f, ensure_ascii=False, indent=2)

    from collections import Counter
    c = Counter((w["volume"], w["lesson"]) for w in all_words)
    print("\n✅ 已生成 %s，共 %d 词，%d 个(册,课)组合" % (OUT_PATH, len(all_words), len(c)))
    for (v, l) in sorted(c):
        pass  # 太详细不打印


if __name__ == "__main__":
    main()
