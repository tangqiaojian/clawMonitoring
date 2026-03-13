from __future__ import annotations

import asyncio
import json
import random
import time
from collections import deque
from typing import Any
from urllib.parse import quote

import psutil
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
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


class MockState(BaseModel):
    enabled: bool


class WorkRecordCreate(BaseModel):
    title: str = Field(min_length=1)
    detail: str | None = None
    progress_percent: float | None = None
    status: str = "done"


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


app = FastAPI(title="Lobster Workstation Monitor", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

hub = ConnectionHub()
nodes: dict[str, Node] = {
    "lobster_01": Node(id="lobster_01", name="龙虾一号", status="active"),
    "lobster_02": Node(id="lobster_02", name="龙虾二号", status="idle"),
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

active_lobsters: dict[str, dict[str, Any]] = {}
work_logs: dict[str, deque[dict[str, Any]]] = {}

MOCK_ENABLED = True
AGENT_SCRIPT_VERSION = "2026.03.13.1"


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
        "current_work": "",
        "progress_percent": None,
        "last_completed_work": "",
        "work_updated_at": None,
    }


def _coerce_progress(value: Any) -> float | None:
    if value is None:
        return None
    try:
        p = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(100.0, p))


def _extract_work_record(data: dict[str, Any]) -> tuple[str | None, str | None, str, float | None]:
    work_record = data.get("work_record")
    if isinstance(work_record, str) and work_record.strip():
        return work_record.strip(), None, "done", 100.0

    if isinstance(work_record, dict):
        title = str(work_record.get("title") or "").strip()
        detail = str(work_record.get("detail") or "").strip() or None
        status = str(work_record.get("status") or "done")
        progress = _coerce_progress(work_record.get("progress_percent"))
        return title or None, detail, status, progress

    completed = data.get("completed_work")
    if isinstance(completed, str) and completed.strip():
        return completed.strip(), None, "done", 100.0

    completed_records = data.get("completed_records")
    if isinstance(completed_records, list) and completed_records:
        latest = completed_records[-1]
        if isinstance(latest, str) and latest.strip():
            return latest.strip(), None, "done", 100.0
        if isinstance(latest, dict):
            title = str(latest.get("title") or "").strip()
            detail = str(latest.get("detail") or "").strip() or None
            status = str(latest.get("status") or "done")
            progress = _coerce_progress(latest.get("progress_percent"))
            return title or None, detail, status, progress

    return None, None, "done", None


def _append_work_record(node_id: str, title: str, detail: str | None, status: str, progress: float | None) -> None:
    if not title.strip():
        return
    logs = work_logs.setdefault(node_id, deque(maxlen=300))
    normalized_title = title.strip()
    normalized_detail = (detail or "").strip() or None

    if logs:
        last = logs[-1]
        if (
            last.get("title") == normalized_title
            and (last.get("detail") or "") == (normalized_detail or "")
            and last.get("status") == status
        ):
            return

    logs.append(
        {
            "id": f"{node_id}_{int(_now() * 1000)}_{len(logs)}",
            "node_id": node_id,
            "title": normalized_title,
            "detail": normalized_detail,
            "status": status,
            "progress_percent": progress,
            "timestamp": _now(),
        }
    )


