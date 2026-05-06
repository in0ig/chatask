#!/usr/bin/env python3
"""
集成测试脚本 - 测试完整部署流程和错误场景

此脚本测试以下场景：
1. 虚拟环境检查（正常情况）
2. 端口占用处理（模拟端口被占用）
3. 数据库初始化（验证数据库创建）
4. 数据库连接（验证连接成功）
5. 依赖检查（验证依赖安装）
6. 启动脚本执行（验证完整启动流程）

所有测试用例必须通过，验证错误提示的清晰度和日志文件的内容。
"""

import os
import sys
import subprocess
import time
import shutil
import tempfile
import logging
from pathlib import Path
import unittest
from typing import Dict, List, Optional

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path("/Users/zhanh391/PC/ChatBI")
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATABASE_INIT_SQL = PROJECT_ROOT / "database" / "init.sql"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
BACKEND_LOG = PROJECT_ROOT / "backend.log"
FRONTEND_LOG = PROJECT_ROOT / "frontend.log"

# 测试环境目录（用于隔离测试）
TEST_ENV_DIR = None


class IntegrationTest(unittest.TestCase):
    """集成测试类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 创建临时测试目录
        cls.test_env_dir = tempfile.mkdtemp(prefix="chatbi_integration_test_")
        cls.test_env_dir = Path(cls.test_env_dir)
        
        # 复制项目结构到测试环境
        cls.copy_project_structure()
        
        # 设置环境变量
        os.environ["DB_HOST"] = "127.0.0.1"
        os.environ["DB_PORT"] = "3306"
        os.environ["DB_USER"] = "root"
        os.environ["DB_PASSWORD"] = "12345678"
        os.environ["DB_NAME"] = "chatbi"
        os.environ["DB_POOL_SIZE"] = "5"
        
        # 确保 MySQL 服务正在运行
        cls.ensure_mysql_running()
        
        # 创建测试数据库
        cls.create_test_database()
        
        # 创建测试用户
        cls.create_test_user()
        
        # 确保后端依赖已安装
        cls.install_backend_deps()
        
        # 确保前端依赖已安装
        cls.install_frontend_deps()
        
        # 清理旧的日志文件
        cls.cleanup_logs()
        
        logger.info(f"测试环境准备完成: {cls.test_env_dir}")
    
    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        # 停止任何正在运行的进程
        cls.kill_all_processes()
        
        # 删除临时测试目录
        if cls.test_env_dir and cls.test_env_dir.exists():
            shutil.rmtree(cls.test_env_dir)
            logger.info(f"已删除测试环境: {cls.test_env_dir}")
    
    @classmethod
    def copy_project_structure(cls):
        """复制项目结构到测试环境"""
        # 创建测试环境目录结构
        test_backend = cls.test_env_dir / "backend"
        test_frontend = cls.test_env_dir / "frontend"
        test_database = cls.test_env_dir / "database"
        test_scripts = cls.test_env_dir / "scripts"
        
        # 创建目录
        test_backend.mkdir(parents=True)
        test_frontend.mkdir(parents=True)
        test_database.mkdir()
        test_scripts.mkdir()
        
        # 复制后端文件
        for item in BACKEND_DIR.iterdir():
            if item.is_file():
                shutil.copy2(item, test_backend / item.name)
            elif item.is_dir() and item.name != ".venv":  # 不复制虚拟环境
                shutil.copytree(item, test_backend / item.name, dirs_exist_ok=True)
        
        # 复制前端文件
        for item in FRONTEND_DIR.iterdir():
            if item.is_file():
                shutil.copy2(item, test_frontend / item.name)
            elif item.is_dir() and item.name != "node_modules":  # 不复制 node_modules
                shutil.copytree(item, test_frontend / item.name, dirs_exist_ok=True)
        
        # 复制数据库初始化脚本
        shutil.copy2(DATABASE_INIT_SQL, test_database / "init.sql")
        
        # 复制启动/停止脚本
        for item in SCRIPTS_DIR.iterdir():
            if item.is_file():
                shutil.copy2(item, test_scripts / item.name)
        
        # 创建空的 .env 文件
        (test_backend / ".env").touch()
        
        # 创建空的 package.json 文件（如果不存在）
        if not (test_frontend / "package.json").exists():
            (test_frontend / "package.json").write_text("{\"name\": \"chatbi-frontend\", \"version\": \"1.0.0\"}")
    
    @classmethod
    def ensure_mysql_running(cls):
        """确保 MySQL 服务正在运行"""
        try:
            result = subprocess.run(["brew", "services", "list"], 
                                  capture_output=True, text=True)
            if "mysql" in result.stdout and "started" not in result.stdout:
                # MySQL 服务未运行，尝试启动
                subprocess.run(["brew", "services", "start", "mysql"], 
                              check=True, capture_output=True)
                time.sleep(5)  # 等待 MySQL 启动
                logger.info("MySQL 服务已启动")
        except Exception as e:
            logger.warning(f"无法确认 MySQL 服务状态: {e}")
    
    @classmethod
    def create_test_database(cls):
        """创建测试数据库"""
        try:
            # 使用 mysql 命令执行初始化脚本
            subprocess.run([
                "mysql", 
                "-u", "root", 
                "-p12345678", 
                "<", str(DATABASE_INIT_SQL)
            ], shell=True, check=True, capture_output=True)
            logger.info("测试数据库已初始化")
        except subprocess.CalledProcessError as e:
            logger.error(f"数据库初始化失败: {e.stderr.decode()}")
            raise
    
    @classmethod
    def create_test_user(cls):
        """创建测试用户（如果需要）"""
        # MySQL root 用户通常已存在
        pass
    
    @classmethod
    def install_backend_deps(cls):
        """安装后端依赖"""
        try:
            # 在测试环境的后端目录中安装依赖
            subprocess.run([
                "pip", "install", "-e", "."
            ], cwd=cls.test_env_dir / "backend", 
            check=True, capture_output=True)
            logger.info("后端依赖已安装")
        except subprocess.CalledProcessError as e:
            logger.error(f"后端依赖安装失败: {e.stderr.decode()}")
            raise
    
    @classmethod
    def install_frontend_deps(cls):
        """安装前端依赖"""
        try:
            # 在测试环境的前端目录中安装依赖
            subprocess.run([
                "npm", "install"
            ], cwd=cls.test_env_dir / "frontend", 
            check=True, capture_output=True)
            logger.info("前端依赖已安装")
        except subprocess.CalledProcessError as e:
            logger.error(f"前端依赖安装失败: {e.stderr.decode()}")
            raise
    
    @classmethod
    def cleanup_logs(cls):
        """清理旧的日志文件"""
        for log_file in [BACKEND_LOG, FRONTEND_LOG]:
            if log_file.exists():
                log_file.unlink()
    
    @classmethod
    def kill_all_processes(cls):
        """杀死所有可能运行的进程"""
        try:
            # 杀死可能运行的后端进程
            subprocess.run(["pkill", "-f", "uvicorn"], 
                          capture_output=True)
            # 杀死可能运行的前端进程
            subprocess.run(["pkill", "-f", "vite"], 
                          capture_output=True)
            # 杀死可能运行的 npm 进程
            subprocess.run(["pkill", "-f", "npm"], 
                          capture_output=True)
        except Exception as e:
            logger.warning(f"杀死进程时出错: {e}")
    
    def test_01_virtual_environment_check_normal(self):
        """测试1: 虚拟环境检查（正常情况）"""
        # 确保虚拟环境存在
        venv_path = self.test_env_dir / "backend" / ".venv"
        venv_path.mkdir(exist_ok=True)
        
        # 创建激活脚本
        bin_dir = venv_path / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "python").touch()
        (bin_dir / "pip").touch()
        
        # 执行启动脚本
        result = subprocess.run([
            "bash", "start.sh"
        ], cwd=self.test_env_dir / "scripts", 
        capture_output=True, text=True)
        
        # 验证输出
        self.assertEqual(result.returncode, 0, "启动脚本应成功执行")
        self.assertIn("虚拟环境已找到", result.stdout, "应包含虚拟环境找到的消息")
        self.assertIn("后端服务已启动", result.stdout, "应包含后端服务启动的消息")
        self.assertIn("前端服务已启动", result.stdout, "应包含前端服务启动的消息")
        
        # 验证日志文件
        self.assertTrue((self.test_env_dir / "backend.log").exists(), "后端日志文件应存在")
        self.assertTrue((self.test_env_dir / "frontend.log").exists(), "前端日志文件应存在")
        
        logger.info("测试1: 虚拟环境检查（正常情况）通过")
    
    def test_02_port_conflict_handling(self):
        """测试2: 端口占用处理（模拟端口被占用）"""
        # 创建一个模拟进程占用端口 8000
        # 使用 netcat 创建一个监听进程
        import threading
        
        def create_port_listener():
            try:
                # 使用 netcat 监听端口 8000
                subprocess.run([
                    "nc", "-l", "-p", "8000", "-q", "1"
                ], cwd=self.test_env_dir / "scripts", 
                capture_output=True)
            except Exception:
                pass
        
        # 启动监听进程
        listener_thread = threading.Thread(target=create_port_listener)
        listener_thread.daemon = True
        listener_thread.start()
        
        # 等待端口被占用
        time.sleep(1)
        
        # 执行启动脚本
        result = subprocess.run([
            "bash", "start.sh"
        ], cwd=self.test_env_dir / "scripts", 
        capture_output=True, text=True)
        
        # 验证输出
        self.assertEqual(result.returncode, 0, "启动脚本应成功执行（即使端口被占用）")
        self.assertIn("警告：端口 8000 被进程", result.stdout, "应包含端口被占用的警告")
        self.assertIn("成功终止占用端口 8000 的进程", result.stdout, "应包含成功终止进程的消息")
        self.assertIn("后端服务已启动", result.stdout, "应包含后端服务启动的消息")
        
        # 验证日志文件
        self.assertTrue((self.test_env_dir / "backend.log").exists(), "后端日志文件应存在")
        
        logger.info("测试2: 端口占用处理通过")
    
    def test_03_database_initialization(self):
        """测试3: 数据库初始化（验证数据库创建）"""
        # 删除数据库以模拟未初始化状态
        try:
            subprocess.run([
                "mysql", "-u", "root", "-p12345678", "-e", "DROP DATABASE IF EXISTS chatbi"
            ], check=True, capture_output=True)
            logger.info("测试数据库已删除")
        except subprocess.CalledProcessError as e:
            logger.warning(f"删除数据库时出错: {e.stderr.decode()}")
        
        # 确保数据库文件存在
        self.assertTrue((self.test_env_dir / "database" / "init.sql").exists(), "数据库初始化脚本应存在")
        
        # 执行启动脚本
        result = subprocess.run([
            "bash", "start.sh"
        ], cwd=self.test_env_dir / "scripts", 
        capture_output=True, text=True)
        
        # 验证输出
        self.assertEqual(result.returncode, 0, "启动脚本应成功执行")
        self.assertIn("数据库连接成功！", result.stdout, "应包含数据库连接成功的消息")
        
        # 验证数据库是否被重新创建
        result = subprocess.run([
            "mysql", "-u", "root", "-p12345678", "-e", "SHOW DATABASES LIKE 'chatbi'"
        ], capture_output=True, text=True)
        self.assertIn("chatbi", result.stdout, "数据库 chatbi 应被重新创建")
        
        # 验证日志文件
        self.assertTrue((self.test_env_dir / "backend.log").exists(), "后端日志文件应存在")
        
        logger.info("测试3: 数据库初始化通过")
    
    def test_04_database_connection(self):
        """测试4: 数据库连接（验证连接成功）"""
        # 确保数据库存在
        try:
            subprocess.run([
                "mysql", "-u", "root", "-p12345678", "-e", "CREATE DATABASE IF NOT EXISTS chatbi"
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"创建数据库时出错: {e.stderr.decode()}")
            raise
        
        # 模拟数据库连接失败（通过修改配置）
        env_file = self.test_env_dir / "backend" / ".env"
        original_env_content = ""
        if env_file.exists():
            original_env_content = env_file.read_text()
        
        # 修改数据库主机为无效值
        env_file.write_text("DB_HOST=invalid-host\nDB_PORT=3306\nDB_USER=root\nDB_PASSWORD=12345678\nDB_NAME=chatbi\nDB_POOL_SIZE=5")
        
        # 执行启动脚本
        result = subprocess.run([
            "bash", "start.sh"
        ], cwd=self.test_env_dir / "scripts", 
        capture_output=True, text=True)
        
        # 验证输出
        self.assertNotEqual(result.returncode, 0, "启动脚本应失败（数据库连接失败）")
        self.assertIn("错误：无法连接到 MySQL 数据库！", result.stdout, "应包含数据库连接失败的错误消息")
        self.assertIn("请确保 MySQL 服务正在运行，并且数据库已初始化。", result.stdout, "应包含数据库初始化提示")
        
        # 验证日志文件
        self.assertTrue((self.test_env_dir / "backend.log").exists(), "后端日志文件应存在")
        
        # 恢复原始环境文件
        env_file.write_text(original_env_content)
        
        logger.info("测试4: 数据库连接通过")
    
    def test_05_dependency_check(self):
        """测试5: 依赖检查（验证依赖安装）"""
        # 删除后端依赖
        venv_path = self.test_env_dir / "backend" / ".venv"
        if venv_path.exists():
            shutil.rmtree(venv_path)
        
        # 确保没有依赖
        # 执行启动脚本
        result = subprocess.run([
            "bash", "start.sh"
        ], cwd=self.test_env_dir / "scripts", 
        capture_output=True, text=True)
        
        # 验证输出
        self.assertEqual(result.returncode, 0, "启动脚本应成功执行")
        self.assertIn("警告：以下依赖缺失：uvicorn", result.stdout, "应包含依赖缺失的警告")
        self.assertIn("请运行以下命令安装缺失的依赖：", result.stdout, "应包含安装依赖的提示")
        
        # 验证日志文件
        self.assertTrue((self.test_env_dir / "backend.log").exists(), "后端日志文件应存在")
        
        logger.info("测试5: 依赖检查通过")
    
    def test_06_start_script_execution(self):
        """测试6: 启动脚本执行（验证完整启动流程）"""
        # 确保所有条件都满足
        venv_path = self.test_env_dir / "backend" / ".venv"
        venv_path.mkdir(exist_ok=True)
        bin_dir = venv_path / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "python").touch()
        (bin_dir / "pip").touch()
        
        # 创建必要的依赖文件
        (self.test_env_dir / "backend" / "pyproject.toml").touch()
        
        # 确保数据库存在
        try:
            subprocess.run([
                "mysql", "-u", "root", "-p12345678", "-e", "CREATE DATABASE IF NOT EXISTS chatbi"
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"创建数据库时出错: {e.stderr.decode()}")
            raise
        
        # 确保前端依赖存在
        (self.test_env_dir / "frontend" / "node_modules").mkdir(exist_ok=True)
        
        # 执行启动脚本
        result = subprocess.run([
            "bash", "start.sh"
        ], cwd=self.test_env_dir / "scripts", 
        capture_output=True, text=True)
        
        # 验证输出
        self.assertEqual(result.returncode, 0, "启动脚本应成功执行")
        self.assertIn("虚拟环境已找到", result.stdout, "应包含虚拟环境找到的消息")
        self.assertIn("后端服务已启动", result.stdout, "应包含后端服务启动的消息")
        self.assertIn("前端服务已启动", result.stdout, "应包含前端服务启动的消息")
        self.assertIn("ChatBI 应用程序启动成功！", result.stdout, "应包含成功启动的消息")
        
        # 验证日志文件
        self.assertTrue((self.test_env_dir / "backend.log").exists(), "后端日志文件应存在")
        self.assertTrue((self.test_env_dir / "frontend.log").exists(), "前端日志文件应存在")
        
        # 验证日志文件内容
        backend_log_content = (self.test_env_dir / "backend.log").read_text()
        frontend_log_content = (self.test_env_dir / "frontend.log").read_text()
        
        # 验证后端日志包含关键信息
        self.assertIn("INFO", backend_log_content, "后端日志应包含 INFO 级别日志")
        self.assertIn("uvicorn", backend_log_content, "后端日志应包含 uvicorn 相关信息")
        
        # 验证前端日志包含关键信息
        self.assertIn("VITE", frontend_log_content, "前端日志应包含 VITE 相关信息")
        self.assertIn("ready", frontend_log_content, "前端日志应包含 ready 信息")
        
        logger.info("测试6: 启动脚本执行通过")


if __name__ == "__main__":
    # 设置测试环境
    unittest.main()
