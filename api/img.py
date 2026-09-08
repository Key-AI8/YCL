import json
import sys
import os
import base64

sys.path.append(os.path.dirname(__file__))

from _lib import http_get_binary


def handler(request):
    query = (request.get("query") or {}) if isinstance(request, dict) else {}
    url = _get(query, "url")

    if not url or not url.startswith("http"):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "invalid url"}),
        }

    data, ctype = http_get_binary(url)
    if not data:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "fetch failed"}),
        }

    # Vercel Python: 返回二进制需使用 isBase64Encoded=True
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": ctype or "image/jpeg",
            "Cache-Control": "public, max-age=86400",
        },
        "body": base64.b64encode(data).decode("ascii"),
        "isBase64Encoded": True,
    }


def _get(query, key):
    v = query.get(key) or ""
    return v[0] if isinstance(v, list) else v
