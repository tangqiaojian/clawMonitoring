<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useMonitorStore } from '../stores/monitor'
import type { LobsterHeartbeat } from '../types/monitor'
import { API_BASE } from '../utils/endpoints'
import MetricCard from '../components/MetricCard.vue'
import LobsterAvatar from '../components/LobsterAvatar.vue'
import HistoryChart from '../components/HistoryChart.vue'
import NodeDetailModal from '../components/NodeDetailModal.vue'
import AlertPopup from '../components/AlertPopup.vue'
import AlertNotification from '../components/AlertNotification.vue'

type Point = { t: number; v: number }
type HostSeriesKey = 'cpu' | 'memory' | 'gpu' | 'network'

const HISTORY_LIMIT = 60

const store = useMonitorStore()
const { connected, payload, lobsterStats, nodes } = storeToRefs(store)

const form = ref({ id: '', name: '', host: '127.0.0.1' })
const error = ref('')
const serverHost = ref(window.location.hostname === 'localhost' ? '' : window.location.hostname)
const serverPort = ref(8000)

const host = computed(() => payload.value?.host)
const hostHistory = ref<Record<HostSeriesKey, Point[]>>({
  cpu: [],
  memory: [],
  gpu: [],
  network: [],
})
const nodeHistory = ref<Record<string, { cpu: Point[]; task: Point[] }>>({})
const lastNetwork = ref<{ up: number; down: number; t: number } | null>(null)

const selectedNodeId = ref<string | null>(null)
const detailOpen = ref(false)
const alertVisible = ref(true)
const mockEnabled = ref(true)

// 获取初始 mock 状态
async function fetchMockState() {
  try {
    const res = await fetch(`${API_BASE}/api/mock`)
    if (res.ok) {
      const data = await res.json()
      mockEnabled.value = data.enabled
    }
  } catch (err) {
    console.error('Failed to load mock state', err)
  }
}

