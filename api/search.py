import json
import sys
import os

sys.path.append(os.path.dirname(__file__))

from _lib import SOURCES, SOURCE_MAP, cache_get, cache_set, search_one


def handler(request):
    # Vercel Python: request 是 dict-like 对象，query 参数在 request.get("query") 中
    query = (request.get("query") or {}) if isinstance(request, dict) else {}
    keyword = (query.get("wd") or [""])[0].strip() if isinstance(query.get("wd"), list) else (query.get("wd") or "").strip()
    source_id = (query.get("source") or [""])[0].strip() if isinstance(query.get("source"), list) else (query.get("source") or "").strip()

    if not keyword:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"list": []}, ensure_ascii=False),
        }

    cache_key = "search:" + (source_id or "all") + ":" + keyword
    cached = cache_get(cache_key)
    if cached is not None:
        return _resp(cached)

    sources = [SOURCE_MAP[source_id]] if source_id in SOURCE_MAP else SOURCES
    results = []
    seen = set()
    for src in sources:
        items = search_one(src, keyword)
        for it in items:
            name = it.get("vod_name")
            if not name or name in seen:
                continue
            seen.add(name)
            results.append(it)

    cache_set(cache_key, results)
    return _resp(results)


def _resp(results):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"list": results}, ensure_ascii=False),
    }
