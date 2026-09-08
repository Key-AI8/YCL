import json
import sys
import os

sys.path.append(os.path.dirname(__file__))

from _lib import load_home


def handler(request):
    try:
        payload = load_home()
        body = json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        body = json.dumps({"week": {}, "hot": [], "error": str(e)}, ensure_ascii=False)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "public, max-age=60",
            "Access-Control-Allow-Origin": "*",
        },
        "body": body,
    }
