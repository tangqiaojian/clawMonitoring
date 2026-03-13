<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useMonitorStore } from '../stores/monitor'
import { API_BASE } from '../utils/endpoints'
import type { WorkRecord } from '../types/monitor'

const store = useMonitorStore()
const { payload, connected } = storeToRefs(store)

// 系统负载状态
const systemLoad = computed(() => {
  if (!payload.value) return 0
  const cpu = payload.value.host.cpu_percent / 100
  const mem = payload.value.host.mem_percent / 100
  const gpu = payload.value.host.gpu.load / 100
  return (cpu + mem + gpu) / 3
})

// 节点状态
const workerStates = computed(() => {
  return payload.value?.lobsters ?? []
})
const recentRecords = ref<WorkRecord[]>([])
let recordTimer: number | null = null

// 办公室动画帧
const animationFrame = ref(0)
let animationId: number | null = null

// 像素风色板
const P = {
  wallTop: '#D4B896',
  wallBottom: '#C4A478',
  wallTrim: '#8B6F4E',
  floorA: '#E8DCCD',
  floorB: '#D9CEB8',
  woodLight: '#A67C52',
  woodMid: '#8B6540',
  woodDark: '#6B4E35',
  woodDeep: '#5A3E28',
  deskTop: '#C4955A',
  chairSeat: '#8B3A3A',
  chairBack: '#6B2A2A',
  monitorFrame: '#2A2A2A',
  screenBg: '#1A3A2A',
  screenGlow: '#3ACA5A',
  sofaBody: '#C9A868',
  sofaDark: '#A68845',
  sofaCushion: '#D4B87A',
  bedFrame: '#8B6540',
  bedSheet: '#E8DDD0',
  blanket: '#7B9B6B',
  pillow: '#F0E6D8',
  bookshelfWood: '#6B4E35',
  carpetA: '#9B6B3E',
  carpetB: '#B87A45',
  plantGreen: '#5A9B4A',
  plantDark: '#3D7D32',
  potBrown: '#8B5E3C',
  skinTone: '#FFD1B0',
  hairDark: '#4A3520',
  catOrange: '#E8A040',
  catDark: '#B87830',
  windowSky: '#87CEEB',
  windowFrame: '#8B6F4E',
  posterFrame: '#6B4E35',
  text: '#FFF8E8',
  banner: '#3A2820',
  bannerBorder: '#8B6F4E',
  gold: '#DAA520',
}

const bookColors = ['#C44444', '#4488CC', '#44AA88', '#DDAA44', '#8844CC', '#CC8844', '#44AACC', '#CC4488']

// 员工角色颜色 - 温暖像素风
const workerColors = [
  '#E74C3C', '#3498DB', '#2ECC71', '#F39C12',
  '#9B59B6', '#1ABC9C', '#E67E22', '#E84393',
  '#00B894', '#6C5CE7', '#FDCB6E', '#74B9FF'
]

const workPositions = [
  { x: 75, y: 145 }, { x: 200, y: 145 }, { x: 325, y: 145 },
  { x: 450, y: 145 }, { x: 575, y: 145 }, { x: 700, y: 145 },
  { x: 75, y: 300 }, { x: 200, y: 300 }, { x: 325, y: 300 },
  { x: 450, y: 300 }, { x: 575, y: 300 }, { x: 700, y: 300 },
]

const restPositions = [
  { x: 900, y: 145 }, { x: 930, y: 145 }, { x: 960, y: 145 },
  { x: 840, y: 260 }, { x: 870, y: 260 }, { x: 900, y: 260 },
]

// 鼠标Hover状态
const hoveredWorker = ref<any | null>(null)
const mousePos = ref({ x: 0, y: 0 })

function handleMouseMove(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas) return
  
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  
  const mouseX = (e.clientX - rect.left) * scaleX
  const mouseY = (e.clientY - rect.top) * scaleY

  let foundWorker = null
  workerStates.value.forEach((worker, index) => {
    if (index < workPositions.length) {
      const pos = workPositions[index]
      if (!pos) return
      if (mouseX >= pos.x - 15 && mouseX <= pos.x + 15 &&
          mouseY >= pos.y - 15 && mouseY <= pos.y + 30) {
        foundWorker = worker
      }
    }
  })

  // 如果想把休息区的小人也加上hover事件，但他们没有绑定具体workerId，目前只显示实际的worker节点
  if (foundWorker) {
    hoveredWorker.value = foundWorker
    mousePos.value = { x: e.clientX, y: e.clientY }
  } else {
    hoveredWorker.value = null
  }
}

function handleMouseLeave() {
  hoveredWorker.value = null
}

function formatRecordTime(ts?: number) {
  if (!ts) return '--'
  return new Date(ts * 1000).toLocaleString()
}

async function loadRecentRecords() {
  try {
    const res = await fetch(`${API_BASE}/api/work?limit=20`)
    if (!res.ok) return
    const data = (await res.json()) as { records: WorkRecord[] }
    recentRecords.value = data.records ?? []
  } catch {
    // ignore
  }
}

