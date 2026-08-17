#!/bin/bash
# 韩语记单词 - 更新单词数据
# 双击此文件即可运行（首次可能需要右键→打开，因为 macOS 安全限制）

cd "$(dirname "$0")"

echo "========================================"
echo "  韩语记单词 - 更新单词数据"
echo "========================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误：未找到 python3，请先安装（系统通常自带）。"
  read -r -p "按回车键退出..."
  exit 1
fi

python3 build.py

echo ""
read -r -p "按回车键关闭..."
