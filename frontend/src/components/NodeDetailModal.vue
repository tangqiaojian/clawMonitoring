<script setup lang="ts">
import { computed } from 'vue'
import type { LobsterRuntime } from '../types/monitor'
import HistoryChart from './HistoryChart.vue'

const props = defineProps<{
  open: boolean
  lobster: LobsterRuntime | null
  cpuPoints: Array<{ t: number; v: number }>
  taskPoints: Array<{ t: number; v: number }>
}>()

const emit = defineEmits<{
  close: []
}>()

const statusLabel = computed(() => {
  switch (props.lobster?.status) {
    case 'active':
      return '正常运行'
    case 'warning':
      return '高负载预警'
    case 'offline':
      return '离线故障'
    default:
      return '空闲'
  }
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-mask" @click.self="emit('close')">
      <section class="glass-card modal-card">
        <header>
          <h3>{{ lobster?.name ?? '节点详情' }}</h3>
          <p>{{ lobster?.id }} · {{ statusLabel }}</p>
          <button class="close-btn" @click="emit('close')">关闭</button>
        </header>
        <div class="modal-grid">
          <div class="detail-metrics">
            <div>
              <span>CPU</span>
              <strong>{{ lobster?.cpu_percent?.toFixed(1) ?? '--' }}%</strong>
            </div>
            <div>
              <span>任务数</span>
              <strong>{{ lobster?.task_count ?? '--' }}</strong>
            </div>
            <div>
              <span>状态</span>
              <strong>{{ statusLabel }}</strong>
            </div>
          </div>
          <HistoryChart title="节点CPU趋势" :points="cpuPoints" color="#06B6D4" suffix="%" />
          <HistoryChart title="任务数量趋势" :points="taskPoints" color="#10B981" suffix="" />
        </div>
      </section>
    </div>
  </Teleport>
</template>
