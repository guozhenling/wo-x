"""
配置管理工具

支持从多个来源读取配置：
1. .env 文件（优先）
2. config.yaml 文件（兼容旧版本）
3. 环境变量
"""
import os
import yaml
from pathlib import Path
from typing import Optional


def load_config() -> dict:
    """
    加载配置

    优先级：
    1. .env 文件
    2. config.yaml 文件
    3. 环境变量

    Returns:
        配置字典
    """
    config = {}

    # 1. 尝试从 config.yaml 读取
    config_file = Path("config.yaml")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config and 'api' in yaml_config:
                api_config = yaml_config['api']
                config['OPENAI_API_KEY'] = api_config.get('api_key')
                config['OPENAI_BASE_URL'] = api_config.get('base_url')
                config['OPENAI_MODEL'] = api_config.get('model', 'gpt-4o-mini')

    # 2. .env 文件会覆盖 config.yaml（如果存在）
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # 3. 环境变量优先级最高
    if os.getenv('OPENAI_API_KEY'):
        config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    if os.getenv('OPENAI_BASE_URL'):
        config['OPENAI_BASE_URL'] = os.getenv('OPENAI_BASE_URL')

    return config


def get_api_key() -> Optional[str]:
    """获取 API Key"""
    config = load_config()
    return config.get('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')


def get_base_url() -> Optional[str]:
    """获取 Base URL"""
    config = load_config()
    return config.get('OPENAI_BASE_URL') or os.getenv('OPENAI_BASE_URL')


def get_model() -> str:
    """获取模型名称"""
    config = load_config()
    return config.get('OPENAI_MODEL') or os.getenv('OPENAI_MODEL') or 'claude-sonnet-5'


# 在导入时自动加载配置到环境变量
_config = load_config()
for key, value in _config.items():
    if value:
        os.environ[key] = value


if __name__ == "__main__":
    print("配置信息:")
    print(f"API Key: {get_api_key()[:20]}..." if get_api_key() else "未配置")
    print(f"Base URL: {get_base_url()}")
    print(f"Model: {get_model()}")
