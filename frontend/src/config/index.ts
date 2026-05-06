/**
 * 统一 API 配置
 *
 * HTTP：相对路径 /api，开发时由 Vite proxy（VITE_API_TARGET）转发。
 *
 * WebSocket：
 *   默认与页面同源（如 ws://内网主机:5173/api/stream/ws/...），经 Vite /api 代理到后端，
 *   这样他人用浏览器访问远程 dev 时不会误连到自己电脑的 localhost。
 *   若必须绕过代理直连后端，可在 .env.local 设置 VITE_WS_DIRECT_URL=ws://127.0.0.1:8000
 */

/**
 * 构建 WebSocket 连接地址
 */
export function buildWsUrl(sessionId: string): string {
  const direct = import.meta.env.VITE_WS_DIRECT_URL
  if (direct) {
    const base = String(direct).replace(/\/$/, '')
    return `${base}/api/stream/ws/${sessionId}`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/api/stream/ws/${sessionId}`
}
