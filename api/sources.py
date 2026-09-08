# -*- coding: utf-8 -*-
"""GET /api/sources -> 返回数据源列表"""
from http.server import BaseHTTPRequestHandler
from ._lib import SOURCES


def _json(code, obj):
    return code, {"Content-Type": "application/json"}, json.dumps(obj, ensure_ascii=False)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        body = json.dumps({"sources": [
            {"id": s["id"], "name": s["name"], "base": s["base"]} for s in SOURCES
        ]}, ensure_ascii=False)
        self.wfile.write(body.encode("utf-8"))

    # 抑制 BaseHTTPRequestHandler 的默认 stderr 日志
    def log_message(self, *args):
        pass


# 让本地 `python server.py` 也能跑：兼容顶层变量写法（Vercel 用 handler 类）
import json  # noqa
