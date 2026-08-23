"""测试部署历史工具"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.deployment_history import get_deployment_history
from tools.executor import execute_tool


def test_deployment_history_basic():
    """基础查询测试"""
    result = get_deployment_history(hours=24)

    assert result['total'] >= 0
    assert 'deployments' in result
    assert 'summary' in result
    assert 'services_deployed' in result['summary']
    assert 'successful_deployments' in result['summary']
    assert 'rollback_count' in result['summary']


def test_deployment_history_time_range():
    """时间范围过滤测试"""
    # 查询最近 12 小时
    result_12 = get_deployment_history(hours=12)
    # 查询最近 24 小时
    result_24 = get_deployment_history(hours=24)

    # 24 小时应该 >= 12 小时的数据
    assert result_24['total'] >= result_12['total']


def test_deployment_history_filter_service():
    """服务过滤测试"""
    result = get_deployment_history(hours=48, service="payment")

    # 验证所有部署都是 payment 服务
    for deploy in result['deployments']:
        assert deploy['service'] == 'payment'


def test_deployment_history_limit():
    """数量限制测试"""
    result = get_deployment_history(hours=48, limit=3)

    # 验证返回数量不超过限制
    assert len(result['deployments']) <= 3
    assert result['total'] <= 3


def test_deployment_history_summary():
    """统计信息测试"""
    result = get_deployment_history(hours=48)

    if result['total'] > 0:
        # 验证统计信息
        assert result['summary']['successful_deployments'] >= 0
        assert result['summary']['rollback_count'] >= 0
        assert (result['summary']['successful_deployments'] +
                result['summary']['rollback_count']) == result['total']


def test_deployment_history_rollback():
    """回滚记录测试"""
    result = get_deployment_history(hours=48)

    # 查找回滚记录
    rollbacks = [d for d in result['deployments'] if d.get('status') == 'rollback']

    # 验证回滚记录包含原因
    for rollback in rollbacks:
        assert 'rollback_reason' in rollback


def test_deployment_history_no_results():
    """无结果测试"""
    # 查询不存在的服务
    result = get_deployment_history(hours=1, service="nonexistent")

    # 应该没有结果
    assert result['total'] == 0
    assert len(result['deployments']) == 0


def test_deployment_history_via_executor():
    """通过 executor 调用"""
    result = execute_tool("get_deployment_history", {
        "hours": 12,
        "service": "order"
    })

    assert 'deployments' in result


if __name__ == "__main__":
    print("=" * 80)
    print("测试 get_deployment_history")
    print("=" * 80)

    print("\n【测试 1】查询所有部署:")
    result = get_deployment_history(hours=24)
    print(f"找到 {result['total']} 条部署记录")
    print(f"涉及服务: {', '.join(result['summary']['services_deployed'])}")
    print(f"成功部署: {result['summary']['successful_deployments']}")
    print(f"回滚次数: {result['summary']['rollback_count']}")

    for i, deploy in enumerate(result['deployments'][:3], 1):
        print(f"\n{i}. {deploy['timestamp']}")
        print(f"   服务: {deploy['service']}")
        print(f"   版本: {deploy['previous_version']} → {deploy['version']}")
        print(f"   操作人: {deploy['deployed_by']}")
        print(f"   状态: {deploy['status']}")
        if deploy['status'] == 'rollback':
            print(f"   回滚原因: {deploy['rollback_reason']}")

    print("\n【测试 2】时间范围过滤:")
    result_12 = get_deployment_history(hours=12)
    result_24 = get_deployment_history(hours=24)
    print(f"最近 12 小时: {result_12['total']} 条")
    print(f"最近 24 小时: {result_24['total']} 条")

    print("\n【测试 3】查询特定服务:")
    result = get_deployment_history(hours=48, service="payment")
    print(f"找到 {result['total']} 条 payment 服务部署")
    for deploy in result['deployments']:
        print(f"  - {deploy['timestamp']}: {deploy['version']} ({deploy['status']})")

    print("\n【测试 4】数量限制:")
    result = get_deployment_history(hours=48, limit=2)
    print(f"限制 2 条，实际返回: {len(result['deployments'])} 条")

    print("\n【测试 5】统计信息验证:")
    result = get_deployment_history(hours=48)
    if result['total'] > 0:
        total_check = (result['summary']['successful_deployments'] +
                      result['summary']['rollback_count'])
        print(f"成功: {result['summary']['successful_deployments']}")
        print(f"回滚: {result['summary']['rollback_count']}")
        print(f"总计: {result['total']}")
        assert total_check == result['total']
        print("✓ 统计信息一致")

    print("\n【测试 6】查找回滚记录:")
    result = get_deployment_history(hours=48)
    rollbacks = [d for d in result['deployments'] if d.get('status') == 'rollback']
    print(f"找到 {len(rollbacks)} 条回滚记录")
    for rb in rollbacks:
        print(f"  - {rb['service']}: {rb['rollback_reason']}")

    print("\n✅ 所有测试通过！")