// ========== 像素风办公室物品 — 温馨房间布局 ==========
const officeItems = [
  // ===== 墙面装饰 =====
  { type: 'poster', x: 55, y: 8, w: 48, h: 52, variant: 'et' },
  { type: 'poster', x: 150, y: 10, w: 44, h: 48, variant: 'chart' },
  { type: 'window', x: 280, y: 4, w: 110, h: 62 },
  { type: 'poster', x: 440, y: 8, w: 48, h: 52, variant: 'lobster' },
  { type: 'clock', x: 550, y: 14, w: 30, h: 30 },
  { type: 'poster', x: 630, y: 8, w: 48, h: 52, variant: 'friends' },
  { type: 'poster', x: 890, y: 10, w: 44, h: 48, variant: 'landscape' },

  // ===== 第一排工位 =====
  { type: 'desk', x: 25, y: 105, w: 105, h: 50 },
  { type: 'desk', x: 150, y: 105, w: 105, h: 50 },
  { type: 'desk', x: 275, y: 105, w: 105, h: 50 },
  { type: 'desk', x: 400, y: 105, w: 105, h: 50 },
  { type: 'desk', x: 525, y: 105, w: 105, h: 50 },
  { type: 'desk', x: 650, y: 105, w: 105, h: 50 },

  { type: 'computer', x: 50, y: 88, w: 36, h: 28 },
  { type: 'computer', x: 175, y: 88, w: 36, h: 28 },
  { type: 'computer', x: 300, y: 88, w: 36, h: 28 },
  { type: 'computer', x: 425, y: 88, w: 36, h: 28 },
  { type: 'computer', x: 550, y: 88, w: 36, h: 28 },
  { type: 'computer', x: 675, y: 88, w: 36, h: 28 },

  { type: 'coffee_cup', x: 102, y: 108, w: 10, h: 12 },
  { type: 'coffee_cup', x: 227, y: 108, w: 10, h: 12 },
  { type: 'coffee_cup', x: 477, y: 108, w: 10, h: 12 },
  { type: 'coffee_cup', x: 727, y: 108, w: 10, h: 12 },

  // ===== 第二排工位 =====
  { type: 'desk', x: 25, y: 260, w: 105, h: 50 },
  { type: 'desk', x: 150, y: 260, w: 105, h: 50 },
  { type: 'desk', x: 275, y: 260, w: 105, h: 50 },
  { type: 'desk', x: 400, y: 260, w: 105, h: 50 },
  { type: 'desk', x: 525, y: 260, w: 105, h: 50 },
  { type: 'desk', x: 650, y: 260, w: 105, h: 50 },

  { type: 'computer', x: 50, y: 243, w: 36, h: 28 },
  { type: 'computer', x: 175, y: 243, w: 36, h: 28 },
  { type: 'computer', x: 300, y: 243, w: 36, h: 28 },
  { type: 'computer', x: 425, y: 243, w: 36, h: 28 },
  { type: 'computer', x: 550, y: 243, w: 36, h: 28 },
  { type: 'computer', x: 675, y: 243, w: 36, h: 28 },

  { type: 'coffee_cup', x: 352, y: 263, w: 10, h: 12 },
  { type: 'coffee_cup', x: 602, y: 263, w: 10, h: 12 },

  // ===== 休息区 (右侧) =====
  { type: 'bookshelf', x: 780, y: 72, w: 85, h: 95 },
  { type: 'sofa', x: 880, y: 100, w: 95, h: 55 },
  { type: 'carpet', x: 790, y: 185, w: 170, h: 90 },
  { type: 'coffee_table', x: 830, y: 200, w: 65, h: 40 },
  { type: 'bed', x: 800, y: 310, w: 120, h: 85 },
  { type: 'cat_bed', x: 930, y: 330, w: 50, h: 36 },

  // ===== 植物 =====
  { type: 'plant', x: 760, y: 78, w: 18, h: 28 },
  { type: 'plant', x: 960, y: 78, w: 18, h: 28 },
  { type: 'plant_small', x: 850, y: 195, w: 12, h: 18 },
  { type: 'plant', x: 20, y: 380, w: 18, h: 28 },
  { type: 'plant', x: 740, y: 380, w: 18, h: 28 },

  // ===== 其他 =====
  { type: 'lamp', x: 740, y: 155, w: 16, h: 55 },
  { type: 'trash', x: 125, y: 160, w: 14, h: 18 },
  { type: 'trash', x: 500, y: 315, w: 14, h: 18 },
]

const canvasRef = ref<HTMLCanvasElement | null>(null)

// ========== 绘制像素风小人 ==========
function drawWorker(
  ctx: CanvasRenderingContext2D,
  x: number, y: number,
  color: string, status: string,
  load: number, frame: number,
  area: 'work' | 'rest' = 'work'
) {
  ctx.imageSmoothingEnabled = false
  const bob = Math.round(Math.sin(frame * 0.15 + x * 0.01) * 2 * load)

  // 身体 (像素块)
  ctx.fillStyle = color
  ctx.fillRect(x - 7, y + 4 + bob, 14, 16)

  // 决定肤色 (红温告警)
  const currentSkin = status === 'warning' ? '#E74C3C' : P.skinTone

  // 头部
  ctx.fillStyle = currentSkin
  ctx.fillRect(x - 8, y - 10 + bob, 16, 14)

  // 头发
  ctx.fillStyle = P.hairDark
  ctx.fillRect(x - 8, y - 12 + bob, 16, 6)

  // 表情
  ctx.fillStyle = '#222'
  if (status === 'warning') {
    // 惊讶 - 大眼 + 汗滴
    ctx.fillRect(x - 5, y - 5 + bob, 3, 3)
    ctx.fillRect(x + 3, y - 5 + bob, 3, 3)
    ctx.fillRect(x - 2, y + bob, 4, 3) // 张大嘴
    // 汗滴
    ctx.fillStyle = '#67D8EF'
    ctx.fillRect(x + 10, y - 8 + bob, 3, 5)
    ctx.fillRect(x + 11, y - 3 + bob, 2, 2)
    // 警告光圈
    ctx.strokeStyle = 'rgba(231, 76, 60, 0.6)'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.arc(x, y + 2 + bob, 18 + Math.sin(frame * 0.25) * 3, 0, Math.PI * 2)
    ctx.stroke()
    
    // 绘制头顶感叹号 (红色, 闪烁跳动)
    const alertBob = Math.abs(Math.sin(frame * 0.2)) * 4
    ctx.fillStyle = '#FF3B30' // 亮红色
    ctx.fillRect(x - 2, y - 26 - alertBob + bob, 4, 8)  // 竖线
    ctx.fillRect(x - 2, y - 16 - alertBob + bob, 4, 3)  // 点
    
    // 感叹号白色描边突出显示
    ctx.fillStyle = '#FFFFFF'
    ctx.fillRect(x - 1, y - 25 - alertBob + bob, 2, 6)
    ctx.fillRect(x - 1, y - 15 - alertBob + bob, 2, 1)
  } else if (status === 'offline') {
    // 睡觉
    ctx.fillRect(x - 5, y - 5 + bob, 4, 1)
    ctx.fillRect(x + 2, y - 5 + bob, 4, 1)
    ctx.fillRect(x - 2, y + bob, 4, 2)
    // Z z z
    ctx.fillStyle = 'rgba(255,255,255,0.6)'
    ctx.font = '10px monospace'
    ctx.fillText('Z', x + 12, y - 8 + Math.sin(frame * 0.1) * 3)
    ctx.font = '8px monospace'
    ctx.fillText('z', x + 18, y - 14 + Math.sin(frame * 0.1 + 1) * 2)
  } else if (status === 'active') {
    if (area === 'work') {
      // 专注工作
      ctx.fillRect(x - 5, y - 5 + bob, 3, 3)
      ctx.fillRect(x + 3, y - 5 + bob, 3, 3)
      ctx.fillRect(x - 2, y + 1 + bob, 4, 1)
    } else {
      // 休息区 - 开心
      ctx.fillRect(x - 5, y - 5 + bob, 3, 3)
      ctx.fillRect(x + 3, y - 5 + bob, 3, 3)
      ctx.fillStyle = '#222'
      ctx.fillRect(x - 3, y + bob, 6, 1)
      ctx.fillRect(x - 2, y + 1 + bob, 4, 1)
    }
  } else {
    // idle
    ctx.fillRect(x - 5, y - 5 + bob, 3, 2)
    ctx.fillRect(x + 3, y - 5 + bob, 3, 2)
    ctx.fillRect(x - 3, y + bob, 6, 1)
  }

  // 小手
  ctx.fillStyle = currentSkin
  ctx.fillRect(x - 11, y + 8 + bob, 4, 4)
  ctx.fillRect(x + 7, y + 8 + bob, 4, 4)

  // 小腿
  ctx.fillStyle = color
  ctx.fillRect(x - 5, y + 20 + bob, 4, 5)
  ctx.fillRect(x + 1, y + 20 + bob, 4, 5)

  // 小鞋
  ctx.fillStyle = P.woodDark
  ctx.fillRect(x - 6, y + 25 + bob, 5, 3)
  ctx.fillRect(x + 1, y + 25 + bob, 5, 3)
}

