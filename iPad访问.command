#!/bin/bash
# 韩语记单词 - iPad/手机访问
# 双击启动，让同一 WiFi 下的 iPad/iPhone 用 Safari 打开

cd "$(dirname "$0")"

IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
if [ -z "$IP" ]; then
  echo "未检测到局域网 IP，请确认 Mac 已连 WiFi。"
  read -r -p "按回车键退出..."
  exit 1
fi

PORT=8000

echo "=============================================="
echo "  iPad / iPhone 访问方法"
echo "=============================================="
echo ""
echo "  1. 确保 iPad 和 Mac 连的是【同一个 WiFi】"
echo "  2. 在 iPad 打开 Safari，地址栏输入下面这行："
echo ""
echo "        http://$IP:$PORT/index.html"
echo ""
echo "  3. 打开后点 Safari 底部的「分享」按钮"
echo "     选择「添加到主屏幕」，以后就像 App 一样点开"
echo ""
echo "  ⚠️ 保持这个窗口开着，不要关（关了就访问不了）"
echo "     用完后按 Ctrl+C 或直接关掉本窗口"
echo "=============================================="
echo ""

python3 serve.py "$PORT"
