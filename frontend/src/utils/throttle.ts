/**
 * 节流函数 - 限制函数执行频率
 * 适用于滚动、窗口大小改变等场景，确保函数在指定时间间隔内只执行一次
 * 
 * @param fn - 需要节流的函数
 * @param interval - 时间间隔（毫秒）
 * @returns 节流后的函数
 */
export function throttle<T extends (...args: any[]) => any>(fn: T, interval: number): T {
  let lastExecTime = 0;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  
  return ((...args: Parameters<T>) => {
    const now = Date.now();
    
    // 如果距离上次执行已经超过时间间隔，则直接执行
    if (now - lastExecTime >= interval) {
      lastExecTime = now;
      fn(...args);
    } else {
      // 否则，设置定时器在下个时间间隔执行
      if (!timeoutId) {
        timeoutId = setTimeout(() => {
          lastExecTime = Date.now();
          timeoutId = null;
          fn(...args);
        }, interval - (now - lastExecTime));
      }
    }
  }) as T;
}