"""
测试失败分析工具

分析 pytest 输出，提取失败信息并给出修复建议
"""
import re
from typing import List, Dict, Any
from pathlib import Path


class TestFailureAnalyzer:
    """测试失败分析器"""

    def __init__(self):
        self.failure_patterns = {
            "api_required": [
                "API",
                "openai",
                "connection",
                "rate limit",
                "authentication"
            ],
            "collection_error": [
                "ERROR collecting"
            ],
            "type_error": [
                "TypeError",
                "string indices must be integers"
            ],
            "attribute_error": [
                "AttributeError",
                "has no attribute"
            ],
            "import_error": [
                "ImportError",
                "ModuleNotFoundError"
            ],
            "assertion_error": [
                "AssertionError",
                "assert"
            ]
        }

    def analyze_pytest_output(self, output: str) -> Dict[str, Any]:
        """
        分析 pytest 输出

        Args:
            output: pytest 输出文本

        Returns:
            分析结果
        """
        # 提取失败的测试（FAILED）
        failed_tests = re.findall(
            r'FAILED (tests/\S+)::(.*?) -',
            output
        )

        if not failed_tests:
            # 尝试另一种格式
            failed_tests = re.findall(
                r'FAILED (tests/\S+)',
                output
            )
            failed_tests = [(test, "") for test in failed_tests]

        # 提取收集错误（ERROR）
        error_tests = re.findall(
            r'ERROR (tests/\S+)',
            output
        )
        error_tests = [(test, "collection error") for test in error_tests]

        # 合并所有失败
        all_failures = failed_tests + error_tests

        # 提取错误类型
        errors = re.findall(
            r'(TypeError|AttributeError|ValueError|ImportError|AssertionError|KeyError|ModuleNotFoundError)',
            output
        )

        # 分类失败
        failure_types = {
            "api_required": [],
            "type_error": [],
            "attribute_error": [],
            "import_error": [],
            "assertion_error": [],
            "collection_error": [],
            "other": []
        }

        for test_path, test_name in all_failures:
            full_name = f"{test_path}::{test_name}" if test_name and test_name != "collection error" else test_path

            # 检查是否是收集错误
            if test_name == "collection error":
                failure_types["collection_error"].append(full_name)
                continue

            # 检查是否是 API 相关
            if any(keyword in output for keyword in self.failure_patterns["api_required"]):
                if "test_e2e" in test_path or "test_api" in test_path or "test_agent" in test_path:
                    failure_types["api_required"].append(full_name)
                    continue

            # 检查错误类型
            categorized = False
            for category, patterns in self.failure_patterns.items():
                if category == "api_required":
                    continue
                for pattern in patterns:
                    if pattern in output:
                        failure_types[category].append(full_name)
                        categorized = True
                        break
                if categorized:
                    break

            if not categorized:
                failure_types["other"].append(full_name)

        # 生成建议
        suggestions = self._generate_suggestions(failure_types, output)

        # 提取堆栈跟踪中的关键信息
        key_errors = self._extract_key_errors(output)

        return {
            "total_failures": len(all_failures),
            "failure_types": failure_types,
            "suggestions": suggestions,
            "key_errors": key_errors,
            "summary": self._generate_summary(len(all_failures), failure_types)
        }

    def _generate_suggestions(
        self,
        failure_types: Dict[str, List],
        output: str
    ) -> List[Dict[str, Any]]:
        """生成修复建议"""
        suggestions = []

        # API 相关失败
        if failure_types["api_required"]:
            suggestions.append({
                "type": "API 配置",
                "priority": "high",
                "count": len(failure_types["api_required"]),
                "tests": failure_types["api_required"],
                "suggestion": (
                    "这些测试需要 API 配置。建议：\n"
                    "1. 检查 .env 文件是否存在\n"
                    "2. 确保 OPENAI_API_KEY 已设置\n"
                    "3. 确保 OPENAI_BASE_URL 正确（需要以 /v1 结尾）\n"
                    "4. 或在 CI 中排除这些测试：\n"
                    "   pytest --ignore-glob='tests/test_e2e*.py' \\\n"
                    "          --ignore-glob='tests/test_agent*.py' \\\n"
                    "          --ignore-glob='tests/test_api*.py'"
                )
            })

        # 收集错误
        if failure_types["collection_error"]:
            suggestions.append({
                "type": "测试收集错误",
                "priority": "high",
                "count": len(failure_types["collection_error"]),
                "tests": failure_types["collection_error"],
                "suggestion": (
                    "测试文件无法加载。检查以下内容：\n"
                    "1. 导入错误（缺少依赖或路径错误）\n"
                    "2. 语法错误\n"
                    "3. 测试文件中的初始化代码错误\n"
                    "4. 使用 pytest tests/filename.py -v 单独测试该文件"
                )
            })

        # 类型错误
        if failure_types["type_error"]:
            suggestions.append({
                "type": "类型错误",
                "priority": "high",
                "count": len(failure_types["type_error"]),
                "tests": failure_types["type_error"],
                "suggestion": (
                    "检查以下内容：\n"
                    "1. 变量类型是否符合预期\n"
                    "2. 函数返回值类型（查看类型注解）\n"
                    "3. 字典 vs 字符串混淆\n"
                    "4. 使用 isinstance() 验证类型"
                )
            })

        # 属性错误
        if failure_types["attribute_error"]:
            suggestions.append({
                "type": "属性错误",
                "priority": "medium",
                "count": len(failure_types["attribute_error"]),
                "tests": failure_types["attribute_error"],
                "suggestion": (
                    "检查以下内容：\n"
                    "1. 对象是否正确初始化\n"
                    "2. 属性名是否拼写正确\n"
                    "3. 是否应该使用方法而不是属性\n"
                    "4. 对象是否为 None"
                )
            })

        # 导入错误
        if failure_types["import_error"]:
            suggestions.append({
                "type": "导入错误",
                "priority": "high",
                "count": len(failure_types["import_error"]),
                "tests": failure_types["import_error"],
                "suggestion": (
                    "检查以下内容：\n"
                    "1. 模块是否已安装（pip install <module>）\n"
                    "2. 导入路径是否正确\n"
                    "3. 是否有循环导入\n"
                    "4. requirements.txt 是否完整"
                )
            })

        # 断言错误
        if failure_types["assertion_error"]:
            suggestions.append({
                "type": "断言失败",
                "priority": "medium",
                "count": len(failure_types["assertion_error"]),
                "tests": failure_types["assertion_error"],
                "suggestion": (
                    "检查以下内容：\n"
                    "1. 期望值是否正确\n"
                    "2. 代码逻辑是否符合预期\n"
                    "3. 测试数据是否准确\n"
                    "4. 是否需要更新测试"
                )
            })

        return suggestions

    def _extract_key_errors(self, output: str) -> List[str]:
        """提取关键错误信息"""
        key_errors = []

        # 提取错误消息
        error_lines = re.findall(
            r'(TypeError|AttributeError|ValueError|ImportError|AssertionError|KeyError):(.+)',
            output
        )

        for error_type, error_msg in error_lines[:5]:  # 最多 5 个
            key_errors.append(f"{error_type}: {error_msg.strip()}")

        return key_errors

    def _generate_summary(
        self,
        total: int,
        failure_types: Dict[str, List]
    ) -> str:
        """生成摘要"""
        if total == 0:
            return "✅ 所有测试通过"

        lines = [f"发现 {total} 个失败测试"]

        # 统计各类型
        type_counts = []
        for ftype, tests in failure_types.items():
            if tests and ftype != "other":
                type_counts.append(f"{len(tests)} 个 {ftype}")

        if type_counts:
            lines.append("分布: " + ", ".join(type_counts))

        return "\n".join(lines)

    def analyze_from_file(self, filepath: str) -> Dict[str, Any]:
        """
        从文件读取 pytest 输出并分析

        Args:
            filepath: pytest 输出文件路径

        Returns:
            分析结果
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            output = f.read()

        return self.analyze_pytest_output(output)

    def print_analysis(self, analysis: Dict[str, Any]):
        """打印分析结果"""
        print("\n" + "=" * 60)
        print("测试失败分析")
        print("=" * 60)

        print(f"\n{analysis['summary']}")

        if analysis["total_failures"] == 0:
            return

        # 失败类型分布
        print(f"\n失败类型分布:")
        for ftype, tests in analysis["failure_types"].items():
            if tests:
                print(f"  {ftype}: {len(tests)} 个")

        # 关键错误
        if analysis["key_errors"]:
            print(f"\n关键错误:")
            for error in analysis["key_errors"]:
                print(f"  ❌ {error}")

        # 修复建议
        if analysis["suggestions"]:
            print(f"\n修复建议:")
            for i, suggestion in enumerate(analysis["suggestions"], 1):
                print(f"\n  {i}. [{suggestion['type']}] (优先级: {suggestion['priority']})")
                print(f"     影响 {suggestion['count']} 个测试")
                print(f"\n{suggestion['suggestion']}")
                if suggestion.get("tests"):
                    print(f"\n     失败的测试:")
                    for test in suggestion["tests"][:3]:
                        print(f"       - {test}")
                    if len(suggestion["tests"]) > 3:
                        print(f"       ... 还有 {len(suggestion['tests']) - 3} 个")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    """
    命令行使用
    """
    import sys

    if len(sys.argv) < 2:
        print("测试失败分析工具使用示例:")
        print("\n# 方式 1: 分析 pytest 输出")
        print("pytest tests/ -v > test_output.txt 2>&1")
        print("python tools/test_failure_analyzer.py test_output.txt")
        print("")
        print("# 方式 2: 在代码中使用")
        print("from tools.test_failure_analyzer import TestFailureAnalyzer")
        print("")
        print("analyzer = TestFailureAnalyzer()")
        print("analysis = analyzer.analyze_from_file('test_output.txt')")
        print("analyzer.print_analysis(analysis)")
        sys.exit(1)

    # 分析文件
    filepath = sys.argv[1]

    if not Path(filepath).exists():
        print(f"\n❌ 文件不存在: {filepath}")
        sys.exit(1)

    analyzer = TestFailureAnalyzer()
    analysis = analyzer.analyze_from_file(filepath)
    analyzer.print_analysis(analysis)

    sys.exit(0 if analysis["total_failures"] == 0 else 1)
