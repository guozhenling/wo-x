# 多阶段构建：减小镜像体积
FROM python:3.11-slim as builder

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 最终镜像
FROM python:3.11-slim

WORKDIR /app

# 从 builder 复制依赖
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY src/ ./src/
COPY tools/ ./tools/
COPY scripts/ ./scripts/
COPY .env.example ./.env

# 设置环境变量
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import src.incident_classifier_v1; print('OK')" || exit 1

# 暴露端口（预留，未来可能有 API 服务）
EXPOSE 8000

# 默认命令
CMD ["python", "-m", "src.incident_classifier_v1", "--help"]
