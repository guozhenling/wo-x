#!/usr/bin/env python3
"""
快速验证脚本 - 验证 v1.0 集成是否正常

验证内容：
1. 所有模块导入正常
2. 基本功能可用
3. 端到端流程通畅
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def verify_imports():
    """验证模块导入"""
    print("=" * 80)
    print("1. 验证模块导入")
    print("=" * 80)

    modules = [
        ("src.models", "IncidentResult"),
        ("src.policy", "PolicyEngine"),
        ("src.trace_manager", "TraceManager"),
        ("tools.tool_coordinator", "ToolCoordinator"),
        ("tools.robust_executor", "RobustToolExecutor"),
        ("src.incident_classifier_v1", "IncidentClassifierV1"),
    ]

    failed = []
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  ✓ {module_name}.{class_name}")
        except Exception as e:
            print(f"  ✗ {module_name}.{class_name}: {e}")
            failed.append((module_name, class_name, e))

    if failed:
        print(f"\n✗ {len(failed)} 个模块导入失败")
        return False

    print(f"\n✓ 所有模块导入成功")
    return True


def verify_classifier_initialization():
    """验证分类器初始化"""
    print("\n" + "=" * 80)
    print("2. 验证分类器初始化")
    print("=" * 80)

    try:
        from src.incident_classifier_v1 import IncidentClassifierV1

        classifier = IncidentClassifierV1(trace_dir="traces/verify")

        print(f"  ✓ 分类器版本: {classifier.VERSION}")
        print(f"  ✓ 模型: {classifier.model}")
        print(f"  ✓ Policy 引擎: {classifier.policy}")
        print(f"  ✓ Trace 管理器: {classifier.trace}")

        print(f"\n✓ 分类器初始化成功")
        return True, classifier

    except Exception as e:
        print(f"\n✗ 分类器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def verify_basic_classification(classifier):
    """验证基本分类功能"""
    print("\n" + "=" * 80)
    print("3. 验证基本分类功能")
    print("=" * 80)

    test_description = "支付接口 5xx 错误率 35%"
    print(f"测试案例: {test_description}")
    print("-" * 80)

    try:
        result = classifier.classify(test_description)

        # 验证结果结构
        assert 'success' in result, "缺少 success 字段"
        assert 'version' in result, "缺少 version 字段"
        assert 'classification' in result, "缺少 classification 字段"
        assert 'evidence_summary' in result, "缺少 evidence_summary 字段"
        assert 'trace' in result, "缺少 trace 字段"
        assert 'performance' in result, "缺少 performance 字段"

        # 验证分类结果
        classification = result['classification']
        assert 'severity' in classification, "缺少 severity 字段"
        assert 'category' in classification, "缺少 category 字段"
        assert 'needs_human_review' in classification, "缺少 needs_human_review 字段"
        assert 'rationale' in classification, "缺少 rationale 字段"

        print(f"\n✓ 结果结构验证通过")
        print(f"  版本: {result['version']}")
        print(f"  成功: {result['success']}")
        print(f"  严重程度: {classification['severity']}")
        print(f"  类别: {classification['category']}")
        print(f"  需要审核: {classification['needs_human_review']}")
        print(f"  工具调用: {result['performance']['tool_calls']}")
        print(f"  耗时: {result['duration_seconds']}s")

        return True

    except Exception as e:
        print(f"\n✗ 分类功能验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_tool_coordinator():
    """验证 ToolCoordinator 集成"""
    print("\n" + "=" * 80)
    print("4. 验证 ToolCoordinator 集成")
    print("=" * 80)

    try:
        from tools.tool_coordinator import ToolCoordinator
        from src.trace_manager import TraceManager

        # 创建模拟 Agent
        class MockAgent:
            def __init__(self):
                self.trace = TraceManager()

        agent = MockAgent()
        coordinator = ToolCoordinator(agent)

        # 测试规划
        plan = coordinator.plan_tool_calls(
            "支付接口 5xx 错误率 35%",
            {"severity": "P0", "category": "availability"}
        )

        print(f"  ✓ 规划了 {len(plan)} 个工具调用")
        for i, step in enumerate(plan, 1):
            print(f"    {i}. {step['tool']} - {step['reason']}")

        # 验证健壮执行器
        print(f"\n  ✓ 健壮执行器: {coordinator.robust_executor}")

        # 验证缓存
        print(f"  ✓ 缓存系统: {coordinator.cache}")

        print(f"\n✓ ToolCoordinator 集成验证通过")
        return True

    except Exception as e:
        print(f"\n✗ ToolCoordinator 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_robust_executor():
    """验证 RobustToolExecutor"""
    print("\n" + "=" * 80)
    print("5. 验证 RobustToolExecutor")
    print("=" * 80)

    try:
        from tools.robust_executor import RobustToolExecutor

        executor = RobustToolExecutor()

        # 测试简单执行
        def dummy_tool(**kwargs):
            return {"result": "success"}

        result = executor.execute(
            tool_name="test_tool",
            tool_function=dummy_tool,
            arguments={},
            timeout_seconds=5,
            max_retries=2
        )

        print(f"  ✓ 工具执行成功: {result}")

        # 获取指标
        metrics = executor.get_metrics()
        print(f"\n  ✓ 性能指标:")
        print(f"    总调用: {metrics['total_calls']}")
        print(f"    成功率: {metrics['success_rate']:.1%}")
        print(f"    缓存命中率: {metrics['cache_hit_rate']:.1%}")

        print(f"\n✓ RobustToolExecutor 验证通过")
        return True

    except Exception as e:
        print(f"\n✗ RobustToolExecutor 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_policy_engine():
    """验证 PolicyEngine"""
    print("\n" + "=" * 80)
    print("6. 验证 PolicyEngine")
    print("=" * 80)

    try:
        from src.policy import PolicyEngine

        policy = PolicyEngine()

        # 测试规则修正
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": False
        }

        corrected = policy.check_and_enforce(
            "支付接口 5xx 错误率 35%",
            result
        )

        # P0 应该强制需要人工审核
        assert corrected['needs_human_review'] is True, "P0 应该需要人工审核"

        violations = policy.get_violations()
        print(f"  ✓ 触发了 {len(violations)} 条规则")
        for v in violations:
            print(f"    - [{v.level.value}] {v.policy_name}: {v.message}")

        print(f"\n✓ PolicyEngine 验证通过")
        return True

    except Exception as e:
        print(f"\n✗ PolicyEngine 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_trace_manager():
    """验证 TraceManager"""
    print("\n" + "=" * 80)
    print("7. 验证 TraceManager")
    print("=" * 80)

    try:
        from src.trace_manager import TraceManager
        from pathlib import Path

        trace = TraceManager(trace_dir="traces/verify")

        # 开始轨迹
        trace_id = trace.start_trace("测试轨迹")
        print(f"  ✓ 开始轨迹: {trace_id}")

        # 记录工具调用
        trace.record_tool_call(
            tool_name="test_tool",
            tool_input={"arg": "value"},
            tool_output={"result": "success"},
            success=True
        )
        print(f"  ✓ 记录工具调用")

        # 结束轨迹
        trace_file = trace.finish_trace(
            final_answer={"severity": "P0"},
            status="success"
        )
        print(f"  ✓ 结束轨迹: {trace_file}")

        # 验证文件存在
        assert Path(trace_file).exists(), "轨迹文件不存在"
        print(f"  ✓ 轨迹文件存在")

        print(f"\n✓ TraceManager 验证通过")
        return True

    except Exception as e:
        print(f"\n✗ TraceManager 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("故障分类器 v1.0 集成验证")
    print("=" * 80 + "\n")

    results = []

    # 1. 验证模块导入
    results.append(("模块导入", verify_imports()))

    # 2. 验证分类器初始化
    success, classifier = verify_classifier_initialization()
    results.append(("分类器初始化", success))

    if classifier:
        # 3. 验证基本分类功能
        results.append(("基本分类功能", verify_basic_classification(classifier)))
    else:
        results.append(("基本分类功能", False))

    # 4. 验证 ToolCoordinator
    results.append(("ToolCoordinator", verify_tool_coordinator()))

    # 5. 验证 RobustToolExecutor
    results.append(("RobustToolExecutor", verify_robust_executor()))

    # 6. 验证 PolicyEngine
    results.append(("PolicyEngine", verify_policy_engine()))

    # 7. 验证 TraceManager
    results.append(("TraceManager", verify_trace_manager()))

    # 汇总结果
    print("\n" + "=" * 80)
    print("验证结果汇总")
    print("=" * 80)

    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)

    print("\n" + "-" * 80)
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print("\n" + "=" * 80)
        print("✅ 所有验证通过！系统集成正常！")
        print("=" * 80 + "\n")
        return 0
    else:
        print("\n" + "=" * 80)
        print(f"❌ {total - passed} 项验证失败，请检查!")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