// 切换 mock 状态
async function toggleMockState(event: Event) {
  const target = event.target as HTMLInputElement
  const newState = target.checked
  try {
    const res = await fetch(`${API_BASE}/api/mock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: newState })
    })
    if (!res.ok) {
      // 失败则恢复状态
      mockEnabled.value = !newState
    }
  } catch (err) {
    console.error('Failed to update mock state', err)
    mockEnabled.value = !newState
  }
}

// 告警记录
interface AlertRecord {
  id: string
  message: string
  timestamp: number
  type: 'cpu' | 'memory' | 'gpu' | 'node'
  source: string
}

const alertHistory = ref<AlertRecord[]>([])
const lastAlertTime = ref<Record<string, number>>({}) // 记录每个设备最后一次告警的时间

// 从localStorage加载保存的阈值，默认值为初始值
const loadThresholds = () => {
  const saved = localStorage.getItem('monitor_thresholds')
  if (saved) {
    try {
      return JSON.parse(saved)
    } catch {
      return {
        cpu: 80,
        memory: 80,
        gpu: 85,
        nodeCpu: 85,
        alertCooldown: 60, // 默认 60 秒
      }
    }
  }
  return {
    cpu: 80,
    memory: 80,
    gpu: 85,
    nodeCpu: 85,
    alertCooldown: 60,
  }
}

const thresholds = ref(loadThresholds())

const memLabel = computed(() => {
  if (!host.value) return '--'
  const used = host.value.mem_used / 1024 / 1024 / 1024
  const total = host.value.mem_total / 1024 / 1024 / 1024
  return `${used.toFixed(1)} / ${total.toFixed(1)} GB`
})

const netLabel = computed(() => {
  if (!host.value) return '--'
  const up = (host.value.network_up / 1024 / 1024).toFixed(1)
  const down = (host.value.network_down / 1024 / 1024).toFixed(1)
  return `↑ ${up} MB  ↓ ${down} MB`
})

const selectedLobster = computed(() => {
  if (!selectedNodeId.value || !payload.value) return null
  return payload.value.lobsters.find((item) => item.id === selectedNodeId.value) ?? null
})

const selectedNodeCpuHistory = computed(() => {
  if (!selectedNodeId.value) return []
  return nodeHistory.value[selectedNodeId.value]?.cpu ?? []
})

const selectedNodeTaskHistory = computed(() => {
  if (!selectedNodeId.value) return []
  return nodeHistory.value[selectedNodeId.value]?.task ?? []
})

const heartbeats = computed<LobsterHeartbeat[]>(() => payload.value?.heartbeats ?? [])

const reportWsUrl = computed(() => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = serverHost.value.trim() || window.location.hostname
  return `${protocol}://${host}:${serverPort.value}/ws/report`
})

const lobsterScript = computed(() => `import asyncio
import json
import psutil
import websockets

NODE_ID = "lobster_01"
NODE_NAME = "龙虾节点01"
REPORT_URL = "${reportWsUrl.value}"

async def report():
    async with websockets.connect(REPORT_URL) as ws:
        while True:
            payload = {
                "id": NODE_ID,
                "name": NODE_NAME,
                "cpu_percent": psutil.cpu_percent(),
                "mem_percent": psutil.virtual_memory().percent,
                "task_count": 0,
                "status": "active"
            }
            await ws.send(json.dumps(payload))
            await asyncio.sleep(1)

asyncio.run(report())
`)

function formatHeartbeatTime(ts: number | null): string {
  if (!ts) return '从未上报'
  return new Date(ts * 1000).toLocaleString()
}

const alertMessages = computed(() => {
  const result: string[] = []
  const h = host.value
  if (!h || !payload.value) return result

  const now = Date.now()
  const currentCooldown = (thresholds.value.alertCooldown || 60) * 1000
  const newAlerts: AlertRecord[] = []

  // 主机CPU告警
  if (h.cpu_percent >= thresholds.value.cpu) {
    const message = `主机 CPU ${h.cpu_percent.toFixed(1)}% 超过阈值 ${thresholds.value.cpu}%`
    result.push(message)
    const source = 'host_cpu'
    if (!lastAlertTime.value[source] || now - lastAlertTime.value[source] >= currentCooldown) {
      newAlerts.push({
        id: `${source}_${now}`,
        message,
        timestamp: now,
        type: 'cpu',
        source
      })
      lastAlertTime.value[source] = now
    }
  }

  // 主机内存告警
  if (h.mem_percent >= thresholds.value.memory) {
    const message = `主机内存 ${h.mem_percent.toFixed(1)}% 超过阈值 ${thresholds.value.memory}%`
    result.push(message)
    const source = 'host_memory'
    if (!lastAlertTime.value[source] || now - lastAlertTime.value[source] >= currentCooldown) {
      newAlerts.push({
        id: `${source}_${now}`,
        message,
        timestamp: now,
        type: 'memory',
        source
      })
      lastAlertTime.value[source] = now
    }
  }

  // GPU告警
  if (h.gpu.load >= thresholds.value.gpu) {
    const message = `GPU ${h.gpu.load.toFixed(1)}% 超过阈值 ${thresholds.value.gpu}%`
    result.push(message)
    const source = 'host_gpu'
    if (!lastAlertTime.value[source] || now - lastAlertTime.value[source] >= currentCooldown) {
      newAlerts.push({
        id: `${source}_${now}`,
        message,
        timestamp: now,
        type: 'gpu',
        source
      })
      lastAlertTime.value[source] = now
    }
  }

  // 节点CPU告警
  payload.value.lobsters
    .filter((item) => item.cpu_percent >= thresholds.value.nodeCpu)
    .forEach((item) => {
      const message = `${item.name} CPU ${item.cpu_percent.toFixed(1)}% 过高`
      result.push(message)
      const source = `node_${item.id}`
      if (!lastAlertTime.value[source] || now - lastAlertTime.value[source] >= currentCooldown) {
        newAlerts.push({
          id: `${source}_${now}`,
          message,
          timestamp: now,
          type: 'node',
          source
        })
        lastAlertTime.value[source] = now
      }
    })

  // 添加新的告警到历史记录，最多保留10条
  if (newAlerts.length > 0) {
    alertHistory.value = [...newAlerts, ...alertHistory.value].slice(0, 10)
  }

  return result
})

function pushSeries(target: Point[], point: Point) {
  target.push(point)
  if (target.length > HISTORY_LIMIT) {
    target.shift()
  }
}

function hydrateHostHistory(items: Point[], targetKey: HostSeriesKey) {
  const trimmed = items.slice(-HISTORY_LIMIT)
  hostHistory.value[targetKey] = trimmed
}

async function preloadHistory() {
  const [cpu, memory, gpu, networkDown] = await Promise.all([
    store.fetchHistory('cpu', HISTORY_LIMIT),
    store.fetchHistory('memory', HISTORY_LIMIT),
    store.fetchHistory('gpu', HISTORY_LIMIT),
    store.fetchHistory('network_down', HISTORY_LIMIT),
  ])

  hydrateHostHistory(cpu, 'cpu')
  hydrateHostHistory(memory, 'memory')
  hydrateHostHistory(gpu, 'gpu')
  hydrateHostHistory(networkDown, 'network')
}

async function onAddNode() {
  try {
    error.value = ''
    await store.addNode({
      id: form.value.id.trim(),
      name: form.value.name.trim(),
      host: form.value.host.trim(),
    })
    form.value.id = ''
    form.value.name = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '添加失败'
  }
}

async function onRemove(id: string) {
  try {
    await store.removeNode(id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除失败'
  }
}

function openDetail(id: string) {
  selectedNodeId.value = id
  detailOpen.value = true
}

function closeAlert() {
  alertVisible.value = false
}

function saveThresholds() {
  localStorage.setItem('monitor_thresholds', JSON.stringify(thresholds.value))
  alert('阈值设置已保存')
}

function clearAlertHistory() {
  alertHistory.value = []
  lastAlertTime.value = {}
}

watch(alertMessages, (newMessages, oldMessages) => {
  // 当有新的告警产生时（从无到有，或者数量增加），自动显示弹窗
  if (newMessages.length > 0 && newMessages.length > oldMessages.length) {
    alertVisible.value = true
  }
  // 当所有告警都消除时，隐藏弹窗
  if (newMessages.length === 0) {
    alertVisible.value = false
  }
}, { deep: true })

watch(payload, (next) => {
  if (!next) return

  pushSeries(hostHistory.value.cpu, { t: next.timestamp, v: next.host.cpu_percent })
  pushSeries(hostHistory.value.memory, { t: next.timestamp, v: next.host.mem_percent })
  pushSeries(hostHistory.value.gpu, { t: next.timestamp, v: next.host.gpu.load })

  if (lastNetwork.value) {
    const dt = Math.max(next.timestamp - lastNetwork.value.t, 1)
    const deltaUp = Math.max(next.host.network_up - lastNetwork.value.up, 0)
    const deltaDown = Math.max(next.host.network_down - lastNetwork.value.down, 0)
    const speed = (deltaUp + deltaDown) / dt / 1024 / 1024
    pushSeries(hostHistory.value.network, { t: next.timestamp, v: speed })
  }

  lastNetwork.value = {
    up: next.host.network_up,
    down: next.host.network_down,
    t: next.timestamp,
  }

  next.lobsters.forEach((item) => {
    if (!nodeHistory.value[item.id]) {
      nodeHistory.value[item.id] = { cpu: [], task: [] }
    }
    const entry = nodeHistory.value[item.id]!
    pushSeries(entry.cpu, { t: next.timestamp, v: item.cpu_percent })
    pushSeries(entry.task, { t: next.timestamp, v: item.task_count })
  })
})

onMounted(async () => {
  try {
    await store.fetchNodes()
    await preloadHistory()
  } catch {
    error.value = '后端未连接，请先启动 FastAPI 服务。'
  }
  store.connect()
  store.startPolling()
  await fetchMockState()
})

onBeforeUnmount(() => {
  store.disconnect()
  store.stopPolling()
})
</script>

<template>
  <div class="page" :data-alert="alertMessages.length > 0">
    <div class="aurora a1" />
    <div class="aurora a2" />

    <!-- 告警弹窗 -->
    <AlertPopup 
      v-if="alertVisible && alertMessages.length > 0" 
      :messages="alertMessages" 
      @close="closeAlert" 
    />

    <header class="glass-card topbar">
      <div class="topbar-content">
        <div class="topbar-info">
          <h1>龙虾工作站</h1>
          <p>Liquid Glass 资源监控系统</p>
          <span class="badge" :data-online="connected">{{ connected ? '实时连接中' : '重连中' }}</span>
        </div>
        <AlertNotification 
          :alerts="alertHistory" 
          :total="alertMessages.length" 
          @clear="clearAlertHistory" 
        />
      </div>
    </header>

    <section class="metrics-grid">
      <MetricCard title="CPU" :value="`${host?.cpu_percent?.toFixed(1) ?? '--'}%`" subtitle="1秒刷新" :tone="host && host.cpu_percent > thresholds.cpu ? 'danger' : 'ok'" />
      <MetricCard title="内存" :value="`${host?.mem_percent?.toFixed(1) ?? '--'}%`" :subtitle="memLabel" :tone="host && host.mem_percent > thresholds.memory ? 'warn' : 'normal'" />
      <MetricCard title="GPU" :value="`${host?.gpu?.load?.toFixed(1) ?? '--'}%`" :subtitle="host?.gpu?.name ?? 'N/A'" :tone="host && host.gpu.load > thresholds.gpu ? 'danger' : 'normal'" />
      <MetricCard title="网络" :value="netLabel" subtitle="累计上下行" />
    </section>

    <section class="glass-card chart-grid">
      <HistoryChart title="CPU 使用率趋势" :points="hostHistory.cpu" color="#06B6D4" suffix="%" />
      <HistoryChart title="内存使用率趋势" :points="hostHistory.memory" color="#10B981" suffix="%" />
      <HistoryChart title="GPU 负载趋势" :points="hostHistory.gpu" color="#F59E0B" suffix="%" />
      <HistoryChart title="网络吞吐趋势" :points="hostHistory.network" color="#60A5FA" suffix=" MB/s" />
    </section>

    <section class="glass-card workspace">
      <div class="workspace-head">
        <h2>Lobster Workspace</h2>
        <div class="stats">
          <span>总数 {{ lobsterStats.total }}</span>
          <span>在线 {{ lobsterStats.active }}</span>
          <span>空闲 {{ lobsterStats.idle }}</span>
          <span>离线 {{ lobsterStats.offline }}</span>
          <span>警告 {{ lobsterStats.warning }}</span>
        </div>
      </div>
      <div class="lobster-grid">
        <LobsterAvatar v-for="lobster in payload?.lobsters ?? []" :key="lobster.id" :lobster="lobster" @select="openDetail" />
      </div>
    </section>

    <section class="glass-card panel">
      <div class="panel-header">
        <h3>配置设置</h3>
        <button class="save-btn" @click="saveThresholds">保存设置</button>
      </div>
      <div class="thresholds">
        <label>CPU {{ thresholds.cpu }}%
          <input v-model.number="thresholds.cpu" type="range" min="5" max="95" />
        </label>
        <label>内存 {{ thresholds.memory }}%
          <input v-model.number="thresholds.memory" type="range" min="5" max="95" />
        </label>
        <label>GPU {{ thresholds.gpu }}%
          <input v-model.number="thresholds.gpu" type="range" min="5" max="95" />
        </label>
        <label>节点CPU {{ thresholds.nodeCpu }}%
          <input v-model.number="thresholds.nodeCpu" type="range" min="5" max="95" />
        </label>
        <label>报警冷却 {{ thresholds.alertCooldown }}秒
          <input v-model.number="thresholds.alertCooldown" type="range" min="5" max="300" step="5" />
        </label>
        <label class="toggle-mock">
          模拟数据 (Mock)
          <input type="checkbox" v-model="mockEnabled" @change="toggleMockState" />
        </label>
      </div>
    </section>

    <!-- ========= 节点管理与接入教程容器 ========= -->
    <div class="bottom-panels">
      <section class="glass-card panel node-panel" id="node-panel-anchor">
        <h3>管理节点</h3>
        <form class="node-form" @submit.prevent="onAddNode">
          <input v-model="form.id" placeholder="id，如 lobster_10" required />
          <input v-model="form.name" placeholder="显示名称" required />
          <input v-model="form.host" placeholder="IP / Host" required />
          <button type="submit">添加节点</button>
        </form>
        <p v-if="error" class="error">{{ error }}</p>
        <ul class="node-list">
          <li v-for="node in nodes" :key="node.id">
            <span>{{ node.name }} <small>({{ node.id }}) @ {{ node.host }}</small></span>
            <button class="remove-btn" @click="onRemove(node.id)">移除</button>
          </li>
        </ul>

        <div class="heartbeat-box">
          <h4>实时心跳</h4>
          <ul class="heartbeat-list">
            <li v-for="beat in heartbeats" :key="beat.id">
              <div>
                <strong>{{ beat.name }}</strong>
                <small>{{ beat.id }} @ {{ beat.host }}</small>
              </div>
              <div class="heartbeat-meta">
                <span class="heartbeat-state" :data-state="beat.status">{{ beat.status }}</span>
                <small>{{ beat.last_seen_ago_sec === null ? '未上报' : `${beat.last_seen_ago_sec}s 前` }}</small>
                <small>{{ formatHeartbeatTime(beat.last_seen) }}</small>
              </div>
            </li>
          </ul>
        </div>
      </section>

      <section class="glass-card panel tutorial-panel">
        <h3><span class="icon">🦞</span> 节点接入教程</h3>
        <div class="tutorial-content">
          <p>把下面教程整段发给“龙虾”同事，只需要告诉他你的服务器 IP 即可接入。</p>
          <div class="tutorial-host-inputs">
            <label>服务器 IP/域名
              <input v-model="serverHost" placeholder="例如 10.10.10.88 或 monitor.example.com" />
            </label>
            <label>后端端口
              <input v-model.number="serverPort" type="number" min="1" max="65535" />
            </label>
          </div>
          <p class="ws-preview">上报地址：<code>{{ reportWsUrl }}</code></p>
          <ol>
            <li>在控制台点击“添加节点”注册新实例。</li>
            <li>在目标机器上安装依赖：<code>pip install psutil websockets</code></li>
            <li>将以下脚本保存为 <code>lobster_report.py</code> 并运行。</li>
          </ol>
          <pre><code>{{ lobsterScript }}</code></pre>
        </div>
      </section>
    </div>



    <NodeDetailModal
      :open="detailOpen"
      :lobster="selectedLobster"
      :cpu-points="selectedNodeCpuHistory"
      :task-points="selectedNodeTaskHistory"
      @close="detailOpen = false"
    />
  </div>
</template>

<style scoped>
/* =========== 底层容器排版 =========== */
.bottom-panels {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 20px;
  width: 100%;
  max-width: 1200px;
  margin-top: 10px;
}

@media (max-width: 900px) {
  .bottom-panels {
    grid-template-columns: 1fr;
  }
}

/* =========== 节点面板 =========== */
.node-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.heartbeat-box {
  margin-top: 8px;
  border-top: 1px solid rgba(148, 163, 184, 0.25);
  padding-top: 12px;
}

.heartbeat-box h4 {
  margin: 0 0 8px;
  color: #bfdbfe;
}

.heartbeat-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 240px;
  overflow: auto;
}

.heartbeat-list li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.35);
}

