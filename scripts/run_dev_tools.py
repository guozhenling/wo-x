#!/usr/bin/env python3
"""
Day 17-18 工具集成脚本

集成配置验证和测试失败分析工具
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.config_validator import ConfigValidator
from tools.test_failure_analyzer import TestFailureAnalyzer


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Day 17-18: 失败分析与优化工具")
    print("=" * 60)

    print("\n可用工具:")
    print("  1. 配置验证工具（验证 .env 和系统配置）")
    print("  2. 测试失败分析器（分析 pytest 输出）")
    print("  3. 完整检查（运行所有工具）")
    print("")

    mode = input("选择工具 (1/2/3，默认 1): ").strip() or "1"

    if mode == "1":
        # 配置验证
        print("\n" + "=" * 60)
        print("配置验证工具")
        print("=" * 60)

        from dotenv import load_dotenv
        load_dotenv()

        # 传入项目根目录
        project_root = Path(__file__).parent.parent
        validator = ConfigValidator(project_root=project_root)

        print("\n选择验证模式:")
        print("  1. 快速验证（仅检查配置文件）")
        print("  2. 完整验证（包含 API 连接测试）")
        test_mode = input("\n选择模式 (1/2，默认 1): ").strip() or "1"

        if test_mode == "2":
            print("\n正在验证配置并测试 API 连接...")
            results = validator.validate_with_test()
        else:
            results = validator.validate()

        validator.print_results(results)

        return 0 if results["valid"] else 1

    elif mode == "2":
        # 测试失败分析
        print("\n" + "=" * 60)
        print("测试失败分析器")
        print("=" * 60)

        print("\n请提供 pytest 输出文件路径")
        print("（运行 pytest tests/ -v > test_output.txt 2>&1 生成）")
        filepath = input("\n文件路径 (默认: test_output.txt): ").strip() or "test_output.txt"

        if not Path(filepath).exists():
            print(f"\n❌ 文件不存在: {filepath}")
            print("\n提示: 先运行以下命令生成输出文件:")
            print("  pytest tests/ -v > test_output.txt 2>&1")
            return 1

        analyzer = TestFailureAnalyzer()
        analysis = analyzer.analyze_from_file(filepath)
        analyzer.print_analysis(analysis)

        return 0

    elif mode == "3":
        # 完整检查
        print("\n执行完整检查...")

        # 1. 配置验证
        print("\n" + "=" * 60)
        print("1/2: 配置验证")
        print("=" * 60)

        from dotenv import load_dotenv
        load_dotenv()

        # 传入项目根目录
        project_root = Path(__file__).parent.parent
        validator = ConfigValidator(project_root=project_root)
        results = validator.validate()
        validator.print_results(results)

        if not results["valid"]:
            print("\n⚠️ 配置验证失败，建议先修复配置问题")

        # 2. 测试失败分析
        print("\n" + "=" * 60)
        print("2/2: 测试失败分析")
        print("=" * 60)

        test_output_file = "test_output.txt"
        if Path(test_output_file).exists():
            print(f"\n发现测试输出文件: {test_output_file}")
            analyzer = TestFailureAnalyzer()
            analysis = analyzer.analyze_from_file(test_output_file)
            analyzer.print_analysis(analysis)
        else:
            print(f"\n未找到测试输出文件: {test_output_file}")
            print("\n运行以下命令生成:")
            print("  pytest tests/ -v > test_output.txt 2>&1")

        print("\n" + "=" * 60)
        print("完整检查完成")
        print("=" * 60)

        return 0

    else:
        print("\n❌ 无效的选择")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
