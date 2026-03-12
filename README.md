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
- `GET /api/nodes`
- `POST /api/nodes`
- `DELETE /api/nodes/{id}`
- `GET /api/history/{metric}`
- `WS /ws`（实时推送 `resource_stream`）

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
