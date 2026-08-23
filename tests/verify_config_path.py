#!/usr/bin/env python3
"""
配置路径修复验证（轻量级版本）
不需要安装 openai/anthropic 依赖
"""

import sys
from pathlib import Path

# 添加 src 到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


def test_find_project_root():
    """测试项目根目录查找"""
    print("=" * 80)
    print("测试 1: 查找项目根目录")
    print("=" * 80)

    try:
        from client import find_project_root

        root = find_project_root()
        print(f"✓ 找到项目根目录: {root}")

        config_file = root / "config.yaml"
        if config_file.exists():
            print(f"✓ 配置文件存在: {config_file}")
            return True
        else:
            print(f"✗ 配置文件不存在: {config_file}")
            print(f"  请从 config.yaml.example 复制一份")
            return False

    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def test_from_different_dirs():
    """测试从不同目录查找"""
    print("\n" + "=" * 80)
    print("测试 2: 从不同目录运行")
    print("=" * 80)

    import os
    original_dir = os.getcwd()

    try:
        from client import find_project_root

        test_dirs = [
            ("项目根目录", project_root),
            ("tests 目录", project_root / "tests"),
            ("examples 目录", project_root / "examples"),
            ("src 目录", project_root / "src"),
        ]

        all_passed = True
        for name, test_dir in test_dirs:
            if not test_dir.exists():
                print(f"⊙ 跳过 {name} (目录不存在)")
                continue

            os.chdir(test_dir)
            root = find_project_root()
            config_exists = (root / "config.yaml").exists()

            if config_exists:
                print(f"✓ {name}: 成功找到配置")
            else:
                print(f"✗ {name}: 未找到配置")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"✗ 失败: {e}")
        return False
    finally:
        os.chdir(original_dir)


def test_config_loading():
    """测试配置加载（不初始化 LLM 客户端）"""
    print("\n" + "=" * 80)
    print("测试 3: 配置文件加载")
    print("=" * 80)

    try:
        import yaml
        from client import find_project_root

        root = find_project_root()
        config_file = root / "config.yaml"

        if not config_file.exists():
            print("✗ 配置文件不存在，跳过此测试")
            return False

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        print("✓ 配置文件解析成功")

        # 检查必需字段
        if 'api' in config:
            print("✓ 包含 api 配置")
            api_config = config['api']

            required_fields = ['protocol', 'api_key']
            for field in required_fields:
                if field in api_config:
                    value = api_config[field]
                    # 隐藏 API key
                    if field == 'api_key' and value:
                        display_value = value[:8] + "..." if len(value) > 8 else "***"
                    else:
                        display_value = value
                    print(f"  ✓ {field}: {display_value}")
                else:
                    print(f"  ⚠ 缺少 {field}")

            return True
        else:
            print("✗ 缺少 api 配置")
            return False

    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🔍 配置路径修复验证\n")

    results = [
        ("查找项目根目录", test_find_project_root()),
        ("从不同目录运行", test_from_different_dirs()),
        ("配置文件加载", test_config_loading()),
    ]

    # 汇总
    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)

    all_passed = True
    for name, passed in results:
        status = "✓" if passed else "✗"
        print(f"{status} {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 所有验证通过！")
        print()
        print("配置路径问题已修复，现在可以:")
        print("  • 从任何目录运行测试")
        print("  • 在 PyCharm 中直接运行")
        print("  • 使用 LLMClient() 自动查找配置")
    else:
        print("⚠️  部分验证失败")
        print()
        print("请检查:")
        print("  1. config.yaml 是否存在于项目根目录")
        print("  2. 从 config.yaml.example 复制并配置")

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
