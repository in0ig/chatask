import { createRouter, createWebHistory } from 'vue-router'
import type { RouteMeta } from './types'
import { DATA_PREP_ROUTES, RouteUtils } from './types'
import { authGuard, permissionGuard, titleGuard, RouteLoadingManager } from './guards'

// 创建日志函数
const createRouterLog = () => {
  const logKey = 'routerLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load router logs from localStorage');
  }
  return { logs, logKey };
};

const addRouterLog = (type: string, message: string, data: any = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'navigation-start':
      console.groupCollapsed('%cRouter Navigation Started', 'color: #1890ff; font-weight: bold');
      console.log('From:', message);
      console.log('To:', data?.to);
      console.log('Query:', data?.query);
      console.groupEnd();
      break;
    case 'navigation-success':
      console.groupCollapsed('%cRouter Navigation Successful', 'color: #52c41a; font-weight: bold');
      console.log('To:', message);
      console.log('From:', data?.from);
      console.log('Hash:', data?.hash);
      console.groupEnd();
      break;
    case 'navigation-error':
      console.groupCollapsed('%cRouter Navigation Error', 'color: red; font-weight: bold');
      console.log('Error:', message);
      console.log('To:', data?.to);
      console.log('From:', data?.from);
      console.log('Details:', data?.error);
      console.groupEnd();
      break;
    case 'route-change':
      console.groupCollapsed('%cRoute Changed', 'color: #666; font-weight: bold');
      console.log('Current route:', message);
      console.log('Params:', data?.params);
      console.log('Query:', data?.query);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createRouterLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save router logs to localStorage');
  }
};

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: {
      title: '首页',
      keepAlive: true
    } as RouteMeta
  },
  // ChatBI 对话界面路由 (暂时注释，文件不存在)
  /*
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/Chat/ChatView.vue'),
    meta: {
      title: 'ChatBI 对话',
      requiresAuth: true,
      keepAlive: true,
      icon: 'chat-dot-round'
    } as RouteMeta
  },
  */
  // ChatBI 数据源管理路由
  {
    path: '/chatbi/datasources',
    name: 'ChatBIDataSources',
    component: () => import('@/views/DataSource/DataSourceManager.vue'),
    meta: {
      title: 'ChatBI 数据源管理',
      requiresAuth: true,
      keepAlive: true,
      icon: 'database'
    } as RouteMeta
  },
  // Prompt 测试页面
  {
    path: '/prompt-test',
    name: 'PromptTest',
    component: () => import('@/views/PromptTest.vue'),
    meta: {
      title: 'Prompt 测试',
      requiresAuth: false,
      keepAlive: false,
      icon: 'document'
    } as RouteMeta
  },
  {
    path: '/data-prep',
    name: DATA_PREP_ROUTES.DATA_PREPARATION,
    component: () => import('@/views/DataPrep/DataPreparationManager.vue'),
    redirect: '/data-prep/sources',
    meta: {
      title: '数据准备',
      requiresAuth: true,
      keepAlive: true,
      icon: 'database'
    } as RouteMeta,
    children: [
      {
        path: 'sources',
        name: DATA_PREP_ROUTES.DATA_SOURCES,
        component: () => import('@/views/DataPrep/DataSources/DataSourceList.vue'),
        meta: {
          title: '数据源管理',
          requiresAuth: true,
          keepAlive: true,
          icon: 'server',
          breadcrumb: RouteUtils.generateBreadcrumb(DATA_PREP_ROUTES.DATA_SOURCES)
        } as RouteMeta
      },
      {
        path: 'tables',
        name: DATA_PREP_ROUTES.DATA_TABLES,
        component: () => import('@/views/DataPrep/DataTables/DataTableManager.vue'),
        meta: {
          title: '数据表管理',
          requiresAuth: true,
          keepAlive: true,
          icon: 'table',
          breadcrumb: RouteUtils.generateBreadcrumb(DATA_PREP_ROUTES.DATA_TABLES)
        } as RouteMeta
      },
      {
        path: 'tables/:tableId/fields',
        name: DATA_PREP_ROUTES.TABLE_FIELDS,
        component: () => import('@/views/DataPrep/DataTables/DataTableManager.vue'),
        props: true,
        meta: {
          title: '字段配置',
          requiresAuth: true,
          keepAlive: false,
          icon: 'setting',
          breadcrumb: RouteUtils.generateBreadcrumb(DATA_PREP_ROUTES.TABLE_FIELDS)
        } as RouteMeta
      },
      {
        path: 'dictionaries',
        name: DATA_PREP_ROUTES.DICTIONARIES,
        component: () => import('@/views/DataPrep/Dictionaries/DictionaryManager.vue'),
        meta: {
          title: '字典表管理',
          requiresAuth: true,
          keepAlive: true,
          icon: 'book',
          breadcrumb: RouteUtils.generateBreadcrumb(DATA_PREP_ROUTES.DICTIONARIES)
        } as RouteMeta
      },
      {
        path: 'relations',
        name: DATA_PREP_ROUTES.TABLE_RELATIONS,
        component: () => import('@/views/DataPrep/Relations/RelationManager.vue'),
        meta: {
          title: '表关联管理',
          requiresAuth: true,
          keepAlive: true,
          icon: 'link',
          breadcrumb: RouteUtils.generateBreadcrumb(DATA_PREP_ROUTES.TABLE_RELATIONS)
        } as RouteMeta
      }
    ]
  },
  // 保持其他现有路由
  {
    path: '/project-info',
    name: 'ProjectInfo',
    component: () => import('@/views/ProjectInfo.vue'),
    meta: {
      title: '项目信息'
    } as RouteMeta
  },
  {
    path: '/team-members',
    name: 'TeamMembers',
    component: () => import('@/views/TeamMembers.vue'),
    meta: {
      title: '团队成员'
    } as RouteMeta
  },
  {
    path: '/resource-permissions',
    name: 'ResourcePermissions',
    component: () => import('@/views/ResourcePermissions.vue'),
    meta: {
      title: '资源权限'
    } as RouteMeta
  },
  // 兼容旧路由，重定向到新路由
  {
    path: '/data-prep/manager',
    redirect: '/data-prep/sources'
  },
  {
    path: '/data-prep/entry',
    redirect: '/data-prep/tables'
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫 - 记录导航开始和权限检查
router.beforeEach((to, from, next) => {
  addRouterLog('navigation-start', from.fullPath, {
    to: to.fullPath,
    query: to.query
  });

  // 设置加载状态
  RouteLoadingManager.setLoading(true)

  // 执行认证检查
  authGuard(to, from, next)
});

// 导航守卫 - 记录导航成功和设置页面标题
router.afterEach((to, from) => {
  addRouterLog('navigation-success', to.fullPath, {
    from: from.fullPath,
    hash: to.hash
  });
  addRouterLog('route-change', to.fullPath, {
    params: to.params,
    query: to.query
  });

  // 设置页面标题
  titleGuard(to, from)

  // 清除加载状态
  RouteLoadingManager.setLoading(false)
});

// 导航守卫 - 记录导航错误
router.onError((error, to, from) => {
  addRouterLog('navigation-error', error.message, {
    to: to?.fullPath || 'unknown',
    from: from?.fullPath || 'unknown',
    error: error
  });
});

export default router
