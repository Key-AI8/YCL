# -*- coding: utf-8 -*-
"""GET /api/search?wd=关键词&source=xxx -> 搜索番剧列表"""
from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse, quote
from ._lib import get_source, fetch, parse_listing


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        wd = (qs.get("wd", [""])[0] or "").strip()
        source_id = (qs.get("source", [""])[0] or "4kcz")
        source = get_source(source_id)

        if not wd:
            self._send(200, {"ok": 0, "msg": "请输入搜索关键词", "items": []})
            return

        url = source["search"].format(wd=quote(wd))
        html = fetch(url, referer=source["base"], timeout=12)
        items = parse_listing(html, url)

        self._send(200, {"ok": 1, "wd": wd, "source": source["id"], "items": items})

    def _send(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def log_message(self, *args):
        pass
