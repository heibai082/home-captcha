# 选用官方 Python 镜像作为基础
FROM python:3.10-slim

# 分配工作目录
WORKDIR /app

# 配置统一时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装依赖
COPY requirements.txt .
# 使用国内阿里云镜像源加速构建
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 拷贝代码目录
COPY ./app ./app
COPY ./static ./static

# 对外暴露运行端口
EXPOSE 8000

# 运行 FastAPI 服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
