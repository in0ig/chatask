import { test, expect } from '@playwright/test';

test.describe('Data Source E2E Tests', () => {
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

  test('should add a MySQL data source', async ({ page }) => {
    // Click on Add Data Source button
    const addDataSourceButton = page.getByRole('button', { name: '添加数据源' });
    await addDataSourceButton.click();
    
    // Fill in MySQL data source form
    await page.getByLabel('数据源名称').fill('Test MySQL Source');
    await page.getByLabel('数据源类型').selectOption('mysql');
    await page.getByLabel('主机').fill('localhost');
    await page.getByLabel('端口').fill('3306');
    await page.getByLabel('数据库名').fill('chatbi_test');
    await page.getByLabel('用户名').fill('root');
    await page.getByLabel('密码').fill('password');
    
    // Submit the form
    const submitButton = page.getByRole('button', { name: '保存' });
    await submitButton.click();
    
    // Verify data source is added
    await expect(page.getByText('Test MySQL Source')).toBeVisible();
  });

  test('should test connection for a data source', async ({ page }) => {
    // First, add a data source
    const addDataSourceButton = page.getByRole('button', { name: '添加数据源' });
    await addDataSourceButton.click();
    
    await page.getByLabel('数据源名称').fill('Test Connection Source');
    await page.getByLabel('数据源类型').selectOption('mysql');
    await page.getByLabel('主机').fill('localhost');
    await page.getByLabel('端口').fill('3306');
    await page.getByLabel('数据库名').fill('chatbi_test');
    await page.getByLabel('用户名').fill('root');
    await page.getByLabel('密码').fill('password');
    
    // Click on Test Connection button
    const testConnectionButton = page.getByRole('button', { name: '测试连接' });
    await testConnectionButton.click();
    
    // Wait for connection result
    const connectionResult = page.getByText('连接成功');
    await expect(connectionResult).toBeVisible();
  });

  test('should edit an existing data source', async ({ page }) => {
    // First, add a data source
    const addDataSourceButton = page.getByRole('button', { name: '添加数据源' });
    await addDataSourceButton.click();
    
    await page.getByLabel('数据源名称').fill('Editable Source');
    await page.getByLabel('数据源类型').selectOption('mysql');
    await page.getByLabel('主机').fill('localhost');
    await page.getByLabel('端口').fill('3306');
    await page.getByLabel('数据库名').fill('chatbi_test');
    await page.getByLabel('用户名').fill('root');
    await page.getByLabel('密码').fill('password');
    
    const submitButton = page.getByRole('button', { name: '保存' });
    await submitButton.click();
    
    // Edit the data source
    const editButton = page.getByRole('button', { name: '编辑' }).first();
    await editButton.click();
    
    // Modify the data source name
    await page.getByLabel('数据源名称').fill('Edited Source');
    
    // Save changes
    await submitButton.click();
    
    // Verify changes were saved
    await expect(page.getByText('Edited Source')).toBeVisible();
  });

  test('should delete a data source with confirmation', async ({ page }) => {
    // First, add a data source
    const addDataSourceButton = page.getByRole('button', { name: '添加数据源' });
    await addDataSourceButton.click();
    
    await page.getByLabel('数据源名称').fill('Deletable Source');
    await page.getByLabel('数据源类型').selectOption('mysql');
    await page.getByLabel('主机').fill('localhost');
    await page.getByLabel('端口').fill('3306');
    await page.getByLabel('数据库名').fill('chatbi_test');
    await page.getByLabel('用户名').fill('root');
    await page.getByLabel('密码').fill('password');
    
    const submitButton = page.getByRole('button', { name: '保存' });
    await submitButton.click();
    
    // Delete the data source
    const deleteButton = page.getByRole('button', { name: '删除' }).first();
    await deleteButton.click();
    
    // Verify confirmation dialog appears
    const confirmDialog = page.getByText('确定要删除此数据源吗？');
    await expect(confirmDialog).toBeVisible();
    
    // Confirm deletion
    const confirmButton = page.getByRole('button', { name: '确定' });
    await confirmButton.click();
    
    // Verify data source is deleted
    await expect(page.getByText('Deletable Source')).not.toBeVisible();
  });

  test('should handle invalid connection', async ({ page }) => {
    // Add a data source with invalid credentials
    const addDataSourceButton = page.getByRole('button', { name: '添加数据源' });
    await addDataSourceButton.click();
    
    await page.getByLabel('数据源名称').fill('Invalid Connection Source');
    await page.getByLabel('数据源类型').selectOption('mysql');
    await page.getByLabel('主机').fill('invalid-host');
    await page.getByLabel('端口').fill('3306');
    await page.getByLabel('数据库名').fill('nonexistent_db');
    await page.getByLabel('用户名').fill('invalid_user');
    await page.getByLabel('密码').fill('invalid_password');
    
    // Test connection
    const testConnectionButton = page.getByRole('button', { name: '测试连接' });
    await testConnectionButton.click();
    
    // Verify connection failed message
    const connectionError = page.getByText('连接失败');
    await expect(connectionError).toBeVisible();
  });
});
