#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩语记单词 - 音频批量生成脚本
用 macOS 自带的高质量韩语语音 Yuna，为每个单词生成发音音频。

用法：python3 generate_audio.py
生成结果存放在 audio/ 目录，文件名用单词内容的哈希（ID），
这样无论在哪里插入/删除单词，音频都不会错位。
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(HERE, "audio")

# 复用 build.py 的读取逻辑和 word_id，保证一致
sys.path.insert(0, HERE)
from build import load_words, CSV_PATH, word_id

VOICE = "Yuna"  # 韩语女声


def gen_one(word, out_path):
    """生成单个单词音频：say 输出 aiff -> afconvert 转 AAC m4a"""
    tmp = os.path.join(tempfile.gettempdir(), "hangul_tmp_%s.aiff" % word_id(word))
    try:
        subprocess.run(
            ["say", "-v", VOICE, "-o", tmp, word],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["afconvert", tmp, "-o", out_path, "-f", "m4af", "-d", "aac"],
            check=True, capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print("  生成失败 [%s]: %s" % (word, e.stderr.decode("utf-8", "ignore").strip()))
        return False
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    if not os.path.exists(CSV_PATH):
        print("错误：找不到 单词.csv")
        sys.exit(1)

    words = load_words(CSV_PATH)
    os.makedirs(AUDIO_DIR, exist_ok=True)

    total = len(words)
    done = 0
    failed = 0
    skipped = 0

    print("开始检查 %d 个单词的音频（语音：%s）..." % (total, VOICE))
    print("音频保存到：%s\n" % AUDIO_DIR)

    for i, w in enumerate(words):
        wid = word_id(w["word"])
        out_path = os.path.join(AUDIO_DIR, "%s.m4a" % wid)
        # 断点续传：已存在的跳过
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            skipped += 1
            continue

        if gen_one(w["word"], out_path):
            done += 1
        else:
            failed += 1

        if (i + 1) % 50 == 0:
            print("  进度：%d / %d（已生成 %d，跳过 %d，失败 %d）"
                  % (i + 1, total, done, skipped, failed))

    print("\n完成！共 %d 个：生成 %d，跳过(已存在) %d，失败 %d"
          % (total, done, skipped, failed))
    if failed:
        print("有失败项，可重新运行本脚本重试（已成功的会自动跳过）。")


if __name__ == "__main__":
    main()
