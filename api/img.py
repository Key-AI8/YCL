# -*- coding: utf-8 -*-
"""GET /api/img?url=封面图url -> 代理返回图片字节（绕过防盗链/跨域）"""
from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
from urllib.parse import parse_qs, urlparse
from ._lib import DEFAULT_UA

# 允许的图片后缀（简单白名单，防止被当任意代理滥用）
_ALLOWED = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        img_url = (qs.get("url", [""])[0] or "").strip()
        if not img_url:
            self._text(400, "missing url")
            return
        lower = img_url.lower()
        if not lower.startswith("http"):
            self._text(400, "invalid url")
            return
        if not lower.endswith(_ALLOWED):
            # 没有后缀也放行（有些动态图床），但记录
            pass

        try:
            req = urllib.request.Request(img_url, headers={
                "User-Agent": DEFAULT_UA,
                "Referer": img_url,
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "image/jpeg")
        except Exception as e:
            self._text(502, "fetch failed: %s" % e)
            return

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _text(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(msg.encode("utf-8"))

    def log_message(self, *args):
        pass
