"""conftest.py — shared pytest fixtures"""
import os
import pytest

def pytest_configure(config):
    os.environ.setdefault('FLASK_ENV', 'testing')
    os.environ.setdefault('GEMINI_API_KEY', 'test-key-do-not-use')

