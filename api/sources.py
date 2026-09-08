import json
import sys
import os

# 确保 api 目录在 path 中，以便导入 _lib
sys.path.append(os.path.dirname(__file__))

from _lib import SOURCES


def handler(request):
    items = [{"id": s["id"], "name": s["name"]} for s in SOURCES]
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"list": items}, ensure_ascii=False),
    }
