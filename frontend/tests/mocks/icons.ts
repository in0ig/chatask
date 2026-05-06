// Mock all Element Plus icons as simple SVG elements
// This prevents the "Failed to resolve component" errors in tests

const mockIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></svg>`

// Create a mock for each icon component
export const mockIcons = {
  ChartLine: () => mockIcon,
  Document: () => mockIcon,
  Setting: () => mockIcon,
  Language: () => mockIcon,
  Bell: () => mockIcon,
  // Add more icons as needed
}

// Register the mocks globally for all tests
export function registerIconMocks() {
  // This will be called in setupFiles
  Object.entries(mockIcons).forEach(([name, component]) => {
    // Register as a global component
    if (typeof window !== 'undefined') {
      window.customElements.define(name, class extends HTMLElement {
        connectedCallback() {
          this.innerHTML = component()
        }
      })
    }
  })
}