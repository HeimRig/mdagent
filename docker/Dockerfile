# 沙箱镜像：只装跑 SQL 需要的东西，越小越好（约 200MB）
#   docker build -t mdagent-sandbox docker/
# 只在 docker 后端下使用；subprocess 后端不需要它。
FROM python:3.11-slim

ARG PIP_INDEX=https://mirrors.aliyun.com/pypi/simple/
RUN pip install --no-cache-dir -i ${PIP_INDEX} duckdb pandas

# 预装 sqlite 扩展：沙箱跑在 --network=none 下，运行时下载不了
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL sqlite')"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /work
CMD ["python", "/work/snippet.py"]
