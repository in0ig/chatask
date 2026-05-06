/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_BASE_API: string
  readonly VITE_API_TARGET?: string
  /** 直连后端 WebSocket（慎用；远程访问应留空走 Vite 代理） */
  readonly VITE_WS_DIRECT_URL?: string
  readonly VITE_ENABLE_STREAMING?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}