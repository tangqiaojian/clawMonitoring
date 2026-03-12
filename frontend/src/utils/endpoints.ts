const defaultApiBase = `${window.location.protocol}//${window.location.hostname}:8000`
const defaultWsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
const defaultWsStreamBase = `${defaultWsProtocol}://${window.location.hostname}:8000/ws/stream`

export const API_BASE = (import.meta.env.VITE_API_BASE || defaultApiBase).replace(/\/+$/, '')
export const WS_STREAM_BASE = import.meta.env.VITE_WS_BASE || defaultWsStreamBase
