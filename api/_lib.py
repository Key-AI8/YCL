import json
import re
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
CTX = ssl.create_default_context()

# Vercel Serverless 是无状态的，进程内缓存在冷启动间不共享，
# 但仍可在一个实例生命周期内减少重复请求，保留原逻辑即可。
CACHE = {}
CACHE_TTL = 300


def cache_get(key):
    hit = CACHE.get(key)
    if not hit:
        return None
    ts, val = hit
    if time.time() - ts > CACHE_TTL:
        CACHE.pop(key, None)
        return None
    return val


def cache_set(key, val):
    CACHE[key] = (time.time(), val)


def http_get(url, timeout=8):
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": url,
    })
    try:
        with urlopen(req, timeout=timeout, context=CTX) as resp:
            data = resp.read()
            charset = "utf-8"
            ctype = resp.headers.get("Content-Type", "")
            m = re.search(r"charset=([\w-]+)", ctype, re.I)
            if m:
                charset = m.group(1)
            return data.decode(charset, "ignore")
    except (HTTPError, URLError, TimeoutError, OSError):
        return None


def http_get_binary(url, timeout=8):
    """返回 (bytes, content_type)，失败返回 (None, None)"""
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": url,
    })
    try:
        with urlopen(req, timeout=timeout, context=CTX) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "application/octet-stream")
            return data, ctype
    except (HTTPError, URLError, TimeoutError, OSError):
        return None, None


def fetch_json(url, timeout=5):
    text = http_get(url, timeout=timeout)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


SOURCES = [
    {"id": "lz", "name": "量子资源", "api": "https://cj.lziapi.com/api.php/provide/vod/from/lzm3u8"},
    {"id": "bf", "name": "暴风资源", "api": "https://bfzyapi.com/api.php/provide/vod"},
    {"id": "ff", "name": "非凡资源", "api": "https://cj.ffzyapi.com/api.php/provide/vod"},
    {"id": "ry", "name": "如意资源", "api": "https://cj.rycjapi.com/api.php/provide/vod"},
    {"id": "ikun", "name": "iKun资源", "api": "https://ikunzyapi.com/api.php/provide/vod"},
    {"id": "wj", "name": "无尽资源", "api": "https://api.wujinapi.me/api.php/provide/vod"},
    {"id": "zd", "name": "最大资源", "api": "https://api.zuidapi.com/api.php/provide/vod"},
    {"id": "js", "name": "极速资源", "api": "https://jszyapi.com/api.php/provide/vod"},
    {"id": "dytt", "name": "电影天堂", "api": "http://caiji.dyttzyapi.com/api.php/provide/vod"},
    {"id": "hn", "name": "红牛资源", "api": "https://www.hongniuzy2.com/api.php/provide/vod"},
]

SOURCE_MAP = {s["id"]: s for s in SOURCES}

GUOMAN_TITLES = [
    {"name": "仙逆", "weekday": 2, "pin": 1},
    {"name": "凡人修仙传", "weekday": 6, "pin": 2},
    {"name": "遮天", "weekday": 3, "pin": 3},
    {"name": "斗破苍穹", "weekday": 5, "pin": 4},
    {"name": "完美世界", "weekday": 4, "pin": 5},
    {"name": "吞噬星空", "weekday": 6, "pin": 6},
    {"name": "一念永恒", "weekday": 5, "pin": 7},
    {"name": "剑来", "weekday": 7, "pin": 8},
    {"name": "牧神记", "weekday": 1, "pin": 9},
    {"name": "沧元图", "weekday": 6, "pin": 10},
    {"name": "斗罗大陆", "weekday": 7, "pin": 11},
    {"name": "神印王座", "weekday": 4, "pin": 12},
    {"name": "斩神", "weekday": 3, "pin": 13},
    {"name": "百炼成神", "weekday": 2, "pin": 14},
    {"name": "灵笼", "weekday": 5, "pin": 15},
    {"name": "凸变英雄", "weekday": 6, "pin": 16},
    {"name": "雾山五行", "weekday": 1, "pin": 17},
    {"name": "狐妖小红娘", "weekday": 4, "pin": 18},
    {"name": "万界独尊", "weekday": 3, "pin": 19},
    {"name": "武神主宰", "weekday": 2, "pin": 20},
    {"name": "星辰变", "weekday": 7, "pin": 21},
    {"name": "全职高手", "weekday": 1, "pin": 22},
]


