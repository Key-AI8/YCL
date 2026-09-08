# 影视搜索播放器（Vercel Python 版）

原 `server.py`（单文件 Python HTTP 服务器）改造为 Vercel Serverless 架构。
**功能完全保留**：片源切换、国漫周更新、热门、搜索、详情/选集、m3u8 播放、图片代理。

## 目录结构
```
vercel-project/
├── api/
│   ├── _lib.py       共享逻辑（数据源、抓取、解析、缓存、归一化）
│   ├── sources.py    GET /api/sources
│   ├── home.py       GET /api/home
│   ├── search.py     GET /api/search?wd=&source=
│   ├── detail.py     GET /api/detail?source=&id=
│   └── img.py        GET /api/img?url=   (图片代理，base64)
├── index.html        前端（与原版完全一致，无需改动）
└── README.md
```

## 相比原 server.py 的改动
只改「部署形态」，不改功能代码：
1. 把 `server.py` 拆成 `api/` 下多个函数，**每个文件 = 一个 API 路由**（Vercel Python 约定）
2. 共享代码抽到 `api/_lib.py`，各函数 `sys.path.append` 后导入
3. 多线程并发 → 顺序请求（Serverless 不宜大量子线程，且 Vercel 函数有超时限制）
4. 图片代理：`/api/img` 返回 `{body: base64, isBase64Encoded: true}`（Vercel 二进制规范）
5. 进程内缓存保留（同一实例生命周期内有效；跨实例不共享，可接受）

前端 `index.html` **零改动**，调用的 5 个 API 路径完全一致。

## 本地测试
Vercel 官方 CLI（推荐）：
```bash
npm i -g vercel
vercel dev          # 本地启动，自动识别 api/ 为函数
```
或用 Vercel Python Runtime 模拟：
```bash
python -c "from api import _lib; print(_lib.search_one(_lib.SOURCES[0], '仙逆'))"
```

## 部署到 Vercel
1. 把整个 `vercel-project/` 推到 GitHub 仓库
2. vercel.com → Import Project → 选该仓库
   - **Root Directory**：留空（默认根目录）
   - **Framework Preset**：Other（或留空）
   - **Runtime**：Python（Vercel 根据 `api/*.py` 自动识别）
3. Deploy → 访问 `xxx.vercel.app`

Vercel 自动：把 `api/*.py` 编译为云函数、把 `index.html` 作为静态入口。无需额外配置。

## 注意事项
- Vercel 函数默认超时 10s（Hobby）/ 60s（Pro），首页顺序抓取多资源可能偏慢；若超时可在 `vercel.json` 调整 `maxDuration`
- 函数冷启动 + 第三方资源站响应慢，首次加载可能需几秒
- 进程内缓存在 Serverless 环境下跨调用不保证命中，属正常
