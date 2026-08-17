#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
韩语记单词 - 本地 HTTP 服务器
正确设置 .m4a 等音频的 MIME 类型，保证 iPad/安卓能正常播放发音。

用法：python3 serve.py [端口]
默认端口 8000。
"""

import http.server
import socketserver
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

# 关键：修正 m4a 的 MIME 类型，避免移动浏览器拒绝播放
class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
    }

    def log_message(self, fmt, *args):
        # 精简日志，不刷屏
        pass


os.chdir(os.path.dirname(os.path.abspath(__file__)))

with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print("服务器已启动，端口 %d" % PORT)
    print("目录：%s" % os.getcwd())
    httpd.serve_forever()
