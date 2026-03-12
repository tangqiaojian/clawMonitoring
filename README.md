# 电脑资源监控与龙虾工作站（V1）

基于你的需求文档实现的首版可运行项目：
- 前端：Vue 3 + TypeScript + Vite + Pinia
- 后端：FastAPI + psutil + WebSocket
- 风格：Liquid Glassmorphism（液态玻璃）
- 功能：主机资源实时监控 + 龙虾节点可视化 + 节点增删管理

## 目录结构

```text
.
├── backend
│   ├── app/main.py
│   └── requirements.txt
├── frontend
│   ├── src
│   └── package.json
└── docker-compose.yml
```

## 项目启动说明

### 环境要求

- Node.js 18+
- Python 3.10+
- npm / pip
- （可选）Docker Desktop（用于容器方式启动）

### 启动方式一：本地开发启动（推荐）

1. 启动后端（FastAPI）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. 新开一个终端，启动前端（Vite）

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

3. 访问地址

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`

### 启动方式二：Docker 启动

```bash
docker compose up --build
```

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`

### 启动方式三：Windows 一键启动

双击根目录 `onekey-deploy-start.bat`，或执行：

```powershell
.\scripts\onekey-deploy-start.ps1
```

停止服务：

```powershell
.\scripts\stop-services.ps1
```

### 服务器部署说明（无反向代理也可用）

- 前端默认会自动连接：`http(s)://当前页面域名:8000`
- WebSocket 默认会自动连接：`ws(s)://当前页面域名:8000/ws/stream`
- 如果你的后端不是 `8000` 端口，请在前端启动前设置：

```bash
VITE_API_BASE=http://你的后端地址:端口
VITE_WS_BASE=ws://你的后端地址:端口/ws/stream
```

### 龙虾节点接入（推荐新通道）

- 前端监控订阅通道：`/ws/stream`
- 龙虾节点上报通道：`/ws/report`
- 兼容旧通道：`/ws`（不建议新接入继续使用）

## 快速启动（本地）

### 1) 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

浏览器访问：`http://127.0.0.1:5173`

## Docker 启动

```bash
docker compose up --build
```

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`

## 已实现接口

- `GET /api/health`
- `GET /api/snapshot`
- `GET /api/nodes`
- `POST /api/nodes`
- `DELETE /api/nodes/{id}`
- `GET /api/history/{metric}`
- `GET /api/heartbeats`（查看节点心跳）
- `WS /ws/stream`（前端实时订阅 `resource_stream`）
- `WS /ws/report`（龙虾节点实时上报）
- `WS /ws`（兼容历史混合模式）

## 当前覆盖的需求点

- 1 秒级实时推送：CPU/内存/网络/节点状态
- GPU 监控：支持 NVML 环境自动读取，未安装时降级
- 龙虾工作空间：状态映射（active/warning/offline/idle）
- 节点管理：前端表单增删节点
- 液态玻璃视觉：模糊玻璃卡片、流动背景、状态色

## 下一步建议

- 接入 ECharts 多指标历史曲线与液态进度图
- 细分采样频率（磁盘 5 秒、GPU 2 秒）并做差分速率
- 增加阈值报警中心与动画事件总线
- 3D 拟态人（Three.js 或 Spline）替换当前 2D Avatar
- SQLite 历史存储与报表导出
