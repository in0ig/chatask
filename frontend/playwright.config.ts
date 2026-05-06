import { defineConfig } from '@playwright/test';
import { resolve } from 'path';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// require('dotenv').config();

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Configure which files to include in test discovery */
  testMatch: ['**/*.{test,spec}.mts'],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:5173',
    
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    
    /* Wait for the app to be ready before running tests */
    waitForLoadState: 'networkidle',
    
    /* Screenshot options */
    screenshot: 'only-on-failure',
    
    /* Video options */
    video: 'retain-on-failure',
    
    /* Use Chromium browser by default */
    browserName: 'chromium',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...defineConfig.use,
        browserName: 'chromium',
      },
    },
    
    {
      name: 'firefox',
      use: {
        ...defineConfig.use,
        browserName: 'firefox',
      },
    },
    
    {
      name: 'webkit',
      use: {
        ...defineConfig.use,
        browserName: 'webkit',
      },
    },
  ],

  /* Folder for test artifacts such as screenshots, videos, traces, etc. */
  outputDir: 'test-results/',

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },

  /* Configure TypeScript path aliases for Playwright */
  // This ensures that @/store paths are resolved correctly during testing
  // We need to use tsconfig.json for path resolution
  // Playwright will automatically use tsconfig.json for path resolution
});