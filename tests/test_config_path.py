#!/usr/bin/env python3
"""
测试配置文件查找功能
验证从不同目录运行时都能找到 config.yaml
"""

import sys
from pathlib import Path

# 添加 src 到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from client import find_project_root, LLMClient


def test_find_project_root():
    """测试项目根目录查找"""
    print("=" * 80)
    print("测试项目根目录查找")
    print("=" * 80)
    print()

    root = find_project_root()
    print(f"✓ 找到项目根目录: {root}")

    config_file = root / "config.yaml"
    if config_file.exists():
        print(f"✓ 配置文件存在: {config_file}")
    else:
        print(f"✗ 配置文件不存在: {config_file}")
        return False

    print()
    return True


def test_llm_client_init():
    """测试 LLMClient 初始化"""
    print("=" * 80)
    print("测试 LLMClient 初始化")
    print("=" * 80)
    print()

    try:
        # 测试不带参数（自动查找配置）
        print("1. 测试自动查找配置...")
        client = LLMClient()
        print(f"   ✓ 初始化成功")
        print(f"   ✓ 协议: {client.protocol}")
        print()

        # 测试显式指定路径
        print("2. 测试显式指定配置路径...")
        config_path = find_project_root() / "config.yaml"
        client2 = LLMClient(config_path=str(config_path))
        print(f"   ✓ 初始化成功")
        print(f"   ✓ 协议: {client2.protocol}")
        print()

        return True

    except FileNotFoundError as e:
        print(f"   ✗ 配置文件未找到: {e}")
        print()
        print("   请确保:")
        print("   1. config.yaml 文件存在于项目根目录")
        print("   2. 可以从 config.yaml.example 复制一份并修改")
        return False

    except Exception as e:
        print(f"   ✗ 初始化失败: {e}")
        return False


def test_from_different_directories():
    """测试从不同目录运行"""
    print("=" * 80)
    print("测试从不同目录运行")
    print("=" * 80)
    print()

    import os
    original_dir = os.getcwd()

    try:
        # 测试从 tests 目录
        tests_dir = project_root / "tests"
        if tests_dir.exists():
            print(f"1. 从 tests 目录运行...")
            os.chdir(tests_dir)
            client = LLMClient()
            print(f"   ✓ 成功 (当前目录: {os.getcwd()})")
            print()

        # 测试从 examples 目录
        examples_dir = project_root / "examples"
        if examples_dir.exists():
            print(f"2. 从 examples 目录运行...")
            os.chdir(examples_dir)
            client = LLMClient()
            print(f"   ✓ 成功 (当前目录: {os.getcwd()})")
            print()

        # 测试从项目根目录
        print(f"3. 从项目根目录运行...")
        os.chdir(project_root)
        client = LLMClient()
        print(f"   ✓ 成功 (当前目录: {os.getcwd()})")
        print()

        return True

    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

    finally:
        os.chdir(original_dir)


def main():
    """运行所有测试"""
    print("\n🔍 开始测试配置文件查找功能...\n")

    results = []

    # 测试 1: 查找项目根目录
    results.append(("查找项目根目录", test_find_project_root()))

    # 测试 2: LLMClient 初始化
    results.append(("LLMClient 初始化", test_llm_client_init()))

    # 测试 3: 从不同目录运行
    results.append(("从不同目录运行", test_from_different_directories()))

    # 汇总结果
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print()

    all_passed = True
    for test_name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 所有测试通过！")
        print()
        print("现在可以从任何目录运行测试:")
        print("  python tests/run_tests.py")
        print("  python tests/test_cases.py")
        print("  python tests/verify_framework.py")
    else:
        print("⚠️  部分测试失败")
        print()
        print("请检查:")
        print("  1. config.yaml 文件是否存在")
        print("  2. API 配置是否正确")

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
