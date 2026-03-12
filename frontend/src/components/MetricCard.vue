<script setup lang="ts">
defineProps<{
  title: string
  value: string
  subtitle?: string
  tone?: 'normal' | 'ok' | 'warn' | 'danger'
}>()
</script>

<template>
  <section class="glass-card metric" :data-tone="tone ?? 'normal'">
    <p class="label">{{ title }}</p>
    <p class="value">{{ value }}</p>
    <p v-if="subtitle" class="sub">{{ subtitle }}</p>
  </section>
</template>
