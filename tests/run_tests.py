#!/usr/bin/env python3
"""
批量测试分类器准确性（兼容版本）
保持向后兼容，同时支持新的测试框架
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# 使用新的测试框架
from test_cases import run_tests


if __name__ == "__main__":
    # 保持原有的简单调用方式
    run_tests(verbose=True, save_results=True)