.heartbeat-list strong {
  display: block;
  color: #e2e8f0;
}

.heartbeat-list small {
  color: #94a3b8;
  font-family: monospace;
}

.heartbeat-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.heartbeat-state {
  font-size: 0.78rem;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
}

.heartbeat-state[data-state='online'] {
  color: #34d399;
  border-color: rgba(52, 211, 153, 0.35);
}

.heartbeat-state[data-state='stale'] {
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.35);
}

.heartbeat-state[data-state='never'] {
  color: #94a3b8;
  border-color: rgba(148, 163, 184, 0.35);
}

.node-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  border-left: 3px solid #8B5CF6;
}

.node-list li span {
  font-size: 0.9rem;
  color: #F8FAFC;
}

.node-list li small {
  color: #94A3B8;
  font-family: monospace;
}

.remove-btn {
  background: rgba(239, 68, 68, 0.1);
  color: #F87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #F87171;
}

/* =========== 教程面板 =========== */
.tutorial-panel h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #10B981;
}

.tutorial-content p {
  color: #E2E8F0;
  margin-bottom: 12px;
  font-size: 0.95rem;
}

.tutorial-host-inputs {
  display: grid;
  grid-template-columns: 1fr 160px;
  gap: 10px;
  margin-bottom: 12px;
}

.tutorial-host-inputs label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #cbd5e1;
  font-size: 0.85rem;
}

.tutorial-host-inputs input {
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.45);
  color: #e2e8f0;
  padding: 8px 10px;
}

.ws-preview {
  margin-top: 4px;
}

@media (max-width: 900px) {
  .tutorial-host-inputs {
    grid-template-columns: 1fr;
  }
}

.tutorial-content ol {
  color: #CBD5E1;
  margin-bottom: 16px;
  padding-left: 20px;
  font-size: 0.9rem;
  line-height: 1.6;
}

.tutorial-content li {
  margin-bottom: 6px;
}

.tutorial-content code {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  color: #FBBF24;
  font-family: monospace;
}

.tutorial-content pre {
  background: rgba(15, 23, 42, 0.6);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow-x: auto;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.2);
}

.tutorial-content pre code {
  background: transparent;
  padding: 0;
  color: #A7F3D0;
  text-shadow: 0 0 5px rgba(167, 243, 208, 0.2);
  line-height: 1.5;
}
</style>
