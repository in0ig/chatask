import { describe, it, expect } from 'vitest'

// Create a simple HTML element
const createTestElement = () => {
  const div = document.createElement('div')
  div.innerHTML = '<p>Hello World</p>'
  return div
}

describe('Basic HTML test', () => {
  it('should create and render a simple HTML element', () => {
    const element = createTestElement()
    
    // Check if the element was created correctly
    expect(element.innerHTML).toContain('Hello World')
    
    // Check if the element has the correct structure
    expect(element.querySelector('p')).toBeTruthy()
    expect(element.querySelector('p')?.textContent).toBe('Hello World')
  })
})