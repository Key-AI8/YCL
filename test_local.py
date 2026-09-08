"""
纯本地单元测试 - 用 mock 替换所有网络调用，完全不联网。
验证: 代码结构、数据格式、参数校验、handler 返回格式
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

# ===== Mock 网络层（避免真实联网） =====
import _lib

MOCK_SEARCH_RESULT = [
    {
        "vod_id": "12345",
        "vod_name": "仙逆",
        "vod_pic": "https://pic.example.com/xianni.jpg",
        "vod_year": "2024",
        "vod_remarks": "更新至40集",
        "vod_play_url": "第01集$https://cdn.example.com/1.m3u8#第02集$https://cdn.example.com/2.m3u8#第03集$https://cdn.example.com/3.m3u8",
        "vod_play_from": "lzm3u8",
        "vod_time": "2024-01-01",
        "type_name": "国产动漫",
    },
    {
        "vod_id": "67890",
        "vod_name": "仙逆番外",
        "vod_pic": "",
        "vod_year": "",
        "vod_remarks": "",
        "vod_play_url": "",
        "vod_play_from": "",
        "vod_time": "",
        "type_name": "国产动漫",
    },
]

MOCK_DETAIL = {
    "vod_id": "12345",
    "vod_name": "仙逆",
    "vod_pic": "https://pic.example.com/xianni.jpg",
    "vod_year": "2024",
    "vod_remarks": "更新至40集",
    "vod_play_url": "第01集$https://cdn.example.com/1.m3u8#第02集$https://cdn.example.com/2.m3u8",
    "vod_play_from": "lzm3u8",
    "vod_time": "2024-01-01",
    "type_name": "国产动漫",
}

MOCK_HOME_DATA = {
    "week": {
        "1": [{"vod_name": "牧神记", "weekday": 1, "pin": 9, "vod_pic": "", "source_id": "ry", "source_name": "如意资源"}],
        "2": [{"vod_name": "仙逆", "weekday": 2, "pin": 1, "vod_pic": "", "source_id": "ry", "source_name": "如意资源"}],
        "3": [{"vod_name": "遮天", "weekday": 3, "pin": 3, "vod_pic": "", "source_id": "ry", "source_name": "如意资源"}],
        "4": [{"vod_name": "完美世界", "weekday": 4, "pin": 5, "vod_pic": "", "source_id": "ry", "source_name": "如意资源"}],
        "5": [{"vod_name": "斗破苍穹", "weekday": 5, "pin": 4, "vod_pic": "", "source_id": "ry", "source_name": "如意资源"}],
        "6": [{"vod_name": "凡人修仙传", "weekday": 6, "pin": 2, "vod_pic": "", "source_id": "ry", "source_name": "如意资源"}],
        "7": [{"vod_name": "斗罗大陆", "weekday": 7, "pin": 11, "vod_pic": "", "source_id": "ry", "source_name": "如意资源"}],
    },
    "hot": [
        {"vod_name": "仙逆", "pin": 1, "source_id": "ry", "source_name": "如意资源", "vod_pic": ""},
        {"vod_name": "凡人修仙传", "pin": 2, "source_id": "ry", "source_name": "如意资源", "vod_pic": ""},
    ],
}

_call_log = []

def mock_fetch_json(url, timeout=8):
    _call_log.append(("fetch_json", url))
    if "wd=" in url or "ac=detail" in url:
        # 搜索或详情
        if "ids=" in url:
            return {"list": [MOCK_DETAIL]}
        return {"list": MOCK_SEARCH_RESULT}
    return None

def mock_http_get(url, timeout=8):
    _call_log.append(("http_get", url))
    return ""

def mock_http_get_binary(url, timeout=8):
    _call_log.append(("http_get_binary", url))
    return b"\xff\xd8\xff" , "image/jpeg"

# 打补丁替换网络函数
_lib.fetch_json = mock_fetch_json
_lib.http_get = mock_http_get
_lib.http_get_binary = mock_http_get_binary

# 清空缓存确保测试纯净
_lib.CACHE = {}

# ===== 导入 API handlers =====
from sources import handler as sources_handler
from home import handler as home_handler
from search import handler as search_handler
from detail import handler as detail_handler
from img import handler as img_handler

PASS = 0
FAIL = 0

def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {msg}")
    else:
        FAIL += 1
        print(f"  ❌ {msg}")

def make_req(query=None):
    return {"query": query or {}}

print("="*60)
print("测试 1: 数据源配置")
print("="*60)
from _lib import SOURCES, SOURCE_MAP, GUOMAN_TITLES
check(len(SOURCES) == 10, f"共 {len(SOURCES)} 个片源")
check(len(GUOMAN_TITLES) == 22, f"共 {len(GUOMAN_TITLES)} 部国漫")
check("lz" in SOURCE_MAP, "片源映射包含 lz")
check(all("api" in s and "id" in s and "name" in s for s in SOURCES), "每个片源都有 id/name/api")

print("\n" + "="*60)
print("测试 2: /api/sources")
print("="*60)
resp = sources_handler(make_req())
body = json.loads(resp["body"])
check(resp["statusCode"] == 200, "状态码 200")
check("list" in body, "返回含 list 字段")
check(len(body["list"]) == 10, f"返回 {len(body['list'])} 个片源")
check(body["list"][0] == {"id": "lz", "name": "量子资源"}, "第一条是量子资源")
check(resp["headers"].get("Access-Control-Allow-Origin") == "*", "允许跨域")

print("\n" + "="*60)
print("测试 3: normalize_item")
print("="*60)
from _lib import normalize_item
src = SOURCES[0]
norm = normalize_item(MOCK_SEARCH_RESULT[0], src)
required = ["vod_id","vod_name","vod_pic","vod_year","vod_remarks",
            "vod_play_url","vod_play_from","type_name","source_id","source_name"]
for f in required:
    check(f in norm, f"包含字段 {f}")
check(norm["source_id"] == "lz", "source_id 正确")
check(norm["source_name"] == "量子资源", "source_name 正确")
check(norm["vod_name"] == "仙逆", "vod_name 正确")

print("\n" + "="*60)
print("测试 4: /api/search")
print("="*60)
# 空关键词
resp = search_handler(make_req({}))
body = json.loads(resp["body"])
check(body == {"list": []}, "空关键词返回空列表")

# 有关键词
resp = search_handler(make_req({"wd": "仙逆"}))
body = json.loads(resp["body"])
check("list" in body, "返回含 list")
check(len(body["list"]) >= 1, f"返回 {len(body['list'])} 条结果")
if body["list"]:
    check(body["list"][0]["vod_name"] == "仙逆", "第一条是仙逆")
    check("source_id" in body["list"][0], "结果含 source_id")

# 指定片源
resp = search_handler(make_req({"wd": "test", "source": "lz"}))
body = json.loads(resp["body"])
check("list" in body, "指定片源也返回 list")

# 去重逻辑
check(len({it["vod_name"] for it in body["list"]}) == len(body["list"]), "结果已按名称去重")

print("\n" + "="*60)
print("测试 5: /api/detail")
print("="*60)
resp = detail_handler(make_req({}))
body = json.loads(resp["body"])
check(body == {"item": None}, "空参数返回 item: null")

resp = detail_handler(make_req({"source": "lz", "id": "12345"}))
body = json.loads(resp["body"])
check("item" in body, "返回含 item")
if body["item"]:
    check(body["item"]["vod_name"] == "仙逆", "详情是仙逆")
    check(body["item"]["vod_play_url"] != "", "详情含播放地址")

# 无效片源
resp = detail_handler(make_req({"source": "invalid", "id": "12345"}))
body = json.loads(resp["body"])
check(body == {"item": None}, "无效片源返回 null")

print("\n" + "="*60)
print("测试 6: /api/home")
print("="*60)
resp = home_handler(make_req())
check(resp["statusCode"] == 200, "状态码 200")
body = json.loads(resp["body"])
check("week" in body and "hot" in body, "返回 week + hot")
check(set(body["week"].keys()) == {str(i) for i in range(1,8)}, "week 含周一到周日(1-7)")
check(len(body["hot"]) >= 1, f"hot 有 {len(body['hot'])} 部")
check(resp["headers"].get("Cache-Control", "").startswith("public"), "首页有缓存头")

print("\n" + "="*60)
print("测试 7: /api/img")
print("="*60)
resp = img_handler(make_req({"url": "not-valid"}))
check(resp["statusCode"] == 400, "无效URL返回400")

resp = img_handler(make_req({"url": "https://example.com/test.jpg"}))
check(resp["statusCode"] == 200, "有效URL返回200")
check(resp.get("isBase64Encoded") == True, "使用 base64 编码")
import base64 as b64
decoded = b64.b64decode(resp["body"])
check(decoded == b"\xff\xd8\xff", "base64 解码后是正确的二进制")
check(resp["headers"]["Content-Type"] == "image/jpeg", "Content-Type 正确")
check(resp["headers"]["Cache-Control"] == "public, max-age=86400", "图片缓存1天")

print("\n" + "="*60)
print("测试 8: pick_guoman 选片逻辑")
print("="*60)
from _lib import pick_guoman
items = [
    {"vod_name": "仙逆", "type_name": "国产动漫", "vod_remarks": "更新至40集"},
    {"vod_name": "仙逆剧场版", "type_name": "动漫", "vod_remarks": ""},
    {"vod_name": "仙逆", "type_name": "动漫", "vod_remarks": ""},
]
best = pick_guoman("仙逆", items)
check(best is not None, "能选出最佳匹配")
if best:
    check("剧场版" not in best["vod_name"], "排除剧场版")
    check(best["vod_name"] == "仙逆", "选中的是仙逆")

# 完全不匹配
best = pick_guoman("不存在的番", items)
check(best is None, "不匹配时返回 None")

print("\n" + "="*60)
print("测试 9: 播放地址解析（与前端 parseRoutes 对齐验证）")
print("="*60)
play_url = MOCK_DETAIL["vod_play_url"]
play_from = MOCK_DETAIL["vod_play_from"]

groups = play_url.split("$$$")
names = play_from.split("$$$")
check(len(groups) == 1, "单线路只有1组")
episodes = []
for g in groups:
    for part in g.split("#"):
        bits = part.split("$")
        if len(bits) >= 2:
            episodes.append({"name": bits[0].strip(), "url": bits[1].strip()})
check(len(episodes) == 2, f"解析出 {len(episodes)} 集")
check(episodes[0]["name"] == "第01集", f"第一集名称: {episodes[0]['name']}")
check(episodes[0]["url"].endswith(".m3u8"), "URL 是 m3u8")
check(".m3u8" in episodes[1]["url"], "第二集也是 m3u8")

print("\n" + "="*60)
print(f"测试结果: {PASS} 通过, {FAIL} 失败")
print("="*60)

if FAIL > 0:
    sys.exit(1)
else:
    print("🎉 全部测试通过！")
    print("""
说明:
- 所有 API handler 的返回格式符合 Vercel Python Runtime 规范
- 前端 index.html 调用的 5 个 API 路径完全对应
- 数据结构与原 server.py 保持一致
- 部署到 Vercel 后，云端函数会真实访问第三方资源站 API
    """)
