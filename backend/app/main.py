# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 创建 FastAPI 实例
app = FastAPI(
    title="DevTrendAnalysis API",
    description="后端提供给前端的数据接口",
    version="0.1.0",
)

# 允许哪些前端域名来访问（开发环境下）
origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

# 配置 CORS 中间件，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # 允许的前端地址
    allow_credentials=True,
    allow_methods=["*"],          # 允许所有 HTTP 方法（GET/POST 等）
    allow_headers=["*"],          # 允许所有请求头
)


# 一个简单的健康检查接口，可选
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 前端刚才在 App.jsx 里请求的接口：
#    fetch("http://127.0.0.1:8000/api/hello")
@app.get("/api/hello")
async def hello():
    return {"message": "Hello from FastAPI"}


# 额外送一个“返回列表数据”的接口，方便你以后做表格/图表
@app.get("/api/sample-data")
async def sample_data():
    """
    返回一些假数据，前端可以拿去画图或做表格：
    [
      {"label": "Jan", "value": 10},
      {"label": "Feb", "value": 20},
      ...
    ]
    """
    data = [
        {"label": "Jan", "value": 10},
        {"label": "Feb", "value": 25},
        {"label": "Mar", "value": 18},
        {"label": "Apr", "value": 30},
    ]
    return {"items": data}
