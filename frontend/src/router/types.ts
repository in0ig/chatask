/**
 * 路由元信息类型定义
 */
export interface RouteMeta extends Record<string | number | symbol, any> {
  /** 页面标题 */
  title?: string
  /** 是否需要认证 */
  requiresAuth?: boolean
  /** 权限要求 */
  permissions?: string[]
  /** 面包屑导航 */
  breadcrumb?: BreadcrumbItem[]
  /** 是否缓存页面 */
  keepAlive?: boolean
  /** 页面图标 */
  icon?: string
}

/**
 * 面包屑导航项
 */
export interface BreadcrumbItem {
  /** 显示文本 */
  text: string
  /** 路由路径 */
  path?: string
  /** 是否为当前页面 */
  active?: boolean
}

/**
 * 数据准备模块路由名称常量
 */
export const DATA_PREP_ROUTES = {
  /** 数据准备主页 */
  DATA_PREPARATION: 'DataPreparation',
  /** 数据源管理 */
  DATA_SOURCES: 'DataSources',
  /** 数据表管理 */
  DATA_TABLES: 'DataTables',
  /** 字段配置 */
  TABLE_FIELDS: 'TableFields',
  /** 字典表管理 */
  DICTIONARIES: 'Dictionaries',
  /** 表关联管理 */
  TABLE_RELATIONS: 'TableRelations'
} as const

/**
 * 路由工具函数
 */
export class RouteUtils {
  /**
   * 生成面包屑导航
   */
  static generateBreadcrumb(routeName: string): BreadcrumbItem[] {
    const breadcrumbs: BreadcrumbItem[] = [
      { text: '首页', path: '/' }
    ]

    switch (routeName) {
      case DATA_PREP_ROUTES.DATA_SOURCES:
        breadcrumbs.push(
          { text: '数据准备', path: '/data-prep' },
          { text: '数据源管理', active: true }
        )
        break
      case DATA_PREP_ROUTES.DATA_TABLES:
        breadcrumbs.push(
          { text: '数据准备', path: '/data-prep' },
          { text: '数据表管理', active: true }
        )
        break
      case DATA_PREP_ROUTES.TABLE_FIELDS:
        breadcrumbs.push(
          { text: '数据准备', path: '/data-prep' },
          { text: '数据表管理', path: '/data-prep/tables' },
          { text: '字段配置', active: true }
        )
        break
      case DATA_PREP_ROUTES.DICTIONARIES:
        breadcrumbs.push(
          { text: '数据准备', path: '/data-prep' },
          { text: '字典表管理', active: true }
        )
        break
      case DATA_PREP_ROUTES.TABLE_RELATIONS:
        breadcrumbs.push(
          { text: '数据准备', path: '/data-prep' },
          { text: '表关联管理', active: true }
        )
        break
      default:
        breadcrumbs.push({ text: '数据准备', active: true })
    }

    return breadcrumbs
  }

  /**
   * 检查路由权限
   */
  static hasPermission(permissions: string[], userPermissions: string[]): boolean {
    if (!permissions || permissions.length === 0) {
      return true
    }
    return permissions.some(permission => userPermissions.includes(permission))
  }

  /**
   * 获取路由标题
   */
  static getRouteTitle(routeName: string): string {
    const titleMap: Record<string, string> = {
      [DATA_PREP_ROUTES.DATA_PREPARATION]: '数据准备',
      [DATA_PREP_ROUTES.DATA_SOURCES]: '数据源管理',
      [DATA_PREP_ROUTES.DATA_TABLES]: '数据表管理',
      [DATA_PREP_ROUTES.TABLE_FIELDS]: '字段配置',
      [DATA_PREP_ROUTES.DICTIONARIES]: '字典表管理',
      [DATA_PREP_ROUTES.TABLE_RELATIONS]: '表关联管理'
    }
    return titleMap[routeName] || '未知页面'
  }
}