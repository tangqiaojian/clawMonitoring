<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  messages: string[]
}>()

const emit = defineEmits<{
  close: []
}>()

const visible = ref(false)
const slideIn = ref(false)

watch(
  () => props.messages.length,
  (newLen) => {
    if (newLen > 0) {
      visible.value = true
      setTimeout(() => {
        slideIn.value = true
      }, 10)
    } else if (newLen === 0) {
      slideIn.value = false
      setTimeout(() => {
        visible.value = false
      }, 300)
    }
  },
  { immediate: true }
)

function handleClose() {
  slideIn.value = false
  setTimeout(() => {
    visible.value = false
    emit('close')
  }, 300)
}
</script>

<template>
  <transition name="fade">
    <div v-if="visible" class="alert-popup" :class="{ 'slide-in': slideIn }">
      <div class="alert-header">
        <strong>⚠️ 实时警报</strong>
        <button class="close-btn" @click="handleClose">×</button>
      </div>
      <div class="alert-items">
        <div v-for="item in messages" :key="item" class="alert-item">
          {{ item }}
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.alert-popup {
  position: fixed;
  top: 20px;
  right: 20px;
  min-width: 320px;
  max-width: 420px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  z-index: 1000;
  backdrop-filter: blur(20px) saturate(140%);
  background: linear-gradient(140deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.08));
  border: 1px solid rgba(239, 68, 68, 0.55);
  border-radius: 14px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45), 0 18px 40px rgba(239, 68, 68, 0.25);
  animation: pulse 1.8s ease-in-out infinite;
  transform: translateX(120%);
  transition: transform 0.3s ease-out;
}

.alert-popup.slide-in {
  transform: translateX(0);
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(239, 68, 68, 0.3);
}

.alert-header strong {
  font-size: 0.9rem;
  color: #ffb7b7;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.2rem;
  color: #ffb7b7;
  cursor: pointer;
  padding: 0 6px;
  line-height: 1;
  border-radius: 4px;
  transition: background 0.2s ease;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
}

.alert-items {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}

/* 自定义滚动条风格 */
.alert-items::-webkit-scrollbar {
  width: 4px;
}
.alert-items::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
}
.alert-items::-webkit-scrollbar-thumb {
  background: rgba(239, 68, 68, 0.4);
  border-radius: 2px;
}
.alert-items::-webkit-scrollbar-thumb:hover {
  background: rgba(239, 68, 68, 0.6);
}

.alert-item {
  font-size: 0.88rem;
  color: #ffe6e6;
  line-height: 1.4;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.alert-item:last-child {
  border-bottom: none;
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45), 0 10px 30px rgba(239, 68, 68, 0.2);
  }
  50% {
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45), 0 10px 34px rgba(239, 68, 68, 0.4);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