def normalize_item(item, source):
    return {
        "vod_id": item.get("vod_id"),
        "vod_name": item.get("vod_name") or "",
        "vod_pic": item.get("vod_pic") or "",
        "vod_year": item.get("vod_year") or "",
        "vod_remarks": item.get("vod_remarks") or "",
        "vod_time": item.get("vod_time") or "",
        "vod_play_url": item.get("vod_play_url") or "",
        "vod_play_from": item.get("vod_play_from") or "",
        "type_name": item.get("type_name") or "",
        "source_id": source["id"],
        "source_name": source["name"],
    }


def search_one(source, keyword):
    url = source["api"] + "?ac=detail&wd=" + quote(keyword)
    data = fetch_json(url, timeout=4)
    if data and data.get("list"):
        return [normalize_item(it, source) for it in data["list"]]
    #  fallback: 部分站点用 ?wd= 而非 ?ac=detail&wd=
    data = fetch_json(source["api"] + "?wd=" + quote(keyword), timeout=4)
    if data and data.get("list"):
        return [normalize_item(it, source) for it in data["list"]]
    return []


def detail_one(source_id, vod_id):
    source = SOURCE_MAP.get(source_id)
    if not source or not vod_id:
        return None
    data = fetch_json(source["api"] + "?ac=detail&ids=" + quote(str(vod_id)), timeout=8)
    if data and data.get("list"):
        return normalize_item(data["list"][0], source)
    return None


def pick_guoman(keyword, items):
    skip = ("短剧", "剧场版", "电影", "日语", "花魁", "合集")
    best = None
    best_score = -1
    for it in items:
        name = it.get("vod_name") or ""
        typ = it.get("type_name") or ""
        remarks = it.get("vod_remarks") or ""
        if keyword not in name:
            continue
        score = 0
        if name == keyword:
            score += 120
        elif name.startswith(keyword):
            score += 90
        else:
            score += 40
        if "国产动漫" in typ or "动漫" in typ:
            score += 25
        if any(s in name or s in typ for s in skip):
            score -= 40
        if "更新" in remarks:
            score += 12
        if score > best_score:
            best_score = score
            best = it
    return best


def load_home():
    cached = cache_get("home")
    if cached is not None:
        return cached
    week = {str(i): [] for i in range(1, 8)}
    hot = []
    src = SOURCE_MAP.get("ry") or SOURCES[0]
    found = {}

    # Vercel 函数有超时限制（Hobby 10s / Pro 60s），必须控制总耗时。
    # 策略：设置总截止时间，逐个请求，超时即停止并返回已收集数据。
    deadline = time.time() + 8  # 预留 2s 余量给序列化/网络

    for meta in GUOMAN_TITLES:
        if time.time() > deadline:
            break
        try:
            items = search_one(src, meta["name"])
        except Exception:
            items = []
        hit = pick_guoman(meta["name"], items)
        if hit:
            hit = dict(hit)
            hit["weekday"] = meta["weekday"]
            hit["kind"] = "week"
            hit["pin"] = meta["pin"]
            found[meta["name"]] = hit

    ordered = sorted(found.values(), key=lambda x: x.get("pin") or 99)
    for it in ordered:
        day = str(it.get("weekday") or 1)
        week.setdefault(day, []).append(it)
        hot.append(it)

    # 补充热门：同样受 deadline 约束
    if time.time() < deadline:
        extra_src = SOURCE_MAP.get("lz") or src
        extra = fetch_json(extra_src["api"] + "?ac=detail&t=29&pg=1", timeout=3)
        seen = {x.get("vod_name") for x in hot}
        if extra and extra.get("list"):
            for raw in extra["list"]:
                if time.time() > deadline:
                    break
                it = normalize_item(raw, extra_src)
                name = it.get("vod_name")
                typ = it.get("type_name") or ""
                if not name or name in seen:
                    continue
                if "短剧" in typ or "电影" in typ:
                    continue
                if "动漫" not in typ and "动画" not in typ:
                    continue
                seen.add(name)
                hot.append(it)
                if len(hot) >= 24:
                    break

    payload = {"week": week, "hot": hot[:30]}
    cache_set("home", payload)
    return payload
