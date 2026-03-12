<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app">
    <!-- 导航栏 -->
    <nav class="nav-bar">
      <div class="nav-content">
        <div class="nav-brand">
          🦞 Lobster Monitor
        </div>
        <div class="nav-links">
          <RouterLink to="/" class="nav-link" active-class="active">
            监控面板
          </RouterLink>
          <RouterLink to="/studio" class="nav-link" active-class="active">
            3D工作室
          </RouterLink>
        </div>
      </div>
    </nav>

    <!-- 路由视图 -->
    <RouterView />
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
}

.nav-bar {
  position: sticky;
  top: 0;
  z-index: 1000;
  backdrop-filter: blur(20px) saturate(140%);
  background: linear-gradient(140deg, rgba(210, 239, 255, 0.12), rgba(255, 255, 255, 0.04));
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.nav-content {
  max-width: 1240px;
  margin: 0 auto;
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-brand {
  font-size: 1.2rem;
  font-weight: 600;
  color: #e2f4ff;
}

.nav-links {
  display: flex;
  gap: 20px;
}

.nav-link {
  padding: 8px 16px;
  border-radius: 12px;
  color: rgba(226, 244, 255, 0.7);
  text-decoration: none;
  transition: all 0.2s ease;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #e2f4ff;
}

.nav-link.active {
  background: linear-gradient(145deg, rgba(6, 182, 212, 0.28), rgba(6, 182, 212, 0.14));
  color: #e2f4ff;
  border: 1px solid rgba(6, 182, 212, 0.3);
}
</style>
