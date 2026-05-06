import { defineStore } from 'pinia';

export const useConfigStore = defineStore('config', {
  state: () => ({
    intelligentTools: {
      enableDataInterpretation: true,
      enableSmartSuggestions: false,
      enableAnomalyDetection: true
    }
  }),

  getters: {
    getDataInterpretationEnabled: (state) => state.intelligentTools.enableDataInterpretation,
    getSmartSuggestionsEnabled: (state) => state.intelligentTools.enableSmartSuggestions,
    getAnomalyDetectionEnabled: (state) => state.intelligentTools.enableAnomalyDetection
  },

  actions: {
    updateIntelligentToolConfig(key: keyof typeof this.intelligentTools, value: boolean) {
      this.intelligentTools = {
        ...this.intelligentTools,
        [key]: value
      };
    }
  }
});
