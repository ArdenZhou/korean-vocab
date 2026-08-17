#!/bin/bash
# 韩语记单词 - 生成发音音频
# 双击运行，为每个单词生成韩语发音（已生成的会自动跳过）

cd "$(dirname "$0")"

echo "========================================"
echo "  韩语记单词 - 生成发音音频"
echo "========================================"
echo ""
echo "  正在为每个单词生成发音，请稍候..."
echo "  （已生成的会自动跳过，只需等待）"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误：未找到 python3。"
  read -r -p "按回车键退出..."
  exit 1
fi

python3 generate_audio.py

echo ""
echo "  生成完成！"
echo ""
read -r -p "按回车键关闭..."
