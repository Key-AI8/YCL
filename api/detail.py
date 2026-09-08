# -*- coding: utf-8 -*-
"""GET /api/detail?source=xxx&url=详情页url -> 抽取选集与首集播放直链"""
from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
from ._lib import get_source, cached_fetch, parse_detail, find_video_url


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        detail_url = (qs.get("url", [""])[0] or "").strip()
        source_id = (qs.get("source", [""])[0] or "4kcz")
        source = get_source(source_id)

        if not detail_url:
            self._send(200, {"ok": 0, "msg": "缺少 url 参数"})
            return

        html = cached_fetch("detail:" + detail_url, detail_url, referer=source["base"], timeout=12)
        if not html:
            self._send(200, {"ok": 0, "msg": "抓取详情页失败（超时或被拦截）"})
            return

        info = parse_detail(html, detail_url, source)
        # 尝试抽取首集播放直链
        first_play_url = ""
        if info["episodes"]:
            first_play_url = info["episodes"][0]["url"]
        play_html = html
        if first_play_url and first_play_url != detail_url:
            play_html = cached_fetch("play:" + first_play_url, first_play_url,
                                     referer=detail_url, timeout=12)
        video_url = find_video_url(play_html, first_play_url or detail_url)
        info["video_url"] = video_url

        self._send(200, {"ok": 1, "data": info})

    def _send(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def log_message(self, *args):
        pass
