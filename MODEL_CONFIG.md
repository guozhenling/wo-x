# 配置说明

## API 模型配置

你的 API 提供商不支持以下模型名称：
- ❌ `gpt-4o-mini`
- ❌ `claude-sonnet-5`

请查看 API 提供商的文档，确认支持的模型名称。

常见的 Claude 模型名称：
- `claude-3-5-sonnet-20241022`
- `claude-3-sonnet-20240229`
- `claude-3-opus-20240229`
- `claude-3-haiku-20240307`

## 如何修复

1. 查看 https://api.waibibabo.com/v1/models 或文档
2. 更新 `config.yaml` 中的 `model` 字段
3. 重新运行测试

## 当前测试结果

✅ **49 个测试通过** - 不需要 API 的测试
❌ **6 个测试失败** - 需要正确的模型名称

失败的测试：
- `test_classifier.py` - 所有测试（需要 LLM）
- 这些测试需要正确的模型名称才能运行

## 临时解决方案

如果暂时无法确认模型名称，可以跳过这些测试：

```bash
# 只运行不需要 API 的测试
pytest tests/test_models.py tests/test_tools.py tests/test_runbooks.py -v
```
