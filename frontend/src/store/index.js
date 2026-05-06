import { createStore } from 'vuex'

const store = createStore({
  state: {
    currentQuery: '',
    isLoading: false,
    errorMessage: '',
    result: null,
    aiExplanation: '',
    dataSources: [],
    activeDataSource: null,
    historyQueries: [
      '上月销售额最高的产品是什么？',
      '各区域销售对比',
      '客户转化率趋势'
    ],
    sessions: [
      { id: 'sess_1', name: '新会话' },
      { id: 'sess_2', name: '会话1' }
    ],
    currentSession: null
  },
  mutations: {
    setCurrentQuery(state, query) {
      state.currentQuery = query;
    },
    setLoading(state, loading) {
      state.isLoading = loading;
    },
    setErrorMessage(state, message) {
      state.errorMessage = message;
    },
    setResult(state, result) {
      state.result = result;
      state.aiExplanation = result.raw.length > 0 ? 
        `根据销售数据分析，${result.data[0].label} 是${result.chartTitle}中表现最佳的产品...` :
        '已成功解析您的查询并返回相关数据。';
    },
    addDataSource(state, source) {
      state.dataSources.push(source);
      if (!state.activeDataSource) {
        state.activeDataSource = source;
      }
    },
    activateDataSource(state, source) {
      state.activeDataSource = source;
      state.result = null;
      state.aiExplanation = '';
    },
    addToHistory(state, query) {
      if (!state.historyQueries.includes(query)) {
        state.historyQueries.unshift(query);
        if (state.historyQueries.length > 5) {
          state.historyQueries.pop();
        }
      }
    },
    switchSession(state, session) {
      state.currentSession = session;
    },
    createNewSession(state) {
      const newSession = {
        id: `sess_${Date.now()}`,
        name: `会话${state.sessions.length + 1}`
      };
      state.sessions.unshift(newSession);
      state.currentSession = newSession;
    }
  },
  actions: {
    async processQuery({ commit }, query) {
      try {
        commit('setLoading', true);
        commit('setErrorMessage', '');
        
        // 调用后端API
        const response = await fetch('/api/query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ text: query })
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || '查询处理失败');
        }
        
        const data = await response.json();
        commit('setResult', data.result);
        commit('addToHistory', query);
      } catch (error) {
        commit('setErrorMessage', error.message);
      } finally {
        commit('setLoading', false);
      }
    },
    async uploadFile({ commit }, file) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/datasources/upload', {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          throw new Error('文件上传失败');
        }
        
        const dataSource = await response.json();
        commit('addDataSource', dataSource);
      } catch (error) {
        commit('setErrorMessage', error.message);
      }
    },
    async activateDataSource({ commit }, sourceId) {
      try {
        const response = await fetch(`/api/datasources/${sourceId}/activate`, {
          method: 'PUT'
        });
        
        if (!response.ok) {
          throw new Error('激活数据源失败');
        }
        
        const data = await response.json();
        if (data.success) {
          commit('activateDataSource', sourceId);
        }
      } catch (error) {
        commit('setErrorMessage', error.message);
      }
    }
  },
  getters: {
    hasActiveDataSource: (state) => {
      return !!state.activeDataSource;
    }
  }
});

export default store;