def build_heartbeats(timestamp: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in nodes.values():
        report = active_lobsters.get(node.id)
        last_seen = float(report["_last_seen"]) if report and "_last_seen" in report else None
        if last_seen is None:
            hb_status = "never"
            ago = None
        else:
            ago = max(int(timestamp - last_seen), 0)
            hb_status = "online" if ago <= 15 else "stale"

        rows.append(
            {
                "id": node.id,
                "name": node.name,
                "host": node.host,
                "status": hb_status,
                "last_seen": last_seen,
                "last_seen_ago_sec": ago,
            }
        )
    rows.sort(key=lambda item: item["last_seen"] or 0, reverse=True)
    return rows


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

    stale_ids = [nid for nid, data in active_lobsters.items() if timestamp - data.get("_last_seen", 0) > 15]
    for nid in stale_ids:
        active_lobsters[nid]["status"] = "offline"

    if MOCK_ENABLED:
        simulated = {node.id: _node_runtime(node) for node in nodes.values()}
    else:
        simulated = {
            node.id: {
                "id": node.id,
                "name": node.name,
                "status": "idle",
                "cpu_percent": 0.0,
                "task_count": 0,
                "current_work": "",
                "progress_percent": None,
                "last_completed_work": "",
                "work_updated_at": None,
            }
            for node in nodes.values()
        }

    merged_lobsters = []
    for node_id, sim_data in simulated.items():
        if node_id in active_lobsters:
            report = active_lobsters[node_id]
            progress = _coerce_progress(report.get("progress_percent", report.get("work_progress")))
            current_work = report.get("current_work") or report.get("work_current") or ""
            node_logs = work_logs.get(node_id)
            last_done = node_logs[-1]["title"] if node_logs else ""
            merged_lobsters.append(
                {
                    "id": node_id,
                    "name": report.get("name", nodes[node_id].name),
                    "status": report.get("status", "active"),
                    "cpu_percent": report.get("cpu_percent", 0),
                    "mem_percent": report.get("mem_percent", 0),
                    "task_count": report.get("task_count", 0),
                    "current_work": str(current_work),
                    "progress_percent": progress,
                    "last_completed_work": last_done,
                    "work_updated_at": report.get("_last_seen"),
                }
            )
        else:
            merged_lobsters.append(sim_data)

    return {
        "topic": "resource_stream",
        "timestamp": timestamp,
        "host": host,
        "lobsters": merged_lobsters,
        "heartbeats": build_heartbeats(timestamp),
    }


def _agent_script(server_url: str, node_id: str, node_name: str) -> str:
    return f"""#!/usr/bin/env python3
# Lobster Agent Reporter
# version: {AGENT_SCRIPT_VERSION}
import argparse
import asyncio
import json
import os
import platform
import socket
import time

import psutil
import websockets

DEFAULT_SERVER = \"{server_url}\"
DEFAULT_NODE_ID = \"{node_id}\"
DEFAULT_NODE_NAME = \"{node_name}\"


def build_payload(args, current_work, progress, task_count, done_title, done_detail):
    payload = {{
        \"id\": args.node_id,
        \"name\": args.node_name,
        \"cpu_percent\": psutil.cpu_percent(),
        \"mem_percent\": psutil.virtual_memory().percent,
        \"task_count\": task_count,
        \"status\": \"active\",
        \"current_work\": current_work,
        \"progress_percent\": progress,
        \"work_record\": {{
            \"title\": done_title,
            \"detail\": done_detail,
            \"status\": \"done\",
            \"progress_percent\": 100,
        }} if done_title else None,
        \"agent\": {{
            \"version\": \"{AGENT_SCRIPT_VERSION}\",
            \"hostname\": socket.gethostname(),
            \"platform\": platform.platform(),
            \"pid\": os.getpid(),
            \"ts\": time.time(),
        }},
    }}
    return payload


async def report_loop(args):
    report_url = args.server.rstrip(\"/\") + \"/ws/report\"
    while True:
        try:
            async with websockets.connect(report_url) as ws:
                while True:
                    payload = build_payload(
                        args,
                        current_work=args.current_work,
                        progress=args.progress,
                        task_count=args.task_count,
                        done_title=args.done_title,
                        done_detail=args.done_detail,
                    )
                    await ws.send(json.dumps(payload, ensure_ascii=False))
                    await asyncio.sleep(max(args.interval, 1))
        except Exception:
            await asyncio.sleep(3)


def parse_args():
    parser = argparse.ArgumentParser(description=\"Lobster reporter\")
    parser.add_argument(\"--server\", default=DEFAULT_SERVER, help=\"e.g. http://10.0.0.10:8000\")
    parser.add_argument(\"--node-id\", default=DEFAULT_NODE_ID)
    parser.add_argument(\"--node-name\", default=DEFAULT_NODE_NAME)
    parser.add_argument(\"--interval\", type=int, default=1)
    parser.add_argument(\"--task-count\", type=int, default=1)
    parser.add_argument(\"--current-work\", default=\"巡检中\")
    parser.add_argument(\"--progress\", type=float, default=0)
    parser.add_argument(\"--done-title\", default=\"\")
    parser.add_argument(\"--done-detail\", default=\"\")
    return parser.parse_args()


if __name__ == \"__main__\":
    asyncio.run(report_loop(parse_args()))
"""


def handle_report_message(text_data: str) -> None:
    data = json.loads(text_data)
    if not isinstance(data, dict):
        return
    if "id" not in data or "cpu_percent" not in data:
        return

    node_id = str(data["id"])
    if node_id not in nodes:
        node_name = str(data.get("name", f"Auto Node {node_id}"))
        nodes[node_id] = Node(id=node_id, name=node_name, status="active")

    progress = _coerce_progress(data.get("progress_percent", data.get("work_progress")))
    if progress is not None:
        data["progress_percent"] = progress

    active_lobsters[node_id] = {
        **data,
        "_last_seen": _now(),
    }

    title, detail, status, record_progress = _extract_work_record(data)
    if title:
        _append_work_record(node_id, title, detail, status, record_progress)


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
    active_lobsters.pop(node_id, None)
    work_logs.pop(node_id, None)
    return {"message": "deleted"}


@app.get("/api/history/{metric}")
def metric_history(metric: str, limit: int = 300) -> dict[str, Any]:
    if metric not in history:
        raise HTTPException(status_code=404, detail="metric not found")

    data = list(history[metric])[-limit:]
    return {"metric": metric, "points": data}


@app.get("/api/mock")
def get_mock_state() -> dict[str, bool]:
    return {"enabled": MOCK_ENABLED}


@app.post("/api/mock")
def set_mock_state(state: MockState) -> dict[str, Any]:
    global MOCK_ENABLED
    MOCK_ENABLED = state.enabled
    return {"message": "mock state updated", "enabled": MOCK_ENABLED}


@app.get("/api/heartbeats")
def list_heartbeats() -> dict[str, Any]:
    timestamp = _now()
    return {"timestamp": timestamp, "heartbeats": build_heartbeats(timestamp)}


@app.get("/api/work/{node_id}")
def list_node_work_records(node_id: str, limit: int = Query(default=50, ge=1, le=300)) -> dict[str, Any]:
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="node not found")
    logs = list(work_logs.get(node_id, deque()))[-limit:]
    logs.reverse()
    return {"node_id": node_id, "records": logs}


