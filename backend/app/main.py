from __future__ import annotations

import asyncio
import random
import time
from collections import deque
from typing import Any

import psutil
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from pynvml import (
        nvmlDeviceGetCount,
        nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetMemoryInfo,
        nvmlDeviceGetName,
        nvmlDeviceGetTemperature,
        nvmlDeviceGetUtilizationRates,
        nvmlInit,
    )

    NVIDIA_AVAILABLE = True
except Exception:
    NVIDIA_AVAILABLE = False


class Node(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    host: str = "127.0.0.1"
    token: str | None = None
    status: str = "idle"
    created_at: float = Field(default_factory=time.time)


class NodeCreate(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    host: str = "127.0.0.1"
    token: str | None = None


class ConnectionHub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for client in self.clients:
            try:
                await client.send_json(payload)
            except Exception:
                stale.append(client)

        for client in stale:
            self.disconnect(client)


app = FastAPI(title="Lobster Workstation Monitor", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

hub = ConnectionHub()
nodes: dict[str, Node] = {
    "lobster_01": Node(id="lobster_01", name="虾兵蟹将一号", status="active"),
    "lobster_02": Node(id="lobster_02", name="皮皮虾先锋", status="idle"),
    "lobster_03": Node(id="lobster_03", name="深海算子", status="warning"),
}
history: dict[str, deque[dict[str, float]]] = {
    "cpu": deque(maxlen=7200),
    "memory": deque(maxlen=7200),
    "network_up": deque(maxlen=7200),
    "network_down": deque(maxlen=7200),
    "disk": deque(maxlen=1440),
    "gpu": deque(maxlen=3600),
}

# 存储真实上报的节点数据
active_lobsters: dict[str, dict[str, Any]] = {}  

# 全局 Mock 数据开关
MOCK_ENABLED = True

def _now() -> float:
    return time.time()


def _safe_disk() -> dict[str, Any]:
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue

        partitions.append(
            {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "used": usage.used,
                "total": usage.total,
                "percent": usage.percent,
            }
        )

    io = psutil.disk_io_counters() or None
    return {
        "partitions": partitions,
        "io_read_bytes": getattr(io, "read_bytes", 0),
        "io_write_bytes": getattr(io, "write_bytes", 0),
    }


def _safe_gpu() -> dict[str, Any]:
    if not NVIDIA_AVAILABLE:
        return {
            "vendor": "unavailable",
            "load": 0.0,
            "memory_used": 0,
            "memory_total": 0,
            "temperature": None,
            "name": "No NVIDIA GPU / NVML unavailable",
        }

    try:
        nvmlInit()
        if nvmlDeviceGetCount() == 0:
            return {
                "vendor": "nvidia",
                "load": 0.0,
                "memory_used": 0,
                "memory_total": 0,
                "temperature": None,
                "name": "No GPU found",
            }

        handle = nvmlDeviceGetHandleByIndex(0)
        util = nvmlDeviceGetUtilizationRates(handle)
        mem = nvmlDeviceGetMemoryInfo(handle)
        temp = nvmlDeviceGetTemperature(handle, 0)

        return {
            "vendor": "nvidia",
            "name": str(nvmlDeviceGetName(handle)),
            "load": float(util.gpu),
            "memory_used": int(mem.used),
            "memory_total": int(mem.total),
            "temperature": int(temp),
        }
    except Exception:
        return {
            "vendor": "error",
            "load": 0.0,
            "memory_used": 0,
            "memory_total": 0,
            "temperature": None,
            "name": "GPU query failed",
        }


def _node_runtime(node: Node) -> dict[str, Any]:
    cpu = random.uniform(5, 95)
    task_count = int(cpu // 20) + random.randint(0, 2)
    if node.status == "offline":
        cpu = 0
        task_count = 0
    elif node.status == "idle":
        cpu = random.uniform(2, 15)
        task_count = random.randint(0, 1)

    if cpu > 80:
        dynamic_status = "warning"
    elif cpu < 10:
        dynamic_status = "idle"
    else:
        dynamic_status = "active"

    if node.status == "offline":
        dynamic_status = "offline"

    return {
        "id": node.id,
        "name": node.name,
        "status": dynamic_status,
        "cpu_percent": round(cpu, 1),
        "task_count": task_count,
    }


def sample_metrics() -> dict[str, Any]:
    timestamp = _now()
    cpu_percent = psutil.cpu_percent(interval=None)
    per_cpu = psutil.cpu_percent(interval=None, percpu=True)
    cpu_freq = psutil.cpu_freq()
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    net = psutil.net_io_counters()
    disk = _safe_disk()
    gpu = _safe_gpu()

    host = {
        "cpu_percent": round(cpu_percent, 1),
        "cpu_cores": [round(v, 1) for v in per_cpu],
        "cpu_freq": round(cpu_freq.current, 1) if cpu_freq else None,
        "mem_percent": round(vm.percent, 1),
        "mem_used": vm.used,
        "mem_total": vm.total,
        "swap_percent": round(sm.percent, 1),
        "network_up": net.bytes_sent,
        "network_down": net.bytes_recv,
        "disk": disk,
        "gpu": gpu,
    }

    history["cpu"].append({"t": timestamp, "v": host["cpu_percent"]})
    history["memory"].append({"t": timestamp, "v": host["mem_percent"]})
    history["network_up"].append({"t": timestamp, "v": host["network_up"]})
    history["network_down"].append({"t": timestamp, "v": host["network_down"]})
    history["disk"].append({"t": timestamp, "v": disk["io_read_bytes"] + disk["io_write_bytes"]})
    history["gpu"].append({"t": timestamp, "v": host["gpu"]["load"]})

    # 清理超时的上报节点 (超过 15 秒没信算离线)
    stale_ids = [nid for nid, data in active_lobsters.items() if timestamp - data.get("_last_seen", 0) > 15]
    for nid in stale_ids:
        if nid in active_lobsters:
            active_lobsters[nid]["status"] = "offline"

    # 1. 生成模拟数据 (受 MOCK_ENABLED 控制)
    simulated = {}
    if MOCK_ENABLED:
        simulated = {node.id: _node_runtime(node) for node in nodes.values()}
    else:
        # 如果关闭 Mock，只保留 nodes 列表里的基础设施占位，状态默认置为 idle
        simulated = {node.id: {
            "id": node.id,
            "name": node.name,
            "status": "idle",
            "cpu_percent": 0.0,
            "task_count": 0,
        } for node in nodes.values()}
    
    # 2. 合并真实上报数据（覆盖模拟数据）
    merged_lobsters = []
    for node_id, sim_data in simulated.items():
        if node_id in active_lobsters:
            merged_lobsters.append({
                "id": node_id,
                "name": active_lobsters[node_id].get("name", nodes[node_id].name),
                "status": active_lobsters[node_id].get("status", "active"),
                "cpu_percent": active_lobsters[node_id].get("cpu_percent", 0),
                "mem_percent": active_lobsters[node_id].get("mem_percent", 0), # 增加内存支持
                "task_count": active_lobsters[node_id].get("task_count", 0),
            })
        else:
            merged_lobsters.append(sim_data)

    payload = {
        "topic": "resource_stream",
        "timestamp": timestamp,
        "host": host,
        "lobsters": merged_lobsters,
    }
    return payload


@app.on_event("startup")
async def startup_task() -> None:
    async def push_loop() -> None:
        while True:
            payload = sample_metrics()
            await hub.broadcast(payload)
            await asyncio.sleep(1)

    asyncio.create_task(push_loop())


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/snapshot")
def snapshot() -> dict[str, Any]:
    return sample_metrics()


@app.get("/api/nodes")
def list_nodes() -> list[Node]:
    return list(nodes.values())


@app.post("/api/nodes", response_model=Node)
def create_node(req: NodeCreate) -> Node:
    if req.id in nodes:
        raise HTTPException(status_code=409, detail="node id already exists")

    node = Node(id=req.id, name=req.name, host=req.host, token=req.token)
    nodes[node.id] = node
    return node


@app.delete("/api/nodes/{node_id}")
def remove_node(node_id: str) -> dict[str, str]:
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="node not found")

    del nodes[node_id]
    return {"message": "deleted"}


@app.get("/api/history/{metric}")
def metric_history(metric: str, limit: int = 300) -> dict[str, Any]:
    if metric not in history:
        raise HTTPException(status_code=404, detail="metric not found")

    data = list(history[metric])[-limit:]
    return {"metric": metric, "points": data}


class MockState(BaseModel):
    enabled: bool

@app.get("/api/mock")
def get_mock_state() -> dict[str, bool]:
    return {"enabled": MOCK_ENABLED}

@app.post("/api/mock")
def set_mock_state(state: MockState) -> dict[str, Any]:
    global MOCK_ENABLED
    MOCK_ENABLED = state.enabled
    return {"message": "mock state updated", "enabled": MOCK_ENABLED}


@app.websocket("/ws")
async def ws_handler(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        while True:
            # 接收客户端上报的数据
            text_data = await ws.receive_text()
            try:
                import json
                data = json.loads(text_data)
                
                # 如果包含特定字段，视为节点主动上报
                if isinstance(data, dict) and "id" in data and "cpu_percent" in data:
                    node_id = data["id"]
                    
                    # 1. 自动添加到 nodes
                    if node_id not in nodes:
                        node_name = data.get("name", f"Auto Node {node_id}")
                        nodes[node_id] = Node(id=node_id, name=node_name, status="active")
                    
                    # 2. 更新真实上报记录
                    active_lobsters[node_id] = {
                        **data,
                        "_last_seen": _now(),
                    }
            except json.JSONDecodeError:
                # 忽略非 JSON 数据（如前端的 'subscribe:resource_stream'）
                pass

    except WebSocketDisconnect:
        hub.disconnect(ws)
    except Exception:
        # 有可能接收到非 JSON 数据，忽略并断开
        hub.disconnect(ws)
