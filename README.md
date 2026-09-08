# 影视搜播（Vercel 版）

填站源 → 输剧名 → 搜番 → 点剧出选集 → 点集本页播放。后端为 Vercel 文件型 Python 函数（`api/*.py`），仅用标准库。

## 目录结构

```
.
├── api/
│   ├── _lib.py       共享：数据源/抓取/解析/缓存
│   ├── sources.py    GET /api/sources        数据源列表
│   ├── home.py       GET /api/home?source=   首页精选
│   ├── search.py     GET /api/search?wd=&source=  搜索
│   ├── detail.py     GET /api/detail?url=&source=  选集+直链
│   └── img.py        GET /api/img?url=       图片代理
├── index.html        前端
├── vercel.json       函数超时+排除规则
├── pyproject.toml    项目声明（防 Vercel 误判为框架）
└── test_local.py     本地测试
```

## 本地测试

```bash
python test_local.py
```

## 本地运行（需额外装一个简易 server，可选）

```bash
pip install flask   # 仅本地调试用，非 Vercel 必需
python -c "from flask import Flask; a=Flask(__name__,static_folder='.',static_url_path=''); a.run()"
# 或直接用: python -m http.server 8000   (前端需把 API 指向本地函数)
```

## 部署到 Vercel（3步）

1. 把整个文件夹推到 GitHub 仓库（如 `Zy-api/yszyl`）
2. 打开 https://vercel.com/import → 选该仓库
   - **Root Directory**：留空（默认根目录）
   - **Framework Preset**：选 `Other`（不要选 Python）
3. Deploy → 访问 `xxx.vercel.app`

> ⚠️ **不要**在根目录放 `requirements.txt` / `runtime.txt`（会触发 Vercel 去找 `app.py` 入口，报 `No python entrypoint found`）。本项目纯标准库，`pyproject.toml` 已声明入口为 `api.sources:handler`。

## 新增数据源

编辑 `api/_lib.py` 的 `SOURCES`，按模板加一项即可（搜索/详情/播放的 URL 规则需符合苹果CMS体系）。

## 排查

- 搜索/选集为空：多半是目标站 HTML 结构不匹配，在 `api/_lib.py` 的 `parse_listing` / `parse_detail` 调整正则。
- 视频 403：直链有 Referer/签名校验，前端可走 `/api/img` 思路再加一个视频代理；强校验需后端补 Header。
- 构建报 `No python entrypoint`：确认根目录无 `requirements.txt`，且 `pyproject.toml` 存在。
