<script setup lang="ts">
import { ref, computed } from 'vue'

interface AlertRecord {
  id: string
  message: string
  timestamp: number
  type: 'cpu' | 'memory' | 'gpu' | 'node'
  source: string
}

const props = defineProps<{
  alerts: AlertRecord[]
  total: number
}>()

const emit = defineEmits<{
  clear: []
}>()

const dropdownOpen = ref(false)

const sortedAlerts = computed(() => {
  return [...props.alerts].sort((a, b) => b.timestamp - a.timestamp)
})

function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

function handleClear() {
  emit('clear')
  dropdownOpen.value = false
}
</script>

<template>
  <div class="alert-notification">
    <button class="alert-bell" @click="toggleDropdown" :data-has-alert="total > 0">
      🔔
      <span v-if="total > 0" class="badge">{{ total > 99 ? '99+' : total }}</span>
    </button>

    <div v-if="dropdownOpen" class="alert-dropdown">
      <div class="dropdown-header">
        <strong>告警通知</strong>
        <button v-if="alerts.length > 0" class="clear-btn" @click="handleClear">清空</button>
      </div>
      <div class="alert-list">
        <div v-if="sortedAlerts.length === 0" class="empty-state">
          暂无告警
        </div>
        <div v-for="alert in sortedAlerts" :key="alert.id" class="alert-item">
          <div class="alert-content">
            <div class="alert-message">{{ alert.message }}</div>
            <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="dropdownOpen" class="dropdown-mask" @click="dropdownOpen = false"></div>
  </div>
</template>

<style scoped>
.alert-notification {
  position: relative;
  z-index: 9999;
}

.alert-bell {
  position: relative;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 8px 12px;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.alert-bell:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.alert-bell[data-has-alert='true'] {
  animation: shake 2s ease-in-out infinite;
}

@keyframes shake {
  0%, 100% { transform: rotate(0deg); }
  10% { transform: rotate(-10deg); }
  20% { transform: rotate(10deg); }
  30% { transform: rotate(-5deg); }
  40% { transform: rotate(5deg); }
  50% { transform: rotate(0deg); }
}

.badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: #ef4444;
  color: white;
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 999px;
  min-width: 18px;
  text-align: center;
  line-height: 1;
}

.alert-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  min-width: 380px;
  max-width: 480px;
  max-height: 80vh; /* 使用 vh 保证不会超出屏幕 */
  display: flex; /* 让内部列表可以自适应高度并滚动 */
  flex-direction: column;
  backdrop-filter: blur(20px) saturate(140%);
  background: linear-gradient(140deg, rgba(210, 239, 255, 0.12), rgba(255, 255, 255, 0.04));
  border: 1px solid var(--glass-border);
  border-radius: 14px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45), 0 18px 40px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  z-index: 10000;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.dropdown-header strong {
  font-size: 0.9rem;
}

.clear-btn {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #ef4444;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clear-btn:hover {
  background: rgba(239, 68, 68, 0.1);
}

.alert-list {
  flex: 1; /* 吸取剩余空间 */
  overflow-y: auto;
  max-height: 400px;
}

/* 自定义滚动条风格 */
.alert-list::-webkit-scrollbar {
  width: 6px;
}

.alert-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
}

.alert-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.alert-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

.alert-item {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  transition: background 0.2s ease;
}

.alert-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.alert-message {
  font-size: 0.85rem;
  line-height: 1.4;
  margin-bottom: 4px;
  color: #ffe6e6;
}

.alert-time {
  font-size: 0.75rem;
  color: rgba(226, 244, 255, 0.6);
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: rgba(226, 244, 255, 0.5);
  font-size: 0.9rem;
}

.dropdown-mask {
  position: fixed;
  inset: 0;
  z-index: -1;
}
</style>
