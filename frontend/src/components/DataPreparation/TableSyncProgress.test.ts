
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, VueWrapper } from '@vue/test-utils';
import { ElDialog, ElProgress, ElButton, ElIcon } from 'element-plus';
import { CircleCheck, CircleClose } from '@element-plus/icons-vue';
import TableSyncProgress from '@/components/DataPreparation/TableSyncProgress.vue';
import { useDataPreparationStore } from '@/store/modules/dataPreparation';

// Mock the store
vi.mock('@/store/modules/dataPreparation', () => ({
  useDataPreparationStore: vi.fn(() => ({
    syncTables: vi.fn(),
  })),
}));

const mockDataPreparationStore = useDataPreparationStore();

// A helper function to tick timers and flush promises
const flushPromises = async () => {
    vi.runAllTimers();
    await new Promise(resolve => setImmediate(resolve));
};

describe('TableSyncProgress.vue', () => {
  let wrapper: VueWrapper<any>;

  beforeEach(() => {
    vi.useFakeTimers();
    // Reset mocks before each test
    vi.clearAllMocks();
    (mockDataPreparationStore.syncTables as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
    if (wrapper) {
      wrapper.unmount();
    }
  });

  const createComponent = (props = {}) => {
    const defaultProps = {
      visible: false,
      tableIds: ['table1'],
      tableName: '测试表',
    };
    return mount(TableSyncProgress, {
      props: { ...defaultProps, ...props },
      global: {
        components: {
          ElDialog,
          ElProgress,
          ElButton,
          ElIcon,
          CircleCheck,
          CircleClose,
        },
      },
    });
  };

  describe('1. 属性(Props)和基础渲染', () => {
    it('当 `visible` 为 false 时，对话框不应被渲染', () => {
      wrapper = createComponent({ visible: false });
      expect(wrapper.find('.el-dialog').exists()).toBe(false);
    });

    it('当 `visible` 为 true 时，对话框应该可见，并显示正确的标题', async () => {
      wrapper = createComponent({ visible: true });
      await flushPromises();
      const dialog = wrapper.findComponent(ElDialog);
      expect(dialog.exists()).toBe(true);
      expect(dialog.props('title')).toBe('正在同步表 测试表');
    });

    it('当 `tableName` 属性改变时，标题应相应更新', async () => {
      wrapper = createComponent({ visible: true });
      await flushPromises();
      expect(wrapper.findComponent(ElDialog).props('title')).toBe('正在同步表 测试表');
      await wrapper.setProps({ tableName: '另一个表' });
      expect(wrapper.findComponent(ElDialog).props('title')).toBe('正在同步表 另一个表');
    });
  });

  describe('2. 事件(Emits)', () => {
    it('在同步完成前点击关闭按钮，应发出 `update:visible` 事件', async () => {
      wrapper = createComponent({ visible: true });
      // Simulate sync completion
      await flushPromises();

      // Find close button and click
      const closeButton = wrapper.findAllComponents(ElButton).find(b => b.text() === '关闭');
      await closeButton!.trigger('click');
      
      expect(wrapper.emitted('update:visible')).toBeTruthy();
      expect(wrapper.emitted('update:visible')![0]).toEqual([false]);
    });
    
    it('在同步完成后点击完成按钮，应发出 `complete` 和 `update:visible` 事件', async () => {
        wrapper = createComponent({ visible: true });
        await flushPromises();
        
        const confirmButton = wrapper.findComponent('[type="primary"]');
        await confirmButton.trigger('click');
        
        expect(wrapper.emitted('complete')).toBeTruthy();
        expect(wrapper.emitted('update:visible')).toBeTruthy();
        expect(wrapper.emitted('update:visible')![0]).toEqual([false]);
    });

    it('在同步进行中调用 `handleClose` 方法不应发出事件', async () => {
      wrapper = createComponent({ visible: true });
      // Sync is running, but not finished
      await new Promise(resolve => setTimeout(resolve, 10)); // let sync start
      
      wrapper.vm.handleClose(() => {});
      await wrapper.vm.$nextTick();
      
      expect(wrapper.emitted('update:visible')).toBeFalsy();
    });

    it('在同步进行中点击取消按钮，应发出 `cancel` 和 `update:visible` 事件', async () => {
        wrapper = createComponent({ visible: true });
        // Sync is running, let it start
        await new Promise(resolve => setTimeout(resolve, 10)); 
        
        const cancelButton = wrapper.findAllComponents(ElButton).find(b => b.text() === '取消同步');
        await cancelButton!.trigger('click');
        
        expect(wrapper.emitted('cancel')).toBeTruthy();
        expect(wrapper.emitted('update:visible')).toBeTruthy();
        expect(wrapper.emitted('update:visible')![0]).toEqual([false]);
    });
  });

  describe('3. 同步逻辑', () => {
    it('当 `visible` 变为 true 时，应自动开始同步', async () => {
      wrapper = createComponent({ visible: false, tableIds: ['id-123'] });
      await wrapper.setProps({ visible: true });
      await wrapper.vm.$nextTick();

      expect(mockDataPreparationStore.syncTables).toHaveBeenCalledWith(['id-123']);
    });
    
    it('如果 `tableIds` 为空，同步不应执行并显示错误', async () => {
        wrapper = createComponent({ visible: true, tableIds: [] });
        await flushPromises();
        
        expect(mockDataPreparationStore.syncTables).not.toHaveBeenCalled();
        expect(wrapper.vm.progressStatus).toBe('exception');
        expect(wrapper.vm.statusText).toContain('没有提供需要同步的表ID');
    });

    it('同步成功后，应更新进度条、状态文本和结果详情', async () => {
      (mockDataPreparationStore.syncTables as ReturnType<typeof vi.fn>).mockImplementation(async () => {
        // Simulate some delay
        await new Promise(r => setTimeout(r, 1000));
        return Promise.resolve();
      });

      wrapper = createComponent({ visible: true });
      await flushPromises();

      expect(wrapper.vm.progressPercentage).toBe(100);
      expect(wrapper.vm.progressStatus).toBe('success');
      expect(wrapper.vm.statusText).toBe('同步已成功完成！');
      expect(wrapper.find('.success-message').exists()).toBe(true);
      expect(wrapper.find('.result-details').text()).toContain('同步成功！');
    });

    it('同步失败后，应更新进度条、状态文本和错误信息', async () => {
      const error = new Error('数据库连接超时');
      (mockDataPreparationStore.syncTables as ReturnType<typeof vi.fn>).mockRejectedValue(error);
      
      wrapper = createComponent({ visible: true });
      await flushPromises();

      expect(wrapper.vm.progressPercentage).toBe(100);
      expect(wrapper.vm.progressStatus).toBe('exception');
      expect(wrapper.vm.statusText).toBe('同步失败: 数据库连接超时');
      expect(wrapper.find('.error-message').exists()).toBe(true);
      expect(wrapper.find('.result-details').text()).toContain('同步失败: 数据库连接超时');
    });
  });
  
  describe('4. 计算属性(Computed Properties)', () => {
    it('`progressStatus` 应根据同步结果返回正确状态', async () => {
      wrapper = createComponent({ visible: false });
      
      // Initial state
      expect(wrapper.vm.progressStatus).toBe('');
      
      // Success state
      wrapper.vm.syncResult = { success: true, startTime: 0, endTime: 0, duration: 0 };
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.progressStatus).toBe('success');
      
      // Failure state
      wrapper.vm.syncResult = { success: false, message: 'error', startTime: 0, endTime: 0, duration: 0 };
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.progressStatus).toBe('exception');
    });

    it('`statusText` 应根据同步状态返回正确的文本', async () => {
        wrapper = createComponent({ visible: false });
        
        // Initial state before sync starts
        wrapper.vm.syncing = false;
        wrapper.vm.syncResult = null;
        expect(wrapper.vm.statusText).toBe('准备开始同步...');

        // Syncing state
        wrapper.vm.syncing = true;
        wrapper.vm.progressPercentage = 50;
        expect(wrapper.vm.statusText).toBe('正在同步中... 50%');

        // Success state
        wrapper.vm.syncing = false;
        wrapper.vm.syncResult = { success: true, startTime: 0, endTime: 0, duration: 0 };
        expect(wrapper.vm.statusText).toBe('同步已成功完成！');

        // Failure state
        wrapper.vm.syncResult = { success: false, message: '测试错误', startTime: 0, endTime: 0, duration: 0 };
        expect(wrapper.vm.statusText).toBe('同步失败: 测试错误');
    });
  });
  
  describe('5. 辅助方法(Methods)', () => {
    beforeEach(() => {
        wrapper = createComponent();
    })
    
    it('`formatTime` 应能正确格式化时间戳', () => {
      const timestamp = new Date('2023-10-27 10:00:00').getTime();
      // localeString is timezone-dependent, so we check for parts
      const formatted = wrapper.vm.formatTime(timestamp);
      expect(formatted).toContain('2023');
      expect(formatted).toContain('10');
      expect(formatted).toContain('27');
    });
    
    it('`formatTime` 对无效时间戳应返回 N/A', () => {
      expect(wrapper.vm.formatTime(0)).toBe('N/A');
      expect(wrapper.vm.formatTime(null)).toBe('N/A');
    });
    
    it('`formatDuration` 应能正确格式化毫秒数', () => {
      expect(wrapper.vm.formatDuration(1234)).toBe('1.23 秒');
      expect(wrapper.vm.formatDuration(500)).toBe('0.50 秒');
      expect(wrapper.vm.formatDuration(0)).toBe('0.00 秒');
    });

    it('`formatDuration` 对负数应返回 N/A', () => {
      expect(wrapper.vm.formatDuration(-100)).toBe('N/A');
    });
  });

  describe('6. UI 状态', () => {
    it('同步时，“取消”按钮显示为“取消同步”且“完成”按钮被隐藏', async () => {
        wrapper = createComponent({ visible: true });
        // Let sync start
        await new Promise(resolve => setTimeout(resolve, 10));

        const cancelButton = wrapper.findAllComponents(ElButton).find(b => b.text() === '取消同步');
        const confirmButton = wrapper.find('[type="primary"]');
        
        expect(cancelButton.exists()).toBe(true);
        expect(cancelButton.props('disabled')).toBe(true); // as per component logic
        expect(confirmButton.exists()).toBe(false);
    });

    it('同步结束后，“取消”按钮显示为“关闭”且“完成”按钮可见', async () => {
        wrapper = createComponent({ visible: true });
        await flushPromises();

        const closeButton = wrapper.findAllComponents(ElButton).find(b => b.text() === '关闭');
        const confirmButton = wrapper.find('[type="primary"]');
        
        expect(closeButton.exists()).toBe(true);
        expect(closeButton.props('disabled')).toBe(false);
        expect(confirmButton.exists()).toBe(true);
    });
  });
});
