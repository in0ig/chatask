import pytest
import time
import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from services.session_service import SessionService
from services.context_summarizer import ContextSummarizer

@pytest.fixture
def session_service():
    """Fixture for SessionService"""
    return SessionService()

@pytest.fixture
def context_summarizer():
    """Fixture for ContextSummarizer"""
    return ContextSummarizer()

@pytest.fixture
def benchmark_timer():
    """Fixture to measure execution time"""
    start_time = time.time()
    yield
    end_time = time.time()
    print(f"\nExecution time: {end_time - start_time:.4f} seconds")