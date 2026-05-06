import { test, expect } from '@playwright/test';

test.describe('Data Table E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('http://localhost:3000');
    
    // Open the Config Drawer
    const configButton = page.getByRole('button', { name: '配置' });
    await configButton.click();
    
    // Navigate to Data Preparation tab
    const dataPrepTab = page.getByRole('tab', { name: '数据准备' });
    await dataPrepTab.click();
  });

  test('should add a new data table', async ({ page }) => {
    // Click on Add Data Table button
    const addDataTableButton = page.getByRole('button', { name: '添加数据表' });
    await addDataTableButton.click();
    
    // Select data source
    await page.getByLabel('选择数据源').selectOption('mysql');
    
    // Select table name
    await page.getByLabel('选择表名').selectOption('users');
    
    // Fill in table information
    await page.getByLabel('表名').fill('用户信息表');
    await page.getByLabel('表描述').fill('存储用户基本信息');
    
    // Submit the form
    const submitButton = page.getByRole('button', { name: '保存' });
    await submitButton.click();
    
    // Verify data table is added
    await expect(page.getByText('用户信息表')).toBeVisible();
  });

  test('should sync table structure', async ({ page }) => {
    // First, add a data table
    const addDataTableButton = page.getByRole('button', { name: '添加数据表' });
    await addDataTableButton.click();
    
    await page.getByLabel('选择数据源').selectOption('mysql');
    await page.getByLabel('选择表名').selectOption('users');
    await page.getByLabel('表名').fill('用户信息表');
    await page.getByLabel('表描述').fill('存储用户基本信息');
    
    const submitButton = page.getByRole('button', { name: '保存' });
    await submitButton.click();
    
    // Wait for table to be added
    await expect(page.getByText('用户信息表')).toBeVisible();
    
    // Click on '字段' button to view fields
    const viewFieldsButton = page.getByRole('button', { name: '字段' }).first();
    await viewFieldsButton.click();
    
    // Click on Sync button
    const syncButton = page.getByRole('button', { name: '同步结构' });
    await syncButton.click();
    
    // Verify sync success message
    const syncSuccess = page.getByText('表结构同步成功');
    await expect(syncSuccess).toBeVisible();
  });

  test('should configure table fields', async ({ page }) => {
    // First, add a data table
    const addDataTableButton = page.getByRole('button', { name: '添加数据表' });
    await addDataTableButton.click();
    
    await page.getByLabel('选择数据源').selectOption('mysql');
    await page.getByLabel('选择表名').selectOption('users');
    await page.getByLabel('表名').fill('用户信息表');
    await page.getByLabel('表描述').fill('存储用户基本信息');
    
    const submitButton = page.getByRole('button', { name: '保存' });
    await submitButton.click();
    
    // Wait for table to be added
    await expect(page.getByText('用户信息表')).toBeVisible();
    
    // Click on '字段' button to view fields
    const viewFieldsButton = page.getByRole('button', { name: '字段' }).first();
    await viewFieldsButton.click();
    
    // Edit field display name
    await page.getByPlaceholder('请输入显示名称').first().fill('用户名');
    
    // Edit field type
    await page.getByLabel('字段类型').first().selectOption('string');
    
    // Save field changes
    const saveFieldsButton = page.getByRole('button', { name: '保存字段' });
    await saveFieldsButton.click();
    
    // Verify changes were saved
    await expect(page.getByText('用户名')).toBeVisible();
  });

  test('should associate dictionary with field', async ({ page }) => {
    // First, add a data table
    const addDataTableButton = page.getByRole('button', { name: '添加数据表' });
    await addDataTableButton.click();
    
    await page.getByLabel('选择数据源').selectOption('mysql');
    await page.getByLabel('选择表名').selectOption('users');
    await page.getByLabel('表名').fill('用户信息表');
    await page.getByLabel('表描述').fill('存储用户基本信息');
    
    const submitButton = page.getByRole('button', { name: '保存' });
    await submitButton.click();
    
    // Wait for table to be added
    await expect(page.getByText('用户信息表')).toBeVisible();
    
    // Click on '字段' button to view fields
    const viewFieldsButton = page.getByRole('button', { name: '字段' }).first();
    await viewFieldsButton.click();
    
    // Click on dictionary association button for first field
    const assocDictButton = page.getByRole('button', { name: '关联字典' }).first();
    await assocDictButton.click();
    
    // Select dictionary
    await page.getByLabel('选择字典').selectOption('gender');
    
    // Save association
    const saveDictButton = page.getByRole('button', { name: '保存' });
    await saveDictButton.click();
    
    // Verify dictionary association
    await expect(page.getByText('性别字典')).toBeVisible();
  });

  test('should handle invalid data source selection', async ({ page }) => {
    // Click on Add Data Table button
    const addDataTableButton = page.getByRole('button', { name: '添加数据表' });
    await addDataTableButton.click();
    
    // Select non-existent data source
    await page.getByLabel('选择数据源').selectOption('nonexistent');
    
    // Try to select table name
    const tableSelect = page.getByLabel('选择表名');
    await expect(tableSelect).toHaveAttribute('disabled');
    
    // Verify error message
    const errorMessage = page.getByText('请先选择有效的数据源');
    await expect(errorMessage).toBeVisible();
  });

  test('should handle empty table name', async ({ page }) => {
    // Click on Add Data Table button
    const addDataTableButton = page.getByRole('button', { name: '添加数据表' });
    await addDataTableButton.click();
    
    // Select data source
    await page.getByLabel('选择数据源').selectOption('mysql');
    
    // Leave table name empty
    await page.getByLabel('表名').clear();
    
    // Try to save
    const submitButton = page.getByRole('button', { name: '保存' });
    await submitButton.click();
    
    // Verify validation error
    const validationError = page.getByText('表名不能为空');
    await expect(validationError).toBeVisible();
  });
});
