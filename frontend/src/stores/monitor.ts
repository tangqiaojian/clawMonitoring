import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { LobsterNode, ResourceStreamPayload } from '../types/monitor'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'
const WS_BASE = import.meta.env.VITE_WS_BASE ?? 'ws://127.0.0.1:8000/ws'

export const useMonitorStore = defineStore('monitor', () => {
  const connected = ref(false)
  const lastUpdate = ref<number>(0)
  const payload = ref<ResourceStreamPayload | null>(null)
  const nodes = ref<LobsterNode[]>([])
  const socket = ref<WebSocket | null>(null)
  const reconnectTimer = ref<number | null>(null)
  const pollingTimer = ref<number | null>(null)

  const lobsterStats = computed(() => {
    const run = payload.value?.lobsters ?? []
    return {
      total: run.length,
      active: run.filter((x) => x.status === 'active').length,
      offline: run.filter((x) => x.status === 'offline').length,
      warning: run.filter((x) => x.status === 'warning').length,
      idle: run.filter((x) => x.status === 'idle').length,
    }
  })

  async function fetchNodes() {
    const res = await fetch(`${API_BASE}/api/nodes`)
    if (!res.ok) {
      throw new Error('failed to load nodes')
    }
    nodes.value = await res.json()
  }

  async function addNode(node: Pick<LobsterNode, 'id' | 'name' | 'host' | 'token'>) {
    const res = await fetch(`${API_BASE}/api/nodes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(node),
    })

    if (!res.ok) {
      throw new Error(await res.text())
    }
    await fetchNodes()
  }

  async function removeNode(id: string) {
    const res = await fetch(`${API_BASE}/api/nodes/${id}`, { method: 'DELETE' })
    if (!res.ok) {
      throw new Error('failed to remove node')
    }
    await fetchNodes()
  }

  async function fetchHistory(metric: string, limit = 60): Promise<Array<{ t: number; v: number }>> {
    const res = await fetch(`${API_BASE}/api/history/${metric}?limit=${limit}`)
    if (!res.ok) {
      return []
    }
    const data = (await res.json()) as { points: Array<{ t: number; v: number }> }
    return data.points
  }

  async function fetchSnapshot() {
    const res = await fetch(`${API_BASE}/api/snapshot`)
    if (!res.ok) {
      return
    }
    const data = (await res.json()) as ResourceStreamPayload
    payload.value = data
    lastUpdate.value = Date.now()
  }

  function startPolling() {
    if (pollingTimer.value !== null) {
      return
    }
    pollingTimer.value = window.setInterval(() => {
      fetchSnapshot().catch(() => {
        // Keep interval alive; transient failures are expected during restart.
      })
    }, 1000)
  }

  function stopPolling() {
    if (pollingTimer.value !== null) {
      window.clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function connect() {
    if (socket.value) {
      socket.value.close()
    }

    const ws = new WebSocket(WS_BASE)
    socket.value = ws

    ws.onopen = () => {
      connected.value = true
      stopPolling()
      ws.send('subscribe:resource_stream')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as ResourceStreamPayload
      payload.value = data
      lastUpdate.value = Date.now()
    }

    ws.onclose = () => {
      connected.value = false
      socket.value = null
      startPolling()
      if (reconnectTimer.value !== null) {
        window.clearTimeout(reconnectTimer.value)
      }
      reconnectTimer.value = window.setTimeout(() => connect(), 20000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }

  function disconnect() {
    if (reconnectTimer.value !== null) {
      window.clearTimeout(reconnectTimer.value)
    }
    socket.value?.close()
    socket.value = null
    connected.value = false
    stopPolling()
  }

  return {
    connected,
    lastUpdate,
    payload,
    nodes,
    lobsterStats,
    fetchNodes,
    addNode,
    removeNode,
    fetchHistory,
    startPolling,
    stopPolling,
    connect,
    disconnect,
  }
})
