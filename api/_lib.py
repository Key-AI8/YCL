# -*- coding: utf-8 -*-
"""共享解析库：数据源配置、抓取、HTML 解析、缓存、归一化。

所有 api/*.py 都 import 这里的函数，避免重复代码。
只使用 Python 标准库（urllib, html, re, json, time, threading），
确保 Vercel Python runtime 无需额外依赖即可运行。
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import re
import threading
from html import unescape

# ---------------------------------------------------------------------------
# 数据源配置
# 每个源：首页列表页 + 搜索页模板 + 详情页模板 + 播放页模板
# ---------------------------------------------------------------------------
SOURCES = [
    {
        "id": "4kcz",
        "name": "4K 纯享",
        "base": "https://www.4kcz.com",
        "home": "https://www.4kcz.com/",
        "search": "https://www.4kcz.com/vod/search/wd/{wd}.html",
        "detail": "https://www.4kcz.com/vod/detail/id/{id}.html",
        "play": "https://www.4kcz.com/vod/play/id/{id}/nid/{nid}.html",
    },
]

# 国漫标题（用于首页精选，与原 server.py 保持一致）
GUOMAN_TITLES = [
    "伍六七", "刺客伍六七", "灵笼", "凡人修仙传", "斗罗大陆", "完美世界",
    "遮天", "斗破苍穹", "大主宰", "武动乾坤", "魔道祖师", "天官赐福",
    "全职高手", "秦时明月", "画江湖", "不良人", "白蛇缘起", "哪吒",
    "姜子牙", "大鱼海棠", "罗小黑战记", "镇魂街", "雏蜂", "端脑",
]

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 进程内缓存（Serverless 同实例有效）
_cache = {}
_lock = threading.Lock()
CACHE_TTL = 300  # 秒


def get_source(source_id):
    for s in SOURCES:
        if s["id"] == source_id:
            return s
    return SOURCES[0]


def fetch(url, referer=None, timeout=10):
    """抓取 URL，返回解码后的文本。失败返回空字符串。"""
    headers = {"User-Agent": DEFAULT_UA}
    if referer:
        headers["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        # 尝试常见编码
        for enc in ("utf-8", "gbk", "gb2312", "gb18030"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore")
    except (urllib.error.URLError, TimeoutError, OSError):
        return ""


def cached_fetch(key, url, referer=None, timeout=10):
    """带 TTL 的缓存抓取。"""
    now = time.time()
    with _lock:
        item = _cache.get(key)
        if item and now - item[0] < CACHE_TTL:
            return item[1]
    text = fetch(url, referer=referer, timeout=timeout)
    with _lock:
        _cache[key] = (now, text)
    return text


def make_abs(base, href):
    """把相对链接转绝对链接。"""
    if not href:
        return ""
    try:
        return urllib.parse.urljoin(base, href.strip())
    except Exception:
        return href


def clean_text(s):
    if not s:
        return ""
    return unescape(re.sub(r"<[^>]+>", "", s)).strip()


# ---------------------------------------------------------------------------
# 搜索结果 / 列表页解析
# 适配苹果CMS体系（4kcz 等）：
#   - 列表项通常在 .search-item / .vodlist / li 含 a[href] 的结构里
#   - 通过正则兜底抽取 cover / title / detail url
# ---------------------------------------------------------------------------
def parse_listing(html, base):
    """从列表/搜索页 HTML 中抽取番剧卡片列表。

    策略：先定位所有「详情链接」的 <a>，再在其内部独立抽取封面 <img> 与标题文本，
    避免封面/标题在 DOM 中顺序不固定导致匹配失败。
    """
    items = []
    seen = set()

    # 第一步：抓所有详情类 <a href>
    link_pat = re.compile(r'<a\b[^>]+href="(?P<href>[^"]+)"[^>]*>.*?</a>', re.DOTALL)
    img_pat = re.compile(r'<img\b[^>]+src="(?P<src>[^"]+)"', re.IGNORECASE)
    title_stop = re.compile(r'<(?:/?(?:span|div|p)|!--)')

    for m in link_pat.finditer(html):
        href = make_abs(base, m.group("href"))
        if not href or href in seen:
            continue
        if not re.search(r"/(detail|show|vod|play)/", href):
            continue
        block = m.group(0)

        # 封面：a 内部第一个 img
        im = img_pat.search(block)
        cover = make_abs(base, im.group("src")) if im else ""

        # 标题：a 内部第一个貌似片名的文本节点（去掉封面alt等）
        # 取所有纯文本，去掉标签，取最长有意义片段
        text = re.sub(r'<[^>]+>', ' ', block)
        text = clean_text(text)
        # 常见分隔清理
        text = re.split(r'\s*(?:主演|导演|类型|年份|地区|简介|详情|播放|选集)\s*[:：]', text)[0]
        title = text.strip()

        if not title or len(title) < 2:
            continue
        if re.match(r"^(主演|导演|类型|年份|地区|简介|详情|播放|选集|搜索|首页)", title):
            continue

        seen.add(href)
        items.append({"title": title, "url": href, "cover": cover})

    return items


# ---------------------------------------------------------------------------
# 详情页解析：抽取选集列表
# 优先从 "播放地址" 区域抽取 nid 链接；其次抽 <a href> 中含 play 的链接。
# ---------------------------------------------------------------------------
def parse_detail(html, base, source):
    """返回 dict: {title, cover, intro, episodes:[{name, url}]}"""
    title = ""
    m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    if m:
        raw = clean_text(m.group(1)).strip()
        # 常见 "片名 - 站点" / "片名_xxx" 取第一部分
        for sep in ["-", "_", "|", "–", "—"]:
            raw = raw.split(sep)[0].strip()
        title = raw

    cover = ""
    cm = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
    if cm:
        cover = make_abs(base, cm.group(1))
    else:
        im = re.search(r'<img[^>]+class="[^"]*vod-pic[^"]*"[^>]+src="([^"]+)"', html)
        if im:
            cover = make_abs(base, im.group(1))

    intro = ""
    im2 = re.search(r'<div[^>]+class="[^"]*vod-content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if im2:
        intro = clean_text(im2.group(1))[:500]

    episodes = []
    seen = set()
    # 选集区域：常见 class 含 "playlist / play-list / vod-play-list"
    play_area = html
    pam = re.search(r'<div[^>]+class="[^"]*(?:play-list|playlist|vod-play-list)[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
    if pam:
        play_area = pam.group(1)

    for a in re.finditer(r'<a[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<name>[^<]{1,40})</a>', play_area):
        href = make_abs(base, a.group("href"))
        if not href or href in seen:
            continue
        if not re.search(r"/(play|ep|video)/", href):
            continue
        name = clean_text(a.group("name"))
        if not name:
            continue
        seen.add(href)
        episodes.append({"name": name, "url": href})

    return {
        "title": title or "未知",
        "cover": cover,
        "intro": intro,
        "episodes": episodes,
    }


# ---------------------------------------------------------------------------
# 播放地址抽取：从播放页 HTML / JS 里抠出 m3u8 / mp4 直链
# ---------------------------------------------------------------------------
def find_video_url(html, base):
    """在播放页里找 m3u8 / mp4 直链。"""
    # 1) 显式 video/source
    for pat in [
        r'<source[^>]+src="([^"]+\.(?:m3u8|mp4|webm)(?:\?[^"]*)?)"',
        r'<video[^>]+src="([^"]+\.(?:m3u8|mp4|webm)(?:\?[^"]*)?)"',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return make_abs(base, m.group(1))

    # 2) JS 变量 / 字符串里的直链
    m = re.search(r'["\']((?:https?:)?//[^"\s]+\.(?:m3u8|mp4|webm)(?:\?[^"\s]*)?)["\']', html, re.IGNORECASE)
    if m:
        return make_abs(base, m.group(1))
    m = re.search(r'(?:file|url|video)\s*[:=]\s*["\']([^"\']+\.(?:m3u8|mp4|webm)(?:\?[^"\s]*)?)["\']', html, re.IGNORECASE)
    if m:
        return make_abs(base, m.group(1))
    return ""


def pick_guoman(items):
    """从列表里优先挑出国漫标题，供首页精选。"""
    hits = []
    for t in GUOMAN_TITLES:
        for it in items:
            if t in it.get("title", ""):
                hits.append(it)
                break
    return hits[:12]
