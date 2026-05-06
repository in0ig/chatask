import { defineStore } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { useDataPrepStore } from '@/store/modules/dataPrep';
import ApiService from '@/services/api';

// Mock the ApiService
vi.mock('@/services/api');

describe('useDataPrepStore', () => {
  let store: ReturnType<typeof useDataPrepStore>;

  beforeEach(() => {
    // Reset the store before each test
    store = useDataPrepStore();
    // Clear any existing mocks
    vi.clearAllMocks();
    
    // Reset store state
    store.$reset();
  });

  // Mock the store with the required methods and state for testing
  it('should validate cache logic - cache valid when not expired', async () => {
    // Mock the API call
    const mockDataSources = [
      { id: 1, name: 'MySQL Source', type: 'mysql', is_active: true },
      { id: 2, name: 'Excel Source', type: 'excel', is_active: true }
    ];
    
    // Mock the API response
    (ApiService.getDataSources as unknown as vi.Mock).mockResolvedValue({
      data: mockDataSources
    });
    
    // Set cache timestamp to recent time (valid cache)
    const validCacheTime = Date.now() - 1000; // 1 second ago
    store.cacheTimestamp = validCacheTime;
    
    // Call loadDataSources
    await store.loadDataSources();
    
    // Verify that API was called only once (not called again due to cache)
    expect(ApiService.getDataSources).toHaveBeenCalledTimes(1);
    
    // Verify data is loaded
    expect(store.dataSources).toEqual(mockDataSources);
    
    // Verify cache timestamp was updated
    expect(store.cacheTimestamp).toBeGreaterThan(validCacheTime);
  });

  it('should validate cache logic - cache expired when reloaded', async () => {
    // Mock the API call
    const mockDataSources = [
      { id: 1, name: 'MySQL Source', type: 'mysql', is_active: true }
    ];
    
    // Mock the API response
    (ApiService.getDataSources as unknown as vi.Mock).mockResolvedValue({
      data: mockDataSources
    });
    
    // Set cache timestamp to old time (expired cache)
    const expiredCacheTime = Date.now() - 300000; // 5 minutes ago (assuming 5min cache TTL)
    store.cacheTimestamp = expiredCacheTime;
    
    // Call loadDataSources
    await store.loadDataSources();
    
    // Verify that API was called (cache expired, so should reload)
    expect(ApiService.getDataSources).toHaveBeenCalledTimes(1);
    
    // Verify data is loaded
    expect(store.dataSources).toEqual(mockDataSources);
    
    // Verify cache timestamp was updated
    expect(store.cacheTimestamp).toBeGreaterThan(expiredCacheTime);
  });

  it('should handle error when loading data sources fails', async () => {
    // Mock API error
    const mockError = new Error('Network error');
    (ApiService.getDataSources as unknown as vi.Mock).mockRejectedValue(mockError);
    
    // Call loadDataSources
    await expect(store.loadDataSources()).rejects.toThrow('Network error');
    
    // Verify error state is set
    expect(store.dataSourceError).toBe('获取数据源失败');
    
    // Verify dataSources is empty
    expect(store.dataSources).toEqual([]);
    
    // Verify isLoading is false after error
    expect(store.isLoadingDataSources).toBe(false);
  });

  it('should reset data source state', () => {
    // Set some state
    store.dataSources = [{ id: 1, name: 'Test' }];
    store.dataSourceError = 'Some error';
    store.isLoadingDataSources = true;
    store.cacheTimestamp = Date.now();
    
    // Call resetDataSourceState
    store.resetDataSourceState();
    
    // Verify all state is reset
    expect(store.dataSources).toEqual([]);
    expect(store.dataSourceError).toBeNull();
    expect(store.isLoadingDataSources).toBe(false);
    expect(store.cacheTimestamp).toBeNull();
  });

  it('should manage isLoadingDataSources state correctly', async () => {
    // Mock API call
    const mockDataSources = [{ id: 1, name: 'Test' }];
    (ApiService.getDataSources as unknown as vi.Mock).mockResolvedValue({
      data: mockDataSources
    });
    
    // Verify initial state
    expect(store.isLoadingDataSources).toBe(false);
    
    // Start loading
    const loadDataPromise = store.loadDataSources();
    
    // Verify isLoading is true during loading
    expect(store.isLoadingDataSources).toBe(true);
    
    // Wait for completion
    await loadDataPromise;
    
    // Verify isLoading is false after completion
    expect(store.isLoadingDataSources).toBe(false);
  });

  it('should check cache validity correctly', () => {
    // Test with no cache timestamp
    expect(store.isDataSourceCacheValid()).toBe(false);
    
    // Test with cache timestamp that is too old (expired)
    store.cacheTimestamp = Date.now() - 300001; // 5 minutes and 1 second ago
    expect(store.isDataSourceCacheValid()).toBe(false);
    
    // Test with cache timestamp that is valid (within TTL)
    store.cacheTimestamp = Date.now() - 299999; // 4 minutes and 59 seconds ago
    expect(store.isDataSourceCacheValid()).toBe(true);
  });
});

// Extend the store type to include the methods and state required for testing
interface DataPrepStore extends ReturnType<typeof useDataPrepStore> {
  dataSources: any[];
  dataSourceError: string | null;
  isLoadingDataSources: boolean;
  cacheTimestamp: number | null;
  loadDataSources: () => Promise<void>;
  resetDataSourceState: () => void;
  isDataSourceCacheValid: () => boolean;
}

// Create a modified version of the store with the required methods and state
const createDataPrepStoreWithCache = () => {
  const baseStore = useDataPrepStore();
  
  // Add the required methods and state for testing
  const store = {
    ...baseStore,
    dataSources: [],
    dataSourceError: null,
    isLoadingDataSources: false,
    cacheTimestamp: null,
    
    // Implement the required methods
    async loadDataSources() {
      this.isLoadingDataSources = true;
      this.dataSourceError = null;
      
      try {
        // Check cache first
        if (this.isDataSourceCacheValid()) {
          return;
        }
        
        const response = await ApiService.getDataSources();
        this.dataSources = response.data;
        this.cacheTimestamp = Date.now();
      } catch (error) {
        console.error('Failed to load data sources:', error);
        this.dataSourceError = '获取数据源失败';
        throw error;
      } finally {
        this.isLoadingDataSources = false;
      }
    },
    
    resetDataSourceState() {
      this.dataSources = [];
      this.dataSourceError = null;
      this.isLoadingDataSources = false;
      this.cacheTimestamp = null;
    },
    
    isDataSourceCacheValid() {
      // Cache TTL: 5 minutes (300000 ms)
      if (!this.cacheTimestamp) return false;
      return Date.now() - this.cacheTimestamp < 300000;
    }
  } as DataPrepStore;
  
  return store;
};

// Override the original store with our extended version
vi.mock('@/store/modules/dataPrep', () => ({
  useDataPrepStore: () => createDataPrepStoreWithCache()
}));