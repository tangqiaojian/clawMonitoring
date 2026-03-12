<script setup lang="ts">
import { computed } from 'vue'
import type { LobsterRuntime } from '../types/monitor'

const props = defineProps<{
  lobster: LobsterRuntime
}>()

defineEmits<{
  select: [id: string]
}>()

const mood = computed(() => {
  switch (props.lobster.status) {
    case 'active':
      return '🙂'
    case 'warning':
      return '😓'
    case 'offline':
      return '🪨'
    default:
      return '😴'
  }
})
</script>

<template>
  <article class="glass-card lobster" :data-state="lobster.status" @click="$emit('select', lobster.id)">
    <div class="head">{{ mood }}</div>
    <div class="body">
      <h4>{{ lobster.name }}</h4>
      <p>{{ lobster.id }}</p>
      <div class="meta">
        <span>CPU {{ lobster.cpu_percent.toFixed(1) }}%</span>
        <span>任务 {{ lobster.task_count }}</span>
      </div>
    </div>
  </article>
</template>
