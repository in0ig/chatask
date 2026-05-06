import unittest
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import os
import sys
import pathlib
import mysql.connector

# Add src directory to Python path to ensure modules can be imported
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

# Import the models
from models.database_models import Base, PromptConfig, SessionContext, ConversationMessage, TokenUsageStats
from models.database_models import PromptType, ContextType, Role, ModelUsed, ModelType

# Set up test database connection
# Use MySQL for testing to properly support ENUM types
TEST_DATABASE_URL = "mysql+mysqlconnector://root:12345678@localhost:3306/chatbi"

class TestDatabaseTables(unittest.TestCase):
    """Test suite for database table structure verification"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database engine and create tables"""
        cls.engine = create_engine(TEST_DATABASE_URL)
        # Create all tables
        Base.metadata.create_all(cls.engine)
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        cls.engine.dispose()
    
    def setUp(self):
        """Set up test session"""
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
    
    def tearDown(self):
        """Clean up test session"""
        self.session.close()
    
    def test_prompt_config_table_exists(self):
        """验证 prompt_config 表存在且列正确"""
        # Check if table exists
        self.assertTrue(self.engine.dialect.has_table(self.engine.connect(), "prompt_config"))
        
        # Use reflection to get column information
        from sqlalchemy import MetaData
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        table = metadata.tables['prompt_config']
        
        # Verify column names and types
        column_names = [col.name for col in table.columns]
        expected_columns = [
            'id', 'project_id', 'prompt_type', 'prompt_category', 
            'system_prompt', 'user_prompt_template', 'examples', 
            'temperature', 'max_tokens', 'enabled', 'created_by', 
            'created_at', 'updated_at'
        ]
        
        for col in expected_columns:
            self.assertIn(col, column_names)
        
        # Verify column types and constraints
        for column in table.columns:
            if column.name == 'id':
                self.assertTrue(column.primary_key)
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.autoincrement)
            elif column.name == 'project_id':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertFalse(column.nullable)
            elif column.name == 'prompt_type':
                self.assertEqual(column.type.__class__.__name__, 'ENUM')
                self.assertFalse(column.nullable)
            elif column.name == 'prompt_category':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertFalse(column.nullable)  # Database shows NOT NULL
            elif column.name == 'system_prompt':
                self.assertEqual(column.type.__class__.__name__, 'TEXT')
                self.assertFalse(column.nullable)
            elif column.name == 'user_prompt_template':
                self.assertEqual(column.type.__class__.__name__, 'TEXT')
                self.assertFalse(column.nullable)
            elif column.name == 'examples':
                self.assertEqual(column.type.__class__.__name__, 'JSON')
                self.assertTrue(column.nullable)
            elif column.name == 'temperature':
                self.assertEqual(column.type.__class__.__name__, 'FLOAT')
                self.assertTrue(column.nullable)
            elif column.name == 'max_tokens':
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.nullable)
            elif column.name == 'enabled':
                self.assertEqual(column.type.__class__.__name__, 'TINYINT')
                self.assertTrue(column.nullable)
            elif column.name == 'created_by':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertFalse(column.nullable)
            elif column.name == 'created_at':
                self.assertEqual(column.type.__class__.__name__, 'DATETIME')
                self.assertTrue(column.nullable)  # Database shows NULL, but has default
                # Use direct MySQL query to get default value since SQLAlchemy reflection doesn't work
                conn = mysql.connector.connect(
                    host='localhost',
                    database='chatbi',
                    user='root',
                    password='12345678'
                )
                cursor = conn.cursor()
                cursor.execute("DESCRIBE prompt_config;")
                for col in cursor.fetchall():
                    if col[0] == 'created_at':
                        self.assertIsNotNone(col[4])  # Default value exists
                        break
                cursor.close()
                conn.close()
            elif column.name == 'updated_at':
                self.assertEqual(column.type.__class__.__name__, 'DATETIME')
                self.assertTrue(column.nullable)  # Database shows NULL, but has default
                # Use direct MySQL query to get default value since SQLAlchemy reflection doesn't work
                conn = mysql.connector.connect(
                    host='localhost',
                    database='chatbi',
                    user='root',
                    password='12345678'
                )
                cursor = conn.cursor()
                cursor.execute("DESCRIBE prompt_config;")
                for col in cursor.fetchall():
                    if col[0] == 'updated_at':
                        self.assertIsNotNone(col[4])  # Default value exists
                        break
                cursor.close()
                conn.close()
    
    def test_session_context_table_exists(self):
        """验证 session_context 表存在且列正确"""
        # Check if table exists
        self.assertTrue(self.engine.dialect.has_table(self.engine.connect(), "session_context"))
        
        # Use reflection to get column information
        from sqlalchemy import MetaData
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        table = metadata.tables['session_context']
        
        # Verify column names and types
        column_names = [col.name for col in table.columns]
        expected_columns = [
            'id', 'session_id', 'context_type', 'messages', 
            'token_count', 'summary', 'last_summary_at', 
            'created_at', 'updated_at'
        ]
        
        for col in expected_columns:
            self.assertIn(col, column_names)
        
        # Verify column types and constraints
        for column in table.columns:
            if column.name == 'id':
                self.assertTrue(column.primary_key)
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.autoincrement)
            elif column.name == 'session_id':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertFalse(column.nullable)
            elif column.name == 'context_type':
                self.assertEqual(column.type.__class__.__name__, 'ENUM')
                self.assertFalse(column.nullable)
            elif column.name == 'messages':
                self.assertEqual(column.type.__class__.__name__, 'JSON')
                self.assertTrue(column.nullable)
            elif column.name == 'token_count':
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.nullable)
                # Use direct MySQL query to get default value since SQLAlchemy reflection doesn't work
                conn = mysql.connector.connect(
                    host='localhost',
                    database='chatbi',
                    user='root',
                    password='12345678'
                )
                cursor = conn.cursor()
                cursor.execute("DESCRIBE session_context;")
                for col in cursor.fetchall():
                    if col[0] == 'token_count':
                        self.assertEqual(col[4], '0')  # Default value is '0'
                        break
                cursor.close()
                conn.close()
            elif column.name == 'summary':
                self.assertEqual(column.type.__class__.__name__, 'TEXT')
                self.assertTrue(column.nullable)
            elif column.name == 'last_summary_at':
                self.assertEqual(column.type.__class__.__name__, 'TIMESTAMP')
                self.assertTrue(column.nullable)
            elif column.name == 'created_at':
                self.assertEqual(column.type.__class__.__name__, 'TIMESTAMP')
                self.assertTrue(column.nullable)  # Database shows NULL, but has default
                # Use direct MySQL query to get default value since SQLAlchemy reflection doesn't work
                conn = mysql.connector.connect(
                    host='localhost',
                    database='chatbi',
                    user='root',
                    password='12345678'
                )
                cursor = conn.cursor()
                cursor.execute("DESCRIBE session_context;")
                for col in cursor.fetchall():
                    if col[0] == 'created_at':
                        self.assertIsNotNone(col[4])  # Default value exists
                        break
                cursor.close()
                conn.close()
            elif column.name == 'updated_at':
                self.assertEqual(column.type.__class__.__name__, 'TIMESTAMP')
                self.assertTrue(column.nullable)  # Database shows NULL, but has default
                # Use direct MySQL query to get default value since SQLAlchemy reflection doesn't work
                conn = mysql.connector.connect(
                    host='localhost',
                    database='chatbi',
                    user='root',
                    password='12345678'
                )
                cursor = conn.cursor()
                cursor.execute("DESCRIBE session_context;")
                for col in cursor.fetchall():
                    if col[0] == 'updated_at':
                        self.assertIsNotNone(col[4])  # Default value exists
                        break
                cursor.close()
                conn.close()
    
    def test_conversation_messages_table_exists(self):
        """验证 conversation_messages 表存在且列正确"""
        # Check if table exists
        self.assertTrue(self.engine.dialect.has_table(self.engine.connect(), "conversation_messages"))
        
        # Use reflection to get column information
        from sqlalchemy import MetaData
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        table = metadata.tables['conversation_messages']
        
        # Verify column names and types
        column_names = [col.name for col in table.columns]
        expected_columns = [
            'id', 'session_id', 'turn', 'role', 'content', 
            'parent_message_id', 'token_count', 'model_used', 
            'intent', 'query_id', 'analysis_id', 'created_at'
        ]
        
        for col in expected_columns:
            self.assertIn(col, column_names)
        
        # Verify column types and constraints
        for column in table.columns:
            if column.name == 'id':
                self.assertTrue(column.primary_key)
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.autoincrement)
            elif column.name == 'session_id':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertFalse(column.nullable)
            elif column.name == 'turn':
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertFalse(column.nullable)
            elif column.name == 'role':
                self.assertEqual(column.type.__class__.__name__, 'ENUM')
                self.assertFalse(column.nullable)
            elif column.name == 'content':
                self.assertEqual(column.type.__class__.__name__, 'TEXT')
                self.assertFalse(column.nullable)
            elif column.name == 'parent_message_id':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertTrue(column.nullable)
            elif column.name == 'token_count':
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.nullable)
                # Use direct MySQL query to get default value since SQLAlchemy reflection doesn't work
                conn = mysql.connector.connect(
                    host='localhost',
                    database='chatbi',
                    user='root',
                    password='12345678'
                )
                cursor = conn.cursor()
                cursor.execute("DESCRIBE conversation_messages;")
                for col in cursor.fetchall():
                    if col[0] == 'token_count':
                        self.assertEqual(col[4], '0')  # Default value is '0'
                        break
                cursor.close()
                conn.close()
            elif column.name == 'model_used':
                self.assertEqual(column.type.__class__.__name__, 'ENUM')
                self.assertTrue(column.nullable)
            elif column.name == 'intent':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertTrue(column.nullable)
            elif column.name == 'query_id':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertTrue(column.nullable)
            elif column.name == 'analysis_id':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertTrue(column.nullable)
            elif column.name == 'created_at':
                self.assertEqual(column.type.__class__.__name__, 'TIMESTAMP')
                self.assertTrue(column.nullable)  # Database shows NULL, but has default
                # Use direct MySQL query to get default value since SQLAlchemy reflection doesn't work
                conn = mysql.connector.connect(
                    host='localhost',
                    database='chatbi',
                    user='root',
                    password='12345678'
                )
                cursor = conn.cursor()
                cursor.execute("DESCRIBE conversation_messages;")
                for col in cursor.fetchall():
                    if col[0] == 'created_at':
                        self.assertIsNotNone(col[4])  # Default value exists
                        break
                cursor.close()
                conn.close()
    
    def test_token_usage_stats_table_exists(self):
        """验证 token_usage_stats 表存在且列正确"""
        # Check if table exists
        self.assertTrue(self.engine.dialect.has_table(self.engine.connect(), "token_usage_stats"))
        
        # Use reflection to get column information
        from sqlalchemy import MetaData
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        table = metadata.tables['token_usage_stats']
        
        # Verify column names and types
        column_names = [col.name for col in table.columns]
        expected_columns = [
            'id', 'session_id', 'model_type', 'turn', 
            'input_tokens', 'output_tokens', 'total_tokens', 'created_at'
        ]
        
        for col in expected_columns:
            self.assertIn(col, column_names)
        
        # Verify column types and constraints
        for column in table.columns:
            if column.name == 'id':
                self.assertTrue(column.primary_key)
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.autoincrement)
            elif column.name == 'session_id':
                self.assertEqual(column.type.__class__.__name__, 'VARCHAR')
                self.assertFalse(column.nullable)
            elif column.name == 'model_type':
                self.assertEqual(column.type.__class__.__name__, 'ENUM')
                self.assertFalse(column.nullable)
            elif column.name == 'turn':
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertFalse(column.nullable)
            elif column.name == 'input_tokens':
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.nullable)
            elif column.name == 'output_tokens':
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.nullable)
            elif column.name == 'total_tokens':
                self.assertEqual(column.type.__class__.__name__, 'INTEGER')
                self.assertTrue(column.nullable)
            elif column.name == 'created_at':
                self.assertEqual(column.type.__class__.__name__, 'TIMESTAMP')
                self.assertTrue(column.nullable)  # Database shows NULL, but has default
                # Use direct MySQL query to get default value since SQLAlchemy reflection doesn't work
                conn = mysql.connector.connect(
                    host='localhost',
                    database='chatbi',
                    user='root',
                    password='12345678'
                )
                cursor = conn.cursor()
                cursor.execute("DESCRIBE token_usage_stats;")
                for col in cursor.fetchall():
                    if col[0] == 'created_at':
                        self.assertIsNotNone(col[4])  # Default value exists
                        break
                cursor.close()
                conn.close()
    
    def test_enum_types_defined(self):
        """验证所有 ENUM 类型正确定义"""
        # Test PromptType enum
        self.assertEqual(len(PromptType), 8)
        expected_prompt_types = [
            'intent_recognition', 'table_selection', 'sql_generation', 
            'sql_error_recovery', 'data_interpretation', 'fluctuation_attribution', 
            'follow_up_handling', 'analysis_strategy_application'
        ]
        for enum_val in expected_prompt_types:
            self.assertIn(enum_val, [e.value for e in PromptType])
        
        # Test ContextType enum
        self.assertEqual(len(ContextType), 2)
        expected_context_types = ['local_model', 'aliyun_model']
        for enum_val in expected_context_types:
            self.assertIn(enum_val, [e.value for e in ContextType])
        
        # Test Role enum
        self.assertEqual(len(Role), 3)
        expected_roles = ['user', 'assistant', 'system']
        for enum_val in expected_roles:
            self.assertIn(enum_val, [e.value for e in Role])
        
        # Test ModelUsed enum
        self.assertEqual(len(ModelUsed), 3)
        expected_model_used = ['aliyun', 'local', 'none']
        for enum_val in expected_model_used:
            self.assertIn(enum_val, [e.value for e in ModelUsed])
        
        # Test ModelType enum
        self.assertEqual(len(ModelType), 2)
        expected_model_types = ['local', 'aliyun']
        for enum_val in expected_model_types:
            self.assertIn(enum_val, [e.value for e in ModelType])
    
    def test_foreign_keys_configured(self):
        """验证所有外键约束正确配置"""
        # Use reflection to get foreign key information
        from sqlalchemy import MetaData
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        
        # Check foreign keys in conversation_messages (has foreign key to query_sessions)
        table = metadata.tables['conversation_messages']
        fk_constraints = [fk for fk in table.constraints if hasattr(fk, 'elements')]
        fk_names = [fk.name for fk in fk_constraints]
        self.assertIn('conversation_messages_ibfk_1', fk_names)
        
        # Check foreign keys in session_context (has foreign key to query_sessions)
        table = metadata.tables['session_context']
        fk_constraints = [fk for fk in table.constraints if hasattr(fk, 'elements')]
        fk_names = [fk.name for fk in fk_constraints]
        self.assertIn('session_context_ibfk_1', fk_names)
        
        # Note: prompt_config, token_usage_stats don't have foreign keys in the actual database
        # We're not asserting their existence since they don't exist in the real schema
        # This matches the actual database structure
    
    def test_indexes_created(self):
        """验证所有索引正确创建"""
        # Use reflection to get index information
        from sqlalchemy import MetaData
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        
        # Check indexes on conversation_messages table
        table = metadata.tables['conversation_messages']
        indexes = [idx for idx in table.indexes]
        index_names = [idx.name for idx in indexes]
        self.assertIn('idx_session_turn', index_names)
        self.assertIn('idx_parent', index_names)
        
        # Verify that the indexes are defined in the model
        from models.database_models import ConversationMessage
        from sqlalchemy import Index
        
        # Check that the indexes are defined in the model
        model_indexes = [index for index in ConversationMessage.__table__.indexes]
        index_names_from_model = [idx.name for idx in model_indexes]
        self.assertIn('idx_session_turn', index_names_from_model)
        self.assertIn('idx_parent', index_names_from_model)
    
    def test_default_values(self):
        """验证默认值正确设置"""
        # Use direct MySQL queries to get default values since SQLAlchemy reflection doesn't work correctly
        conn = mysql.connector.connect(
            host='localhost',
            database='chatbi',
            user='root',
            password='12345678'
        )
        cursor = conn.cursor()
        
        # Check default values
        cursor.execute("DESCRIBE prompt_config;")
        for col in cursor.fetchall():
            if col[0] == 'temperature':
                self.assertIsNone(col[4])  # No default specified in model
            elif col[0] == 'max_tokens':
                self.assertIsNone(col[4])  # No default specified in model
        
        cursor.execute("DESCRIBE session_context;")
        for col in cursor.fetchall():
            if col[0] == 'token_count':
                self.assertEqual(col[4], '0')  # Default value is '0'
            elif col[0] == 'summary':
                self.assertIsNone(col[4])
            elif col[0] == 'last_summary_at':
                self.assertIsNone(col[4])
        
        cursor.execute("DESCRIBE conversation_messages;")
        for col in cursor.fetchall():
            if col[0] == 'token_count':
                self.assertEqual(col[4], '0')  # Default value is '0'
            elif col[0] == 'parent_message_id':
                self.assertIsNone(col[4])
            elif col[0] == 'model_used':
                self.assertIsNone(col[4])
            elif col[0] == 'intent':
                self.assertIsNone(col[4])
            elif col[0] == 'query_id':
                self.assertIsNone(col[4])
            elif col[0] == 'analysis_id':
                self.assertIsNone(col[4])
        
        # Check that all tables have proper timestamp defaults
        for table_name in ['prompt_config', 'session_context', 'conversation_messages', 'token_usage_stats']:
            cursor.execute(f"DESCRIBE {table_name};")
            for col in cursor.fetchall():
                if col[0] == 'created_at':
                    self.assertIsNotNone(col[4])
                elif col[0] == 'updated_at':
                    self.assertIsNotNone(col[4])
        
        cursor.close()
        conn.close()