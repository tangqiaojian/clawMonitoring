<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([SVGRenderer, LineChart, GridComponent, TooltipComponent])

const props = withDefaults(
  defineProps<{
    title: string
    points: Array<{ t: number; v: number }>
    color?: string
    suffix?: string
  }>(),
  {
    color: '#06B6D4',
    suffix: '%',
  },
)

const option = computed(() => {
  const data = props.points.map((p) => [new Date(p.t * 1000).toLocaleTimeString('zh-CN', { hour12: false }), Number(p.v.toFixed(2))])
  return {
    animationDuration: 500,
    textStyle: { color: '#d9f5ff' },
    grid: { left: 10, right: 10, top: 24, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(2, 17, 31, 0.82)',
      borderWidth: 1,
      borderColor: 'rgba(255,255,255,0.25)',
      valueFormatter: (value: number) => `${value}${props.suffix}`,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map((row) => row[0]),
      axisLabel: { color: 'rgba(226,244,255,0.68)', fontSize: 10 },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.12)' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: 'rgba(226,244,255,0.68)', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: props.color },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: `${props.color}CC` },
              { offset: 1, color: `${props.color}14` },
            ],
          },
        },
        data: data.map((row) => row[1]),
      },
    ],
  }
})
</script>

<template>
  <section class="chart-block">
    <h4>{{ title }}</h4>
    <VChart :option="option" autoresize class="chart" />
  </section>
</template>
