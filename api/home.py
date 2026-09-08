# -*- coding: utf-8 -*-
"""GET /api/home?source=xxx -> 首页精选（抓取首页，优先挑出国漫）"""
from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
from ._lib import get_source, cached_fetch, parse_listing, pick_guoman


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        source_id = (qs.get("source", [""])[0] or "4kcz")
        source = get_source(source_id)

        html = cached_fetch("home:" + source["id"], source["home"], referer=source["base"])
        items = parse_listing(html, source["home"])
        featured = pick_guoman(items)
        if not featured:
            featured = items[:12]

        payload = {"ok": 1, "source": source["id"], "items": featured}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "public, max-age=60")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def log_message(self, *args):
        pass
