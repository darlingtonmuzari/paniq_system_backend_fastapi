"""
Simple test to verify task testing works
"""
import pytest
from unittest.mock import MagicMock


def test_simple():
    """Simple test"""
    assert True


class TestSimple:
    """Simple test class"""
    
    def test_method(self):
        """Simple test method"""
        assert True