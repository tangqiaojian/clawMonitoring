export type LobsterStatus = 'active' | 'warning' | 'offline' | 'idle'

export interface HostMetrics {
  cpu_percent: number
  cpu_cores: number[]
  cpu_freq: number | null
  mem_percent: number
  mem_used: number
  mem_total: number
  swap_percent: number
  network_up: number
  network_down: number
  disk: {
    partitions: Array<{
      device: string
      mountpoint: string
      fstype: string
      used: number
      total: number
      percent: number
    }>
    io_read_bytes: number
    io_write_bytes: number
  }
  gpu: {
    vendor: string
    name: string
    load: number
    memory_used: number
    memory_total: number
    temperature: number | null
  }
}

export interface LobsterNode {
  id: string
  name: string
  host: string
  token?: string
  status: LobsterStatus
  created_at?: number
}

export interface LobsterRuntime {
  id: string
  name: string
  status: LobsterStatus
  cpu_percent: number
  task_count: number
}

export interface ResourceStreamPayload {
  topic: 'resource_stream'
  timestamp: number
  host: HostMetrics
  lobsters: LobsterRuntime[]
}
