import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import LobsterStudio from '../views/LobsterStudio.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/studio',
    name: 'LobsterStudio',
    component: LobsterStudio
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
