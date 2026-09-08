import json
import sys
import os

sys.path.append(os.path.dirname(__file__))

from _lib import detail_one


def handler(request):
    query = (request.get("query") or {}) if isinstance(request, dict) else {}
    source_id = _get(query, "source")
    vod_id = _get(query, "id")

    item = detail_one(source_id, vod_id)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"item": item}, ensure_ascii=False),
    }


def _get(query, key):
    v = query.get(key) or ""
    return v[0] if isinstance(v, list) else v