@app.get("/api/work")
def list_all_work_records(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    merged: list[dict[str, Any]] = []
    for node_id in nodes.keys():
        merged.extend(list(work_logs.get(node_id, deque()))[-limit:])
    merged.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return {"records": merged[:limit]}


@app.post("/api/work/{node_id}")
def create_work_record(node_id: str, req: WorkRecordCreate) -> dict[str, Any]:
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="node not found")
    progress = _coerce_progress(req.progress_percent)
    _append_work_record(node_id, req.title, req.detail, req.status, progress)
    return {"message": "ok"}


@app.get("/api/agent/version")
def agent_version() -> dict[str, str]:
    return {"version": AGENT_SCRIPT_VERSION}


@app.get("/api/agent/script")
def agent_script(
    server_host: str | None = None,
    server_port: int = 8000,
    node_id: str = "lobster_01",
    node_name: str = "龙虾节点",
) -> PlainTextResponse:
    host = (server_host or "127.0.0.1").strip() or "127.0.0.1"
    server_url = f"http://{host}:{server_port}"
    script = _agent_script(server_url=server_url, node_id=node_id, node_name=node_name)
    return PlainTextResponse(script)


@app.get("/api/agent/upgrade-guide")
def agent_upgrade_guide(server_host: str | None = None, server_port: int = 8000, node_id: str = "lobster_01") -> dict[str, str]:
    host = (server_host or "127.0.0.1").strip() or "127.0.0.1"
    encoded_name = quote("龙虾节点")
    script_url = (
        f"http://{host}:{server_port}/api/agent/script"
        f"?server_host={quote(host)}&server_port={server_port}&node_id={quote(node_id)}&node_name={encoded_name}"
    )
    linux_cmd = (
        f"curl -fsSL '{script_url}' -o lobster_agent.py && "
        f"python lobster_agent.py --server http://{host}:{server_port} --node-id {node_id}"
    )
    windows_cmd = (
        f"powershell -Command \"iwr -UseBasicParsing '{script_url}' -OutFile lobster_agent.py; "
        f"python lobster_agent.py --server http://{host}:{server_port} --node-id {node_id}\""
    )
    return {
        "version": AGENT_SCRIPT_VERSION,
        "script_url": script_url,
        "linux_upgrade": linux_cmd,
        "windows_upgrade": windows_cmd,
    }


@app.websocket("/ws/stream")
async def ws_stream_handler(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(ws)
    except Exception:
        hub.disconnect(ws)


@app.websocket("/ws/report")
async def ws_report_handler(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            text_data = await ws.receive_text()
            try:
                handle_report_message(text_data)
            except json.JSONDecodeError:
                continue
    except WebSocketDisconnect:
        return
    except Exception:
        return


@app.websocket("/ws")
async def ws_legacy_handler(ws: WebSocket) -> None:
    await ws.accept()
    is_stream_client = False
    try:
        while True:
            text_data = await ws.receive_text()
            try:
                handle_report_message(text_data)
            except json.JSONDecodeError:
                if not is_stream_client:
                    hub.clients.add(ws)
                    is_stream_client = True
                continue
    except WebSocketDisconnect:
        if is_stream_client:
            hub.disconnect(ws)
    except Exception:
        if is_stream_client:
            hub.disconnect(ws)
