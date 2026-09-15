#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 words.js 生成 Anki 牌组（.apkg）

用法：
    python3 make_anki.py                      # 默认：首尔大学韩国语，双向，带发音
    python3 make_anki.py --book yonsei        # 延世韩国语
    python3 make_anki.py --book all           # 全部教材
    python3 make_anki.py --direction forward  # 只生成 韩→中
    python3 make_anki.py --direction reverse  # 只生成 中→韩
    python3 make_anki.py --no-audio           # 不打包发音

发音来源：krdict 官方真人 mp3 优先，Yuna m4a 兜底（本项目中 668/668 词均有真人发音）
"""

import argparse
import hashlib
import json
import os
import re
import sys

import genanki

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORDS_JS = os.path.join(BASE_DIR, "words.js")
KR_MP3_DIR = os.path.join(BASE_DIR, "audio_krdict")
YUNA_DIR = os.path.join(BASE_DIR, "audio")

# ---------------------------------------------------------------- 数据读取


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load_books(path=WORDS_JS):
    """读取 words.js 中的 window.BOOKS 数组"""
    src = open(path, encoding="utf-8").read()
    m = re.search(r"window\.BOOKS\s*=\s*(\[.*\])\s*;?\s*$", src, re.S)
    if not m:
        sys.exit("✗ 无法在 words.js 中找到 window.BOOKS 数据")
    return json.loads(m.group(1))


def find_audio(word):
    """返回 (文件名, 绝对路径)；优先 krdict 官方 mp3，其次 Yuna m4a"""
    h = md5(word)
    mp3 = os.path.join(KR_MP3_DIR, h + ".mp3")
    if os.path.exists(mp3):
        return h + ".mp3", mp3
    m4a = os.path.join(YUNA_DIR, h + ".m4a")
    if os.path.exists(m4a):
        return h + ".m4a", m4a
    return None, None


# ---------------------------------------------------------------- 卡片样式

CSS = """
.card {
  font-family: -apple-system, "PingFang SC", "Hiragino Sans GB", "Noto Sans KR", "Malgun Gothic", sans-serif;
  font-size: 20px;
  text-align: center;
  color: #1b1b1b;
  background: #ffffff;
  padding: 24px 16px;
  line-height: 1.5;
}
.word {
  font-family: "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  font-size: 52px;
  font-weight: 700;
  color: #111111;
  letter-spacing: 1px;
  margin-bottom: 4px;
}
.pron {
  font-size: 19px;
  color: #a9720a;
  margin-bottom: 10px;
}
.meaning {
  font-size: 34px;
  font-weight: 600;
  color: #0b5fa5;
  margin: 10px 0 6px 0;
}
.pos {
  display: inline-block;
  font-size: 13px;
  color: #777777;
  border: 1px solid #d5d5d5;
  border-radius: 10px;
  padding: 1px 9px;
  margin: 4px 0 10px 0;
}
.meta {
  font-size: 15px;
  color: #666666;
  margin-top: 5px;
}
.meta b { color: #444444; font-weight: 600; }
.lesson {
  font-size: 13px;
  color: #a0a0a0;
  margin-top: 14px;
}
hr#answer {
  border: none;
  border-top: 1px solid #e2e2e2;
  margin: 16px 0 12px 0;
}
/* 夜间模式 */
.night_mode .card, .nightMode .card { background: #2b2b2b; color: #e8e8e8; }
.night_mode .word, .nightMode .word { color: #ffffff; }
.night_mode .meaning, .nightMode .meaning { color: #6fb8f0; }
.night_mode .pron, .nightMode .pron { color: #e0b055; }
.night_mode .pos, .nightMode .pos { color: #aaaaaa; border-color: #555555; }
.night_mode .meta, .nightMode .meta { color: #aaaaaa; }
.night_mode .meta b, .nightMode .meta b { color: #cccccc; }
.night_mode .lesson, .nightMode .lesson { color: #888888; }
.night_mode hr#answer, .nightMode hr#answer { border-top-color: #444444; }
"""

FIELDS = [
    {"name": "Word"},          # 韩语
    {"name": "Meaning"},       # 中文释义
    {"name": "Pos"},           # 词性
    {"name": "Pron"},          # 发音标注（如 중국 → 한국）
    {"name": "Origin"},        # 词源
    {"name": "OriginDetail"},  # 词源细节（如 中國）
    {"name": "English"},       # 英文
    {"name": "Lesson"},        # 出处
    {"name": "Audio"},         # [sound:xxx]
]

# 韩 → 中
QFMT_FORWARD = """<div class="word">{{Word}}</div>
<div class="pos">{{Pos}}</div>
<div>{{Audio}}</div>"""

AFMT_FORWARD = """<div class="word">{{Word}}</div>
{{#Pron}}<div class="pron">{{Pron}}</div>{{/Pron}}
<div class="pos">{{Pos}}</div>
<div>{{Audio}}</div>
<hr id="answer">
<div class="meaning">{{Meaning}}</div>
{{#Origin}}<div class="meta">词源：<b>{{Origin}}</b>{{#OriginDetail}}（{{OriginDetail}}）{{/OriginDetail}}</div>{{/Origin}}
{{#English}}<div class="meta">英文：{{English}}</div>{{/English}}
<div class="meta lesson">{{Lesson}}</div>"""

# 中 → 韩
QFMT_REVERSE = """<div class="meaning">{{Meaning}}</div>
<div class="pos">{{Pos}}</div>"""

AFMT_REVERSE = """<div class="meaning">{{Meaning}}</div>
<div class="pos">{{Pos}}</div>
<hr id="answer">
<div class="word">{{Word}}</div>
{{#Pron}}<div class="pron">{{Pron}}</div>{{/Pron}}
<div>{{Audio}}</div>
{{#Origin}}<div class="meta">词源：<b>{{Origin}}</b>{{#OriginDetail}}（{{OriginDetail}}）{{/OriginDetail}}</div>{{/Origin}}
{{#English}}<div class="meta">英文：{{English}}</div>{{/English}}
<div class="meta lesson">{{Lesson}}</div>"""


def build_model(direction):
    templates = []
    if direction in ("forward", "both"):
        templates.append({
            "name": "韩语 → 中文",
            "qfmt": QFMT_FORWARD,
            "afmt": AFMT_FORWARD,
        })
    if direction in ("reverse", "both"):
        templates.append({
            "name": "中文 → 韩语",
            "qfmt": QFMT_REVERSE,
            "afmt": AFMT_REVERSE,
        })
    return genanki.Model(
        1607392319,
        "韩语单词（真人发音）",
        fields=FIELDS,
        templates=templates,
        css=CSS,
    )


# ---------------------------------------------------------------- 主流程


def stable_id(text):
    """由字符串生成稳定的 Anki id"""
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:9], 16)


def clean(text):
    if not text:
        return ""
    return str(text).strip()


def main():
    ap = argparse.ArgumentParser(description="生成韩语单词 Anki 牌组")
    ap.add_argument("--book", default="snu", choices=["snu", "yonsei", "all"],
                    help="教材范围（默认 snu 首尔大学韩国语）")
    ap.add_argument("--direction", default="both",
                    choices=["forward", "reverse", "both"],
                    help="卡片方向（默认 both 双向）")
    ap.add_argument("--no-audio", action="store_true", help="不打包真人发音")
    ap.add_argument("--out", default=None, help="输出文件名")
    args = ap.parse_args()

    books = load_books()
    if args.book == "all":
        selected = books
    else:
        selected = [b for b in books if b["id"] == args.book]
        if not selected:
            sys.exit("✗ 未找到教材: " + args.book)

    model = build_model(args.direction)
    decks = []
    media_files = []
    media_seen = set()
    stats = {"words": 0, "notes": 0, "audio": 0, "no_audio": 0, "docs": []}

    for book in selected:
        book_name = book["name"]
        book_id = book["id"]
        # 按 (册, 课) 分组
        groups = {}
        for w in book["words"]:
            vol = w.get("volume")
            les = w.get("lesson")
            groups.setdefault((vol, les), []).append(w)

        for (vol, les), words in sorted(
            groups.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1])
        ):
            if vol is None:
                deck_name = "%s::第%02d课" % (book_name, les)
                lesson_label = "第%d课" % les
            else:
                deck_name = "%s::第%d册::第%02d课" % (book_name, vol, les)
                lesson_label = "第%d册 第%d课" % (vol, les)

            deck = genanki.Deck(stable_id("deck::" + deck_name), deck_name)
            stats["docs"].append((deck_name, len(words)))

            for w in words:
                word = clean(w.get("word"))
                meaning = clean(w.get("explain"))
                if not word:
                    continue
                stats["words"] += 1

                # 发音
                audio_field = ""
                if not args.no_audio:
                    fname, fpath = find_audio(word)
                    if fname:
                        audio_field = "[sound:%s]" % fname
                        if fname not in media_seen:
                            media_seen.add(fname)
                            media_files.append(fpath)
                        stats["audio"] += 1
                    else:
                        stats["no_audio"] += 1

                pron = clean(w.get("pron"))
                if pron == word:
                    pron = ""  # 与拼写相同则不显示，减少干扰

                note = genanki.Note(
                    model=model,
                    fields=[
                        word,
                        meaning,
                        clean(w.get("pos")),
                        pron,
                        clean(w.get("origin")),
                        clean(w.get("originDetail")),
                        clean(w.get("english")),
                        lesson_label,
                        audio_field,
                    ],
                )
                deck.add_note(note)
                stats["notes"] += 1

            if deck.notes:
                decks.append(deck)

    if not decks:
        sys.exit("✗ 没有生成任何卡片")

    out_name = args.out or ("%s%s.apkg" % (
        "韩语单词-全部" if args.book == "all" else selected[0]["name"],
        "" if args.direction == "both" else ("-韩中" if args.direction == "forward" else "-中韩"),
    ))
    out_path = os.path.join(BASE_DIR, out_name)

    pkg = genanki.Package(decks)
    if media_files:
        pkg.media_files = media_files
    pkg.write_to_file(out_path)

    # ------------------------------------------------------------ 报告
    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print("✓ 生成成功: %s" % out_name)
    print("  体积: %.1f MB" % size_mb)
    print("  牌组: %d 个（按课拆分）" % len(decks))
    print("  单词: %d 个" % stats["words"])
    print("  卡片: %d 张（%s）" % (
        stats["notes"] * (2 if args.direction == "both" else 1),
        {"both": "双向", "forward": "韩→中", "reverse": "中→韩"}[args.direction],
    ))
    print("  真人发音: %d 个" % stats["audio"])
    if stats["no_audio"]:
        print("  ⚠ 无发音: %d 个" % stats["no_audio"])
    if media_files:
        total_media = sum(os.path.getsize(p) for p in media_files) / 1024 / 1024
        print("  音频原始体积: %.1f MB（已压缩进包）" % total_media)
    print("\n  牌组列表:")
    for name, cnt in stats["docs"]:
        print("    %s  (%d 词)" % (name, cnt))
    print("\n下一步：双击 %s 导入 Anki" % out_name)


if __name__ == "__main__":
    main()
