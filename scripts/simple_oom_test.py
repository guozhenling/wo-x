#!/usr/bin/env python3
"""最简单的 OOM 测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent_v2 import IncidentAgentV2

agent = IncidentAgentV2()

description = "recommendation 服务 Pod 内存溢出，重启 5 次"

print("=" * 80)
print(f"测试: {description}")
print("=" * 80)

result = agent.analyze(description)

print("\n【结果】")
print(f"分类: {result['classification']['severity']}, {result['classification']['category']}")
print(f"证据数量: {len(result['evidence'])}")

evidence_tools = [ev["tool"] for ev in result["evidence"]]
print(f"调用工具: {evidence_tools}")

if "search_oom_events" in evidence_tools:
    print("\n✅ 成功调用了 OOM 工具")
else:
    print("\n❌ 没有调用 OOM 工具")
    print(f"期望: search_oom_events")
    print(f"实际: {evidence_tools}")
