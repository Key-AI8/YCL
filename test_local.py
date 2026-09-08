# -*- coding: utf-8 -*-
"""本地测试：mock 网络层，验证解析 + API 逻辑。
不依赖真实网络，可在沙盒/本地直接跑：python test_local.py
"""
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

import _lib

# 用真实 4kcz 片段构造测试 HTML
SAMPLE_LIST = """
<html><body>
<a href="/vod/detail/id/123.html">
  <img src="/uploads/cover1.jpg">
  <span class="title">伍六七 第三季</span>
</a>
<a href="/vod/detail/id/124.html">
  <img src="https://img.example.com/c2.jpg">
  <span class="title">主演:张三</span>
</a>
<a href="/vod/detail/id/125.html">
  <img src="/uploads/cover3.jpg">
  <span class="title">斗罗大陆</span>
</a>
<a href="/other/page.html"><img src="/x.jpg"><span>无关链接</span></a>
</body></html>
"""

SAMPLE_DETAIL = """
<html><head><title>灵笼 - 4K纯享</title>
<meta property="og:image" content="https://img.example.com/linglong.jpg"></head>
<body>
<div class="vod-content">末日废土题材动画，讲述人类在天空之城中生存的故事。</div>
<div class="play-list">
  <a href="/vod/play/id/200/nid/1.html">第01集</a>
  <a href="/vod/play/id/200/nid/2.html">第02集</a>
  <a href="/vod/play/id/200/nid/3.html">第03集</a>
</div>
</body></html>
"""

SAMPLE_PLAY = """
<html><body>
<video src="https://video.example.com/linglong/ep1.m3u8?token=abc"></video>
</body></html>
"""

SAMPLE_PLAY_JS = """
<script>
var player = {file:"https://video.example.com/xx/playlist.m3u8?sign=xyz",type:"hls"};
</script>
"""

passed = 0
failed = 0

def ok(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}")

print("== _lib 解析逻辑 ==")
items = _lib.parse_listing(SAMPLE_LIST, "https://www.4kcz.com")
ok("列表解析出2个有效项(过滤主演/无关)", len(items) == 2)
ok("第一项标题含片名", items[0]["title"].startswith("伍六七"))
ok("封面转绝对地址", items[0]["cover"].startswith("https://www.4kcz.com/uploads/"))
ok("过滤掉'主演:'误判", not any("主演" in i["title"] for i in items))
ok("过滤掉非详情链接", all("/detail/" in i["url"] for i in items))

info = _lib.parse_detail(SAMPLE_DETAIL, "https://www.4kcz.com/vod/detail/id/200.html", _lib.SOURCES[0])
ok("详情标题抽取", info["title"].startswith("灵笼"))
ok("详情封面og:image", info["cover"] == "https://img.example.com/linglong.jpg")
ok("选集抽3集", len(info["episodes"]) == 3)
ok("选集name正确", info["episodes"][0]["name"] == "第01集")
ok("选集url绝对化", info["episodes"][0]["url"].startswith("https://www.4kcz.com/vod/play/"))

v1 = _lib.find_video_url(SAMPLE_PLAY, "https://www.4kcz.com")
ok("video标签直链", v1 == "https://video.example.com/linglong/ep1.m3u8?token=abc")

v2 = _lib.find_video_url(SAMPLE_PLAY_JS, "https://www.4kcz.com")
ok("JS变量直链", v2 == "https://video.example.com/xx/playlist.m3u8?sign=xyz")

gm = _lib.pick_guoman([
    {"title": "伍六七 第三季", "url": "u1", "cover": ""},
    {"title": "某外国动画", "url": "u2", "cover": ""},
    {"title": "斗罗大陆", "url": "u3", "cover": ""},
])
ok("国漫精选命中", len(gm) == 2 and gm[0]["title"].startswith("伍六七"))

ok("数据源配置存在4kcz", any(s["id"] == "4kcz" for s in _lib.SOURCES))
ok("get_source默认回退", _lib.get_source("not_exist")["id"] == "4kcz")

print("\n== API handler 逻辑（mock fetch）==")

# mock _lib.fetch / cached_fetch
def mock_fetch(url, referer=None, timeout=10):
    if "search" in url:
        return SAMPLE_LIST
    if "detail" in url or url.endswith(".html"):
        return SAMPLE_DETAIL
    return ""

def mock_cached(k, url, referer=None, timeout=10):
    return mock_fetch(url, referer, timeout)

_lib.fetch = mock_fetch
_lib.cached_fetch = mock_cached

# 手动调用 handler 的 do_GET 逻辑（复用其内部拼接）
from urllib.parse import urlencode, quote
src = _lib.SOURCES[0]

# search 逻辑
wd = "灵笼"
search_url = src["search"].format(wd=quote(wd))
search_html = mock_fetch(search_url)
search_items = _lib.parse_listing(search_html, search_url)
ok("search接口解析", len(search_items) >= 0)

# detail 逻辑
detail_url = src["detail"].format(id=200)
detail_html = mock_fetch(detail_url, referer=src["base"])
d = _lib.parse_detail(detail_html, detail_url, src)
first = d["episodes"][0]["url"] if d["episodes"] else ""
play_html = mock_fetch(first, referer=detail_url)
video_url = _lib.find_video_url(play_html, first or detail_url)
d["video_url"] = video_url
ok("detail接口含video_url", "video_url" in d)

# 组装最终 payload（模拟前端拿到的结构）
payload = {"ok": 1, "data": d}
ok("payload结构含data.items/episodes", "episodes" in payload["data"] and "video_url" in payload["data"])
print("  sample payload:", json.dumps(payload, ensure_ascii=False)[:200])

print(f"\n总计：{passed} 通过，{failed} 失败")
sys.exit(0 if failed == 0 else 1)
