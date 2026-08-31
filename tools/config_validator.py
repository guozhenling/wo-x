"""
配置验证工具

启动前验证关键配置
"""
import os
from typing import Dict, List
from pathlib import Path


class ConfigValidator:
    """配置验证器"""

    def __init__(self, project_root: Path = None):
        """
        初始化配置验证器

        Args:
            project_root: 项目根目录，默认为当前工作目录
        """
        self.project_root = project_root or Path.cwd()

        self.required_configs = {
            "OPENAI_API_KEY": "OpenAI API 密钥",
        }

        self.optional_configs = {
            "OPENAI_BASE_URL": "OpenAI API 基础 URL",
            "OPENAI_MODEL": "使用的模型",
        }

    def validate(self) -> Dict:
        """
        验证所有配置

        Returns:
            验证结果
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": []
        }

        # 检查 .env 文件
        env_file = self.project_root / ".env"
        if not env_file.exists():
            results["warnings"].append(
                "未找到 .env 文件，将使用环境变量或默认值"
            )

        # 验证必需配置
        for key, desc in self.required_configs.items():
            value = os.getenv(key)
            if not value:
                results["errors"].append(f"缺少必需配置: {key} ({desc})")
                results["valid"] = False
            else:
                results["info"].append(f"✓ {key}: 已设置")

        # 验证可选配置
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL")

        if not base_url:
            results["warnings"].append(
                "未设置 OPENAI_BASE_URL，将使用 OpenAI 默认值"
            )
        else:
            # 检查 BASE_URL 格式
            if not base_url.endswith("/v1"):
                results["errors"].append(
                    f"OPENAI_BASE_URL 应该以 /v1 结尾\n"
                    f"  当前: {base_url}\n"
                    f"  建议: {base_url}/v1"
                )
                results["valid"] = False
            else:
                results["info"].append(f"✓ OPENAI_BASE_URL: {base_url}")

        if not model:
            results["warnings"].append(
                "未设置 OPENAI_MODEL，将使用默认值 (gpt-4o-mini)"
            )
        else:
            results["info"].append(f"✓ OPENAI_MODEL: {model}")

        # 验证目录结构
        required_dirs = [
            "src",
            "tests",
            "outputs",
        ]

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                results["warnings"].append(
                    f"目录不存在: {dir_name}（可能不影响运行）"
                )

        # 验证关键文件
        critical_files = [
            "src/incident_classifier_v1.py",
            "src/policy.py",
            "src/trace_manager.py",
        ]

        for file_path in critical_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                results["errors"].append(f"关键文件缺失: {file_path}")
                results["valid"] = False

        return results

    def validate_with_test(self) -> Dict:
        """
        验证配置并尝试连接 API

        Returns:
            验证结果
        """
        results = self.validate()

        if not results["valid"]:
            return results

        # 尝试连接 API
        try:
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")

            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )

            # 简单的测试请求
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )

            results["info"].append("✓ API 连接测试通过")

        except Exception as e:
            results["errors"].append(f"API 连接测试失败: {str(e)}")
            results["valid"] = False

        return results

    def print_results(self, results: Dict):
        """打印验证结果"""
        print("\n" + "=" * 60)
        print("配置验证")
        print("=" * 60)

        # 总体状态
        if results["valid"]:
            print("\n✅ 配置验证通过")
        else:
            print("\n❌ 配置验证失败")

        # 错误
        if results["errors"]:
            print(f"\n错误 ({len(results['errors'])} 个):")
            for err in results["errors"]:
                print(f"  ❌ {err}")

        # 警告
        if results["warnings"]:
            print(f"\n警告 ({len(results['warnings'])} 个):")
            for warn in results["warnings"]:
                print(f"  ⚠️  {warn}")

        # 信息
        if results["info"]:
            print(f"\n配置信息:")
            for info in results["info"]:
                print(f"  {info}")

        print("\n" + "=" * 60)

        # 修复建议
        if not results["valid"]:
            print("\n修复建议:")
            if any("OPENAI_API_KEY" in err for err in results["errors"]):
                print("  1. 创建 .env 文件")
                print("  2. 添加: OPENAI_API_KEY=your_api_key")
            if any("/v1" in err for err in results["errors"]):
                print("  3. 修正 OPENAI_BASE_URL，确保以 /v1 结尾")
            print("\n参考 .env.example 文件")


def quick_validate():
    """快速验证（命令行使用）"""
    from dotenv import load_dotenv
    load_dotenv()

    validator = ConfigValidator(project_root=Path.cwd())
    results = validator.validate()
    validator.print_results(results)

    return 0 if results["valid"] else 1


if __name__ == "__main__":
    """
    使用示例
    """
    import sys

    # 加载 .env
    from dotenv import load_dotenv
    load_dotenv()

    # 创建验证器
    validator = ConfigValidator(project_root=Path.cwd())

    # 选择验证模式
    print("配置验证工具")
    print("1. 快速验证（检查配置文件）")
    print("2. 完整验证（包含 API 连接测试）")
    choice = input("\n选择模式 (1/2，默认 1): ").strip() or "1"

    if choice == "2":
        print("\n正在验证配置并测试 API 连接...")
        results = validator.validate_with_test()
    else:
        results = validator.validate()

    validator.print_results(results)

    sys.exit(0 if results["valid"] else 1)