// ========== 绘制像素风家具 ==========
function drawOfficeItem(ctx: CanvasRenderingContext2D, item: any, frame: number) {
  ctx.imageSmoothingEnabled = false
  const { x, y, w, h } = item

  switch (item.type) {
    case 'desk': {
      // 桌面
      ctx.fillStyle = P.deskTop
      ctx.fillRect(x, y, w, 8)
      ctx.fillStyle = P.woodLight
      ctx.fillRect(x, y + 8, w, h - 8)
      // 桌面高光
      ctx.fillStyle = 'rgba(255,255,255,0.15)'
      ctx.fillRect(x + 2, y + 1, w - 4, 3)
      // 桌腿
      ctx.fillStyle = P.woodDark
      ctx.fillRect(x + 4, y + h, 6, 16)
      ctx.fillRect(x + w - 10, y + h, 6, 16)
      // 抽屉
      ctx.fillStyle = P.woodMid
      ctx.fillRect(x + 60, y + 12, 35, h - 16)
      ctx.fillStyle = P.gold
      ctx.fillRect(x + 75, y + 22, 5, 3)
      break
    }

    case 'computer': {
      // 显示器外框
      ctx.fillStyle = P.monitorFrame
      ctx.fillRect(x, y, w, h)
      // 屏幕
      ctx.fillStyle = P.screenBg
      ctx.fillRect(x + 3, y + 3, w - 6, h - 8)
      // 屏幕内容闪烁
      const flicker = Math.sin(frame * 0.08 + x * 0.1) * 0.5 + 0.5
      ctx.fillStyle = `rgba(58, 202, 90, ${0.15 + flicker * 0.25})`
      // 代码行
      for (let i = 0; i < 4; i++) {
        const lineW = 8 + Math.abs(Math.sin(x + i * 3)) * 16
        ctx.fillRect(x + 5, y + 5 + i * 4, lineW, 2)
      }
      // 显示器底座
      ctx.fillStyle = P.monitorFrame
      ctx.fillRect(x + 12, y + h, 12, 4)
      ctx.fillRect(x + 8, y + h + 4, 20, 3)
      // 小苹果 logo
      ctx.fillStyle = 'rgba(255,255,255,0.4)'
      ctx.fillRect(x + w / 2 - 1, y + h - 4, 3, 3)
      break
    }

    case 'coffee_cup': {
      // 杯身
      ctx.fillStyle = '#F5F0E8'
      ctx.fillRect(x, y + 3, w, h - 3)
      // 咖啡液面
      ctx.fillStyle = '#8B5A3C'
      ctx.fillRect(x + 1, y + 4, w - 2, 3)
      // 杯把
      ctx.fillStyle = '#F5F0E8'
      ctx.fillRect(x + w, y + 5, 3, 5)
      ctx.fillRect(x + w + 3, y + 6, 1, 3)
      // 蒸汽
      if (Math.sin(frame * 0.1 + x) > 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.3)'
        ctx.fillRect(x + 2, y - 1 + Math.round(Math.sin(frame * 0.15) * 1), 2, 3)
        ctx.fillRect(x + 6, y - 2 + Math.round(Math.cos(frame * 0.12) * 1), 2, 2)
      }
      break
    }

    case 'bookshelf': {
      // 书架背板
      ctx.fillStyle = P.bookshelfWood
      ctx.fillRect(x, y, w, h)
      // 架板
      ctx.fillStyle = P.woodMid
      for (let i = 0; i < 3; i++) {
        ctx.fillRect(x, y + 4 + i * 30, w, 4)
      }
      // 书本
      for (let shelf = 0; shelf < 3; shelf++) {
        let bx = x + 3
        const by = y + 8 + shelf * 30
        for (let b = 0; b < 6; b++) {
          const bw = 6 + Math.floor(Math.abs(Math.sin(shelf * 7 + b * 3)) * 5)
          const bh = 18 + Math.floor(Math.abs(Math.cos(shelf * 5 + b * 2)) * 6)
          ctx.fillStyle = bookColors[(shelf * 3 + b) % bookColors.length] || '#C44444'
          ctx.fillRect(bx, by + (24 - bh), bw, bh)
          // 书脊高光
          ctx.fillStyle = 'rgba(255,255,255,0.2)'
          ctx.fillRect(bx + 1, by + (24 - bh) + 2, 1, bh - 4)
          bx += bw + 2
          if (bx > x + w - 8) break
        }
      }
      // 边框
      ctx.strokeStyle = P.woodDark
      ctx.lineWidth = 2
      ctx.strokeRect(x, y, w, h)
      break
    }

    case 'sofa': {
      // 沙发主体
      ctx.fillStyle = P.sofaBody
      ctx.fillRect(x, y + 8, w, h - 8)
      // 靠背
      ctx.fillStyle = P.sofaDark
      ctx.fillRect(x, y, w, 14)
      // 坐垫
      ctx.fillStyle = P.sofaCushion
      ctx.fillRect(x + 4, y + 18, w / 2 - 6, h - 26)
      ctx.fillRect(x + w / 2 + 2, y + 18, w / 2 - 6, h - 26)
      // 扶手
      ctx.fillStyle = P.sofaDark
      ctx.fillRect(x, y + 14, 10, h - 14)
      ctx.fillRect(x + w - 10, y + 14, 10, h - 14)
      // 腿
      ctx.fillStyle = P.woodDark
      ctx.fillRect(x + 2, y + h, 5, 5)
      ctx.fillRect(x + w - 7, y + h, 5, 5)
      break
    }

    case 'carpet': {
      // 地毯主体
      ctx.fillStyle = P.carpetA
      ctx.fillRect(x, y, w, h)
      // 花纹边框
      ctx.fillStyle = P.carpetB
      ctx.fillRect(x, y, w, 4)
      ctx.fillRect(x, y + h - 4, w, 4)
      ctx.fillRect(x, y, 4, h)
      ctx.fillRect(x + w - 4, y, 4, h)
      // 内花纹
      ctx.fillStyle = 'rgba(255,255,255,0.08)'
      for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 2; j++) {
          ctx.fillRect(x + 20 + i * 50, y + 15 + j * 30, 20, 20)
        }
      }
      break
    }

    case 'coffee_table': {
      // 桌面
      ctx.fillStyle = P.woodLight
      ctx.fillRect(x, y, w, 6)
      ctx.fillStyle = P.woodMid
      ctx.fillRect(x, y + 6, w, h - 6)
      // 桌腿
      ctx.fillStyle = P.woodDark
      ctx.fillRect(x + 3, y + h, 4, 10)
      ctx.fillRect(x + w - 7, y + h, 4, 10)
      // 桌上的杯子
      ctx.fillStyle = '#F5F0E8'
      ctx.fillRect(x + 12, y - 4, 8, 10)
      ctx.fillStyle = '#5A8B4A'
      ctx.fillRect(x + 13, y - 3, 6, 3)
      break
    }

    case 'bed': {
      // 床架
      ctx.fillStyle = P.bedFrame
      ctx.fillRect(x, y, w, h)
      // 床垫
      ctx.fillStyle = P.bedSheet
      ctx.fillRect(x + 4, y + 4, w - 8, h - 12)
      // 被子
      ctx.fillStyle = P.blanket
      ctx.fillRect(x + 4, y + h / 2, w - 8, h / 2 - 12)
      // 被子花纹
      ctx.fillStyle = 'rgba(255,255,255,0.1)'
      ctx.fillRect(x + 12, y + h / 2 + 5, w - 24, 3)
      ctx.fillRect(x + 12, y + h / 2 + 15, w - 24, 3)
      // 枕头
      ctx.fillStyle = P.pillow
      ctx.fillRect(x + 10, y + 8, 40, 22)
      ctx.fillRect(x + 60, y + 10, 36, 18)
      // 枕头高光
      ctx.fillStyle = 'rgba(255,255,255,0.15)'
      ctx.fillRect(x + 12, y + 10, 20, 3)
      // 床头板
      ctx.fillStyle = P.woodDark
      ctx.fillRect(x, y - 8, w, 12)
      ctx.fillStyle = P.woodMid
      ctx.fillRect(x + 2, y - 6, w - 4, 8)
      break
    }

    case 'cat_bed': {
      // 猫窝垫子
      ctx.fillStyle = '#A0785A'
      ctx.beginPath()
      ctx.ellipse(x + w / 2, y + h / 2 + 4, w / 2, h / 2 - 2, 0, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = '#C49878'
      ctx.beginPath()
      ctx.ellipse(x + w / 2, y + h / 2 + 2, w / 2 - 4, h / 2 - 6, 0, 0, Math.PI * 2)
      ctx.fill()
      // 猫咪 (蜷缩)
      ctx.fillStyle = P.catOrange
      ctx.beginPath()
      ctx.ellipse(x + w / 2, y + h / 2, 14, 10, 0, 0, Math.PI * 2)
      ctx.fill()
      // 猫头
      ctx.beginPath()
      ctx.arc(x + w / 2 - 10, y + h / 2 - 4, 8, 0, Math.PI * 2)
      ctx.fill()
      // 猫耳
      ctx.fillStyle = P.catDark
      ctx.fillRect(x + w / 2 - 16, y + h / 2 - 12, 5, 6)
      ctx.fillRect(x + w / 2 - 8, y + h / 2 - 12, 5, 6)
      // 尾巴
      ctx.fillStyle = P.catOrange
      ctx.fillRect(x + w / 2 + 8, y + h / 2 - 6, 10, 4)
      ctx.fillRect(x + w / 2 + 16, y + h / 2 - 9, 4, 6)
      // 条纹
      ctx.fillStyle = P.catDark
      ctx.fillRect(x + w / 2 - 4, y + h / 2 - 6, 3, 8)
      ctx.fillRect(x + w / 2 + 3, y + h / 2 - 5, 3, 7)
      // 闭眼
      ctx.fillStyle = '#222'
      ctx.fillRect(x + w / 2 - 13, y + h / 2 - 4, 3, 1)
      // zzz
      ctx.fillStyle = 'rgba(255,255,255,0.4)'
      ctx.font = '8px monospace'
      const zy = Math.sin(frame * 0.08) * 2
      ctx.fillText('z', x + w / 2 - 4, y + h / 2 - 14 + zy)
      ctx.font = '6px monospace'
      ctx.fillText('z', x + w / 2 + 1, y + h / 2 - 18 + zy)
      break
    }

    case 'plant': {
      // 花盆
      ctx.fillStyle = P.potBrown
      ctx.fillRect(x + 3, y + h - 12, w - 6, 12)
      ctx.fillRect(x + 1, y + h - 14, w - 2, 4)
      // 泥土
      ctx.fillStyle = '#5A3E28'
      ctx.fillRect(x + 4, y + h - 14, w - 8, 3)
      // 叶子
      ctx.fillStyle = P.plantGreen
      ctx.beginPath()
      ctx.arc(x + w / 2, y + h / 2 - 2, 10, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = P.plantDark
      ctx.beginPath()
      ctx.arc(x + w / 2 - 3, y + h / 2 - 5, 6, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = P.plantGreen
      ctx.beginPath()
      ctx.arc(x + w / 2 + 4, y + h / 2 - 8, 7, 0, Math.PI * 2)
      ctx.fill()
      break
    }

    case 'plant_small': {
      ctx.fillStyle = P.potBrown
      ctx.fillRect(x + 2, y + h - 8, w - 4, 8)
      ctx.fillStyle = P.plantGreen
      ctx.beginPath()
      ctx.arc(x + w / 2, y + h / 2 - 1, 6, 0, Math.PI * 2)
      ctx.fill()
      break
    }

    case 'poster': {
      // 画框
      ctx.fillStyle = P.posterFrame
      ctx.fillRect(x - 2, y - 2, w + 4, h + 4)
      // 画布底色
      if (item.variant === 'et') {
        ctx.fillStyle = '#1B2838'
        ctx.fillRect(x, y, w, h)
        // ET 月亮
        ctx.fillStyle = '#F0E060'
        ctx.beginPath()
        ctx.arc(x + 30, y + 15, 12, 0, Math.PI * 2)
        ctx.fill()
        // 自行车剪影
        ctx.fillStyle = '#111'
        ctx.fillRect(x + 10, y + 28, 28, 3)
        // 文字
        ctx.fillStyle = '#F0E060'
        ctx.font = 'bold 8px monospace'
        ctx.fillText('E.T.', x + 14, y + 46)
      } else if (item.variant === 'friends') {
        ctx.fillStyle = '#6B2D8B'
        ctx.fillRect(x, y, w, h)
        ctx.fillStyle = '#FFD700'
        ctx.font = 'bold 7px monospace'
        ctx.fillText('CENTRAL', x + 4, y + 15)
        ctx.fillText('PERK', x + 10, y + 25)
        // 咖啡杯图标
        ctx.fillStyle = '#FFF'
        ctx.fillRect(x + 15, y + 30, 12, 10)
        ctx.fillStyle = '#8B5A3C'
        ctx.fillRect(x + 16, y + 31, 10, 4)
      } else if (item.variant === 'chart') {
        ctx.fillStyle = '#1A2A3A'
        ctx.fillRect(x, y, w, h)
        // 监控图标
        ctx.strokeStyle = '#3ACA5A'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(x + 5, y + 35)
        ctx.lineTo(x + 15, y + 20)
        ctx.lineTo(x + 25, y + 30)
        ctx.lineTo(x + 35, y + 10)
        ctx.stroke()
        ctx.fillStyle = '#67D8EF'
        ctx.font = '7px monospace'
        ctx.fillText('MONITOR', x + 3, y + 44)
      } else if (item.variant === 'lobster') {
        ctx.fillStyle = '#2A1A0A'
        ctx.fillRect(x, y, w, h)
        ctx.fillStyle = '#E74C3C'
        ctx.font = '20px sans-serif'
        ctx.fillText('🦞', x + 12, y + 30)
        ctx.fillStyle = '#DAA520'
        ctx.font = '6px monospace'
        ctx.fillText('LOBSTER', x + 6, y + 44)
        ctx.fillText('STUDIO', x + 9, y + 44)
      } else {
        // 风景画
        ctx.fillStyle = '#87CEEB'
        ctx.fillRect(x, y, w, h * 0.5)
        ctx.fillStyle = '#5A9B4A'
        ctx.fillRect(x, y + h * 0.5, w, h * 0.3)
        ctx.fillStyle = '#3D7D32'
        ctx.fillRect(x, y + h * 0.8, w, h * 0.2)
        // 太阳
        ctx.fillStyle = '#F0E060'
        ctx.beginPath()
        ctx.arc(x + w - 12, y + 10, 6, 0, Math.PI * 2)
        ctx.fill()
      }
      break
    }

    case 'window': {
      // 窗框
      ctx.fillStyle = P.windowFrame
      ctx.fillRect(x - 3, y - 3, w + 6, h + 6)
      // 天空
      const skyGrad = ctx.createLinearGradient(x, y, x, y + h)
      skyGrad.addColorStop(0, '#5B9BD5')
      skyGrad.addColorStop(1, '#87CEEB')
      ctx.fillStyle = skyGrad
      ctx.fillRect(x, y, w, h)
      // 云朵
      ctx.fillStyle = 'rgba(255,255,255,0.7)'
      const cx1 = x + 25 + Math.sin(frame * 0.01) * 10
      ctx.fillRect(cx1, y + 12, 20, 6)
      ctx.fillRect(cx1 + 5, y + 8, 10, 4)
      const cx2 = x + 65 + Math.sin(frame * 0.008 + 2) * 8
      ctx.fillRect(cx2, y + 22, 16, 5)
      ctx.fillRect(cx2 + 3, y + 18, 8, 4)
      // 窗框十字
      ctx.fillStyle = P.windowFrame
      ctx.fillRect(x + w / 2 - 2, y, 4, h)
      ctx.fillRect(x, y + h / 2 - 2, w, 4)
      // 窗帘
      ctx.fillStyle = '#B85A5A'
      ctx.fillRect(x, y, 12, h)
      ctx.fillRect(x + w - 12, y, 12, h)
      // 窗帘褶皱
      ctx.fillStyle = 'rgba(0,0,0,0.1)'
      ctx.fillRect(x + 3, y, 2, h)
      ctx.fillRect(x + 7, y, 2, h)
      ctx.fillRect(x + w - 9, y, 2, h)
      ctx.fillRect(x + w - 5, y, 2, h)
      break
    }

    case 'clock': {
      // 钟面
      ctx.fillStyle = '#F5F0E0'
      ctx.beginPath()
      ctx.arc(x + w / 2, y + h / 2, w / 2, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = P.woodDark
      ctx.lineWidth = 3
      ctx.stroke()
      // 指针 - 随时间转动
      const cx = x + w / 2
      const cy = y + h / 2
      // 时针
      ctx.strokeStyle = '#333'
      ctx.lineWidth = 2
      const ha = (frame * 0.005) % (Math.PI * 2)
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(cx + Math.cos(ha) * 8, cy + Math.sin(ha) * 8)
      ctx.stroke()
      // 分针
      ctx.lineWidth = 1.5
      const ma = (frame * 0.02) % (Math.PI * 2)
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(cx + Math.cos(ma) * 11, cy + Math.sin(ma) * 11)
      ctx.stroke()
      // 中心点
      ctx.fillStyle = '#333'
      ctx.beginPath()
      ctx.arc(cx, cy, 2, 0, Math.PI * 2)
      ctx.fill()
      break
    }

    case 'lamp': {
      // 灯杆
      ctx.fillStyle = '#444'
      ctx.fillRect(x + 6, y + 15, 4, h - 15)
      // 底座
      ctx.fillStyle = '#555'
      ctx.fillRect(x + 2, y + h - 4, 12, 4)
      // 灯罩
      ctx.fillStyle = '#E8C870'
      ctx.fillRect(x, y, w, 16)
      ctx.fillStyle = '#D4B040'
      ctx.fillRect(x + 1, y + 1, w - 2, 14)
      // 灯光效果
      ctx.fillStyle = `rgba(255, 220, 100, ${0.06 + Math.sin(frame * 0.05) * 0.02})`
      ctx.beginPath()
      ctx.moveTo(x - 5, y + 16)
      ctx.lineTo(x + w + 5, y + 16)
      ctx.lineTo(x + w + 20, y + 60)
      ctx.lineTo(x - 20, y + 60)
      ctx.fill()
      break
    }

    case 'trash': {
      ctx.fillStyle = '#888'
      ctx.fillRect(x, y + 3, w, h - 3)
      ctx.fillStyle = '#999'
      ctx.fillRect(x - 1, y, w + 2, 5)
      ctx.fillStyle = '#666'
      ctx.fillRect(x + 4, y + 6, 2, h - 10)
      ctx.fillRect(x + 8, y + 6, 2, h - 10)
      break
    }
  }
}

// 绘制标题横幅
function drawBanner(ctx: CanvasRenderingContext2D, canvasW: number, y: number) {
  const bw = 260
  const bx = (canvasW - bw) / 2
  // 横幅背景
  ctx.fillStyle = P.banner
  ctx.fillRect(bx, y, bw, 26)
  // 金色边框
  ctx.strokeStyle = P.gold
  ctx.lineWidth = 2
  ctx.strokeRect(bx, y, bw, 26)
  // 装饰角
  ctx.fillStyle = P.gold
  ctx.fillRect(bx - 1, y - 1, 6, 6)
  ctx.fillRect(bx + bw - 5, y - 1, 6, 6)
  ctx.fillRect(bx - 1, y + 21, 6, 6)
  ctx.fillRect(bx + bw - 5, y + 21, 6, 6)
  // ★ 装饰
  ctx.fillStyle = P.gold
  ctx.font = '10px sans-serif'
  ctx.fillText('★', bx + 8, y + 18)
  ctx.fillText('★', bx + bw - 20, y + 18)
  // 标题文字
  ctx.fillStyle = P.text
  ctx.font = 'bold 13px "PingFang SC", sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('🦞  龙虾小队的办公室', canvasW / 2, y + 18)
  ctx.textAlign = 'left'
}

// 绘制区域标签 (游戏风)
function drawAreaLabel(ctx: CanvasRenderingContext2D, text: string, x: number, y: number) {
  ctx.fillStyle = 'rgba(58, 40, 32, 0.75)'
  ctx.fillRect(x, y, 70, 20)
  ctx.strokeStyle = P.gold
  ctx.lineWidth = 1
  ctx.strokeRect(x, y, 70, 20)
  ctx.fillStyle = P.text
  ctx.font = '11px "PingFang SC", sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(text, x + 35, y + 15)
  ctx.textAlign = 'left'
}

// ========== 动画循环 ==========
function animate() {
  animationId = requestAnimationFrame(animate)
  animationFrame.value++

  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.imageSmoothingEnabled = false
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // ===== 绘制墙壁 =====
  const wallGrad = ctx.createLinearGradient(0, 0, 0, 72)
  wallGrad.addColorStop(0, P.wallTop)
  wallGrad.addColorStop(1, P.wallBottom)
  ctx.fillStyle = wallGrad
  ctx.fillRect(0, 0, canvas.width, 72)

  // 墙裙线
  ctx.fillStyle = P.wallTrim
  ctx.fillRect(0, 68, canvas.width, 6)
  ctx.fillStyle = 'rgba(255,255,255,0.15)'
  ctx.fillRect(0, 68, canvas.width, 2)

  // ===== 绘制棋盘格地板 =====
  const tileSize = 32
  for (let ty = 74; ty < canvas.height - 32; ty += tileSize) {
    for (let tx = 0; tx < canvas.width; tx += tileSize) {
      const isLight = ((tx / tileSize) + (ty / tileSize)) % 2 === 0
      ctx.fillStyle = isLight ? P.floorA : P.floorB
      ctx.fillRect(tx, ty, tileSize, tileSize)
    }
  }

  // 地板底部阴影
  ctx.fillStyle = 'rgba(0,0,0,0.08)'
  ctx.fillRect(0, canvas.height - 32, canvas.width, 32)

  // ===== 绘制区域标签 =====
  drawAreaLabel(ctx, '💻 工作区', 300, 78)
  drawAreaLabel(ctx, '🛋️ 休息区', 840, 78)

  // ===== 绘制家具 (先画地毯、再画家具，最后画电脑) =====
  // 先画地面物品
  officeItems.filter(i => i.type === 'carpet').forEach(item => drawOfficeItem(ctx, item, animationFrame.value))
  // 再画墙面装饰
  officeItems.filter(i => ['poster', 'window', 'clock'].includes(i.type)).forEach(item => drawOfficeItem(ctx, item, animationFrame.value))
  // 然后画家具
  officeItems.filter(i => !['carpet', 'poster', 'window', 'clock', 'computer', 'coffee_cup', 'lamp'].includes(i.type)).forEach(item => drawOfficeItem(ctx, item, animationFrame.value))
  // 最后画桌面物品和灯
  officeItems.filter(i => ['computer', 'coffee_cup', 'lamp'].includes(i.type)).forEach(item => drawOfficeItem(ctx, item, animationFrame.value))

  // ===== 绘制工作区员工 =====
  workerStates.value.forEach((worker, index) => {
    if (index < workPositions.length) {
      const pos = workPositions[index]
      if (!pos) return
      const speedMultiplier = 0.5 + systemLoad.value * 1.5
      drawWorker(ctx, pos.x, pos.y, workerColors[index % workerColors.length] || '#3498DB', worker.status, speedMultiplier, animationFrame.value, 'work')
    }
  })

  // 休息区闲人
  const restCount = Math.max(0, 6 - Math.max(0, workerStates.value.length - 12))
  for (let i = 0; i < restCount; i++) {
    const pos = restPositions[i]
    if (!pos) continue
    drawWorker(ctx, pos.x, pos.y, workerColors[(i + workerStates.value.length) % workerColors.length] || '#3498DB', 'idle', 0.3, animationFrame.value, 'rest')
  }

  // ===== 绘制标题横幅 =====
  drawBanner(ctx, canvas.width, canvas.height - 30)

  // ===== 温暖的浮动粒子（灰尘/阳光粒子）=====
  const particleCount = Math.floor(3 + systemLoad.value * 8)
  for (let i = 0; i < particleCount; i++) {
    const px = (Math.sin(animationFrame.value * 0.008 + i * 1.7) * 0.5 + 0.5) * canvas.width
    const py = (Math.cos(animationFrame.value * 0.006 + i * 2.3) * 0.5 + 0.5) * (canvas.height - 50) + 30
    ctx.fillStyle = `rgba(255, 240, 200, ${0.2 + Math.sin(animationFrame.value * 0.03 + i) * 0.15})`
    ctx.beginPath()
    ctx.arc(px, py, 1.5, 0, Math.PI * 2)
    ctx.fill()
  }
}

// 初始化
function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  canvas.width = 1000
  canvas.height = 420
}

onMounted(async () => {
  initCanvas()
  animate()
  store.connect()
  await loadRecentRecords()
  recordTimer = window.setInterval(() => {
    loadRecentRecords().catch(() => {
      // ignore
    })
  }, 5000)
  const resizeCanvas = () => {
    if (canvasRef.value) {
      canvasRef.value.style.width = '100%'
      canvasRef.value.style.height = 'auto'
    }
  }
  window.addEventListener('resize', resizeCanvas)
  resizeCanvas()
})

onBeforeUnmount(() => {
  if (animationId) cancelAnimationFrame(animationId)
  window.removeEventListener('resize', initCanvas)
  if (recordTimer !== null) {
    window.clearInterval(recordTimer)
    recordTimer = null
  }
  store.disconnect()
})
</script>

<template>
  <div class="studio-page">
    <div class="studio-header pixel-card">
      <div class="header-info">
        <h2>🏢 像素办公室工作室</h2>
        <p>员工状态与系统负载实时同步</p>
      </div>
      <div class="header-stats">
        <span class="status-badge" :data-online="connected">
          {{ connected ? '🟢 实时同步中' : '🔴 连接断开' }}
        </span>
        <span class="load-badge">
          ⚡ 系统负载: {{ (systemLoad * 100).toFixed(0) }}%
        </span>
        <span class="people-badge">
          👥 在线员工: {{ workerStates.length }}人
        </span>
      </div>
    </div>

    <div class="office-container">
      <div class="office-wrapper" @mousemove="handleMouseMove" @mouseleave="handleMouseLeave">
        <canvas ref="canvasRef" class="office-canvas"></canvas>
      </div>
    </div>

    <div class="work-panels pixel-card">
      <section class="work-panel">
        <h3>🧭 实时工作进度</h3>
        <ul class="work-live-list">
          <li v-for="worker in workerStates" :key="worker.id">
            <div class="work-row">
              <strong>{{ worker.name }}</strong>
              <span>{{ worker.status }}</span>
            </div>
            <p v-if="worker.current_work">当前：{{ worker.current_work }}</p>
            <div v-if="worker.progress_percent !== null && worker.progress_percent !== undefined" class="work-progress-row">
              <div class="work-progress-track">
                <div class="work-progress-fill" :style="{ width: `${Math.max(0, Math.min(100, worker.progress_percent))}%` }" />
              </div>
              <span>{{ worker.progress_percent.toFixed(0) }}%</span>
            </div>
            <small v-if="worker.last_completed_work">最近完成：{{ worker.last_completed_work }}</small>
          </li>
        </ul>
      </section>
      <section class="work-panel">
        <h3>🧾 工作记录查询</h3>
        <ul class="work-record-list">
          <li v-for="item in recentRecords" :key="item.id">
            <div class="work-row">
              <strong>{{ item.node_id }}</strong>
              <span>{{ formatRecordTime(item.timestamp) }}</span>
            </div>
            <p>{{ item.title }}</p>
            <small v-if="item.detail">{{ item.detail }}</small>
            <div class="work-row">
              <span>{{ item.status }}</span>
              <span v-if="item.progress_percent !== null && item.progress_percent !== undefined">{{ item.progress_percent.toFixed(0) }}%</span>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <!-- Hover 悬浮窗 -->
    <div 
      v-if="hoveredWorker" 
      class="worker-tooltip pixel-card" 
      :style="{ left: mousePos.x + 15 + 'px', top: mousePos.y + 15 + 'px' }"
    >
      <div class="tooltip-header">
        <h4>{{ hoveredWorker.name || 'Unknown' }}</h4>
        <span class="status-dot" :data-status="hoveredWorker.status"></span>
      </div>
      <div class="tooltip-body">
        <p><span>节点 ID</span><span>{{ hoveredWorker.id }}</span></p>
        <p><span>CPU 负载</span><span>{{ typeof hoveredWorker.cpu_percent === 'number' ? hoveredWorker.cpu_percent.toFixed(1) : '0.0' }}%</span></p>
        <p><span>内存使用</span><span>{{ typeof hoveredWorker.mem_percent === 'number' ? hoveredWorker.mem_percent.toFixed(1) : '0.0' }}%</span></p>
        <p><span>当前任务</span><span>{{ hoveredWorker.task_count || 0 }}</span></p>
      </div>
    </div>

    <div class="studio-controls pixel-card">
      <div class="control-section">
        <h3>📋 区域说明</h3>
        <ul class="area-list">
          <li class="area-item">
            <span class="area-icon">💻</span>
            <strong class="area-title">工作区</strong>
            <span class="area-desc">12个工位，员工在工位上办公</span>
          </li>
          <li class="area-item">
            <span class="area-icon">🛋️</span>
            <strong class="area-title">休息区</strong>
            <span class="area-desc">沙发、书柜、茶几，空闲员工在此休息</span>
          </li>
          <li class="area-item">
            <span class="area-icon">🐱</span>
            <strong class="area-title">猫咪角</strong>
            <span class="area-desc">办公室吉祥物正在打盹</span>
          </li>
        </ul>
      </div>

      <div class="control-section">
        <h3>😊 状态说明</h3>
        <ul class="status-list">
          <li>😄 专注工作：节点运行正常（active）</li>
          <li>😐 平静摸鱼：节点空闲（idle）</li>
          <li>😨 惊讶流汗：节点告警（warning），周围有红色光圈</li>
          <li>😴 打瞌睡 Z：节点离线（offline）</li>
          <li>⚡ 动作频率：随系统负载变化，负载越高动得越快</li>
          <li>✨ 阳光粒子：数量随系统负载增加</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ============================================================
   像素风 (Pixel Art) 游戏UI — LobsterStudio
   ============================================================ */

.studio-page {
  position: relative;
  width: 100%;
  min-height: calc(100vh - 60px);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;

  background:
    linear-gradient(180deg, #1A1210 0%, #2A1E18 40%, #1E1614 100%);
  color: #FFF8E8;
}

/* ---------- 像素风卡片 ---------- */
.pixel-card {
  position: relative;
  background: linear-gradient(180deg, #2E2218 0%, #241A12 100%);
  border: 3px solid #8B6F4E;
  border-radius: 4px;
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 232, 0.08),
    inset 0 -1px 0 rgba(0, 0, 0, 0.3),
    0 4px 16px rgba(0, 0, 0, 0.5);
}

/* 双线边框效果 */
.pixel-card::before {
  content: '';
  position: absolute;
  inset: 3px;
  border: 1px solid rgba(139, 111, 78, 0.4);
  border-radius: 2px;
  pointer-events: none;
}

/* ---------- Header ---------- */
.studio-header {
  width: 100%;
  max-width: 1100px;
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
}

.header-info h2 {
  margin: 0 0 4px 0;
  font-size: 1.2rem;
  font-weight: 700;
  color: #DAA520;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

.header-info p {
  margin: 0;
  font-size: 0.82rem;
  color: rgba(255, 248, 232, 0.55);
}

.header-stats {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.status-badge, .load-badge, .people-badge {
  padding: 5px 12px;
  border-radius: 3px;
  font-size: 0.78rem;
  font-weight: 500;
  white-space: nowrap;
  border: 1px solid #8B6F4E;
  background: rgba(58, 40, 32, 0.7);
  color: #FFF8E8;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}

.status-badge[data-online="true"] {
  color: #7BC96A;
  border-color: rgba(123, 201, 106, 0.5);
}

.status-badge[data-online="false"] {
  color: #E88;
  border-color: rgba(238, 136, 136, 0.5);
  animation: blink 1.5s ease-in-out infinite;
}

.load-badge {
  color: #F0D060;
  border-color: rgba(240, 208, 96, 0.4);
}

.people-badge {
  color: #87CEEB;
  border-color: rgba(135, 206, 235, 0.4);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* ---------- 悬浮窗 ---------- */
.worker-tooltip {
  position: fixed;
  z-index: 1000;
  padding: 12px;
  width: 200px;
  pointer-events: none;
  background: rgba(36, 26, 18, 0.95);
  backdrop-filter: blur(4px);
  transform: translate(0, 0);
  transition: all 0.1s ease-out;
}

.tooltip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px dashed rgba(139, 111, 78, 0.5);
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.tooltip-header h4 {
  margin: 0;
  font-size: 0.95rem;
  color: #DAA520;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid #000;
}

.status-dot[data-status="active"] { background: #2ECC71; box-shadow: 0 0 5px #2ECC71; }
.status-dot[data-status="warning"] { background: #E74C3C; box-shadow: 0 0 5px #E74C3C; }
.status-dot[data-status="idle"] { background: #3498DB; box-shadow: 0 0 5px #3498DB; }
.status-dot[data-status="offline"] { background: #95A5A6; }

.tooltip-body p {
  margin: 5px 0;
  font-size: 0.82rem;
  display: flex;
  justify-content: space-between;
  color: rgba(255, 248, 232, 0.85);
}

.tooltip-body p span:last-child {
  font-family: monospace;
  color: #FFF8E8;
  font-weight: 500;
}

/* ---------- Canvas 容器 ---------- */
.office-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 1100px;
}

.office-wrapper {
  position: relative;
  border-radius: 4px;
  padding: 4px;
  width: 100%;
  background: #8B6F4E;
  box-shadow:
    0 6px 24px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 248, 232, 0.15);
}

/* 外框装饰角 */
.office-wrapper::before {
  content: '';
  position: absolute;
  inset: 6px;
  border: 2px solid rgba(218, 165, 32, 0.35);
  border-radius: 2px;
  pointer-events: none;
  z-index: 1;
}

.office-canvas {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 2px;
  image-rendering: pixelated;
  image-rendering: -moz-crisp-edges;
  image-rendering: crisp-edges;
}

.work-panels {
  width: 100%;
  max-width: 1100px;
  padding: 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.work-panel h3 {
  margin: 0 0 10px;
  font-size: 0.92rem;
  color: #f5d06a;
}

.work-live-list,
.work-record-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
  max-height: 230px;
  overflow: auto;
}

.work-live-list li,
.work-record-list li {
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 248, 232, 0.04);
  padding: 8px 10px;
}

.work-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.82rem;
}

.work-live-list p,
.work-record-list p {
  margin: 4px 0;
  font-size: 0.84rem;
  color: rgba(255, 248, 232, 0.86);
}

.work-live-list small,
.work-record-list small {
  color: rgba(255, 248, 232, 0.65);
  font-size: 0.76rem;
}

.work-progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.76rem;
}

.work-progress-track {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  overflow: hidden;
}

.work-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #06b6d4, #10b981);
  border-radius: 999px;
}

/* ---------- 控制面板 ---------- */
.studio-controls {
  width: 100%;
  max-width: 1100px;
  padding: 18px 20px;
  z-index: 10;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.control-section h3 {
  margin: 0 0 12px 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: #DAA520;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(139, 111, 78, 0.4);
}

.area-list, .status-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}

.area-list li, .status-list li {
  font-size: 0.82rem;
  color: rgba(255, 248, 232, 0.72);
  line-height: 1.5;
  padding: 5px 8px;
  border-radius: 3px;
  background: rgba(255, 248, 232, 0.03);
  border-left: 2px solid rgba(139, 111, 78, 0.3);
  transition: all 0.2s ease;
}

.area-list li:hover, .status-list li:hover {
  background: rgba(255, 248, 232, 0.06);
  border-left-color: #DAA520;
  color: #FFF8E8;
  padding-left: 12px;
}

.area-item {
  display: grid;
  grid-template-columns: 36px 92px 1fr;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 8px 12px !important;
  border-left: 3px solid rgba(218, 165, 32, 0.35) !important;
  background: linear-gradient(90deg, rgba(255, 214, 143, 0.08), rgba(255, 248, 232, 0.03));
}

.area-item:hover {
  border-left-color: #DAA520 !important;
  background: linear-gradient(90deg, rgba(255, 214, 143, 0.14), rgba(255, 248, 232, 0.06)) !important;
}

.area-icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(218, 165, 32, 0.28);
  font-size: 15px;
}

.area-title {
  color: #F5D06A;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.area-desc {
  color: rgba(255, 248, 232, 0.85);
  font-size: 0.86rem;
}

/* ---------- 响应式 ---------- */
@media (max-width: 968px) {
  .studio-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  .header-stats {
    width: 100%;
    justify-content: flex-start;
  }
  .studio-controls {
    grid-template-columns: 1fr;
  }

  .work-panels {
    grid-template-columns: 1fr;
  }

  .area-item {
    grid-template-columns: 32px 1fr;
    row-gap: 3px;
  }

  .area-desc {
    grid-column: 1 / -1;
    padding-left: 1px;
  }
}
</style>
