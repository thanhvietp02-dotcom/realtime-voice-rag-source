"""
语音 RAG 后端的总入口。

这份文件负责把以下几部分串联起来：
1. Web 前端：获取场景、启动或停止语音对话；
2. 火山引擎 RTC：完成实时语音通信、语音识别和语音合成；
3. RAG 知识库：根据用户问题检索相关资料；
4. 方舟大模型：结合对话历史和检索资料生成回答。

主要接口：
- POST /getScenes：向前端返回场景及 RTC 入会信息；
- POST /proxy：代理 StartVoiceChat、StopVoiceChat 等 RTC 操作；
- POST /api/chat_callback：接收 RTC 的文字请求并流式返回模型回答；
- POST /debug/chat：绕过 RTC，单独测试 RAG + 大模型；
- GET  /debug/rag：只测试知识库检索。
"""

import uuid
import time
import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from config import settings
from services.llm_service import llm_service
from services.token_build import AccessToken, PRIVILEGES
from services.utils import Signer  # 确保 utils.py 已移动到 services 目录

from fastapi.responses import JSONResponse

from fastapi import Request
from fastapi.responses import StreamingResponse  # <--- 必须导入这个
import json
from services.rag_service import rag_service  # <--- 新增这行

# 在你的 settings.py 或 main.py 顶部
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 中的密钥、模型 ID、RTC 配置和公网回调地址

# ==================== 模块 1：创建 Web 服务 ====================
app = FastAPI()

# 允许前端页面跨域请求 Python 后端。当前“*”适合本地开发，生产环境应限制域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 模块 2：场景初始化 ====================
# 前端进入页面时调用。返回智能体展示信息，以及加入 RTC 房间所需的信息。
@app.post("/getScenes")
async def get_scenes(request: Request):
    # 当前使用固定房间和用户；多人同时使用时应改成动态生成。
    room_id = "ChatRoom01"
    user_id = "Huoshan01"

    # 签发 RTC Token
    token_builder = AccessToken(
        settings.RTC_APP_ID, settings.RTC_APP_KEY, room_id, user_id
    )
    token_builder.add_privilege(PRIVILEGES["PrivSubscribeStream"], 0)
    token_builder.add_privilege(PRIVILEGES["PrivPublishStream"], 0)
    token_builder.expire_time(int(time.time()) + 3600 * 24)
    token = token_builder.serialize()

    # 构造返回结构
    return {
        "ResponseMetadata": {"Action": "getScenes"},
        "Result": {
            "scenes": [
                {
                    "scene": {
                        # --- 补全的核心字段 ---
                        "id": "Custom",  # 建议改为 Custom，通常前端会根据这个 ID 做特殊处理
                        "name": "自定义助手",
                        "botName": "AiAgent",
                        "icon": "https://lf3-rtc-demo.volccdn.com/obj/rtc-aigc-assets/DoubaoAvatar.png",  # 补全图标
                        # --- 功能开关 ---
                        "isInterruptMode": True,  # 是否支持打断
                        "isVision": False,  # 补全：是否开启视觉（摄像头）
                        "isScreenMode": False,  # 补全：是否开启屏幕共享
                        # --- 数字人相关 (无数字人时设为 None/null) ---
                        "isAvatarScene": None,
                        "avatarBgUrl": None,
                    },
                    "rtc": {
                        "AppId": settings.RTC_APP_ID,
                        "RoomId": room_id,
                        "UserId": user_id,
                        "Token": "0016a8fc05f323a0a017e85f3dbSQApphEA6/mTams0nWoKAENoYXRSb29tMDEJAEh1b3NoYW4wMQYAAABrNJ1qAQBrNJ1qAgBrNJ1qAwBrNJ1qBABrNJ1qBQBrNJ1qIAARXdqviUUQnnt4EnXSzntVyeLie70VWIebVkyntlOEcg==",
                    },
                    # 这里的配置主要是为了兼容前端透传，实际生效主要看 proxy
                    "VoiceChat": {},
                }
            ]
        },
    }


# ==================== 模块 3：RTC 启停控制 ====================
# 接收前端的 StartVoiceChat / StopVoiceChat，并代理调用火山引擎 RTC OpenAPI。
# main.py 核心修改
# rag_llm_server/main.py


@app.post("/proxy")
async def proxy(request: Request):
    """
    完全硬编码的代理接口，用于测试链路是否畅通
    """
    # Action 决定本次是启动、停止，还是其他 RTC 操作。
    action = request.query_params.get("Action")
    version = request.query_params.get("Version", "2024-12-01")

    # 打印前端实际传过来的数据，方便观察
    try:
        incoming_body = await request.json()
        print(f"DEBUG: 收到前端请求 {action}, Body: {incoming_body}")
    except:
        pass

    # --- 开始硬编码数据 ---
    # 注意：这里的 AppId, RoomId, UserId, Token 必须与你提供的 JSON 完全一致
    target_app_id = "6a8fc05f323a0a017e85f3db"
    target_room_id = "ChatRoom01"
    target_user_id = "Huoshan01"

    request_body = {}

    print(f"RTCCCCC  callback {settings.SERVER_URL}/api/chat_callback")
    if action == "StartVoiceChat":
        # 启动时下发 ASR、TTS 和自定义大模型回调配置。
        request_body = {
            "AppId": target_app_id,
            "RoomId": target_room_id,
            "TaskId": "ChatTask01",
            "AgentConfig": {
                "TargetUserId": [target_user_id],
                "WelcomeMessage": "你好，我是语音助手。你想了解什么？",
                "UserId": "AiAgent",
                "EnableConversationStateCallback": True, 
            },
            "Config": {
                "ASRConfig": {
                    "Provider": "volcano",
                    "ProviderParams": {
                        "Mode": "smallmodel",
                        "AppId": "8952847754",
                        "Cluster": "volcengine_streaming_common",
                    },
                },
                "TTSConfig": {
                    "Provider": "volcano",
                    "ProviderParams": {
                        "app": {"appid": "8952847754", "cluster": "volcano_tts"},
                        "audio": {
                            "voice_type": "BV001_streaming",
                            "speed_ratio": 1,
                            "pitch_ratio": 1,
                            "volume_ratio": 1,
                        },
                    },
                },
                "LLMConfig": {
                    # 先用 Custom 模式测试你的回调地址
                    "Mode": "CustomLLM",    #这表示不让 RTC 直接调用它内置的大模型，而是调用你提供的接口。
                    "Url": f"{settings.SERVER_URL}/api/chat_callback",  #不能只写 ngrok 域名，因为 ngrok 域名只代表你的后端服务器，没有说明具体要调用哪个接口。
                    "Method": "POST",
                    "ApiType": "https"
                    if str(settings.SERVER_URL).startswith("https")
                    else "http",
                },
                "InterruptMode": 0,
            },
        }
    elif action == "StopVoiceChat":
        # 停止时使用相同的 AppId、RoomId 和 TaskId 结束当前任务。
        request_body = {
            "AppId": target_app_id,
            "RoomId": target_room_id,
            "TaskId": "ChatTask01",
        }
    else:
        # 其他 Action 直接返回前端传的内容
        request_body = incoming_body

    # --- 签名与发送 ---
    host = "rtc.volcengineapi.com"
    open_api_request_data = {
        "method": "POST",
        "path": "/",
        "params": {"Action": action, "Version": version},
        "headers": {"Host": host, "Content-Type": "application/json"},
        "body": request_body,
    }

    # 这里的 AK/SK 必须拥有调用 RTC OpenAPI 的权限
    account_config = {"accessKeyId": settings.VOLC_AK, "secretKey": settings.VOLC_SK}

    signer = Signer(open_api_request_data, "rtc")
    signer.add_authorization(account_config)

    url = f"https://{host}?Action={action}&Version={version}"

    # print(f"DEBUG: 发送请求到 {url} callback rtc")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers=open_api_request_data["headers"],
            json=request_body,
            timeout=30.0,
        )
        result = resp.json()
        print(f"DEBUG: 火山引擎返回结果: {result}")
        return result


# ==================== 模块 4：AI 对话回调（核心链路） ====================
# RTC 将语音识别后的用户消息发送到这里；本接口执行 RAG 检索和大模型生成。


# ... 其他代码 ...


@app.post("/api/chat_callback")   #当有人使用 POST 请求访问 /api/chat_callback 时，执行下面的 chat_callback()
async def chat_callback(request: Request): #当接口收到请求时，FastAPI 会自动创建一个 Request 对象，并把它传给你定义的 request 参数
    try:      #先尝试执行一段可能失败的代码；如果失败，不让整个接口崩溃，而是执行备用处理。
        data = await request.json()    
    except:
        return {"text": ""}   #返回空内容，避免程序崩溃。

    print(f"======================== 流式请求", data)

    messages = data.get("messages", [])  #如果请求里没有 messages，就使用空列表 []

    # 校验逻辑 (保持不变)
    if not messages or messages[-1].get("role") != "user":
        print("⚠️ 忽略：非用户主动发言")
        return {"text": ""}    #检查最后一条是不是用户问题

    # --- 定义 SSE 生成器 ---
    async def generate_sse():
        # 1. 调用 LLM 的流式方法
        # 注意：这里是同步生成器还是异步取决于 SDK，Ark SDK 默认是同步 iterator，
        # 但在 FastAPI 的 async def 中，通常可以直接遍历

        # 第一步：用用户最新问题检索知识库，获得可供模型参考的上下文。
        rag_content = await rag_service.retrieve(messages[-1].get("content", ""))

        # 第二步：把对话历史和知识库上下文交给大模型，获取流式结果。
        stream_iterator = llm_service.chat_stream(messages, rag_content)

        for chunk in stream_iterator:
            if chunk:
                # Ark SDK 的 chunk 是一个对象 (ChatCompletionChunk)
                # 我们直接用 model_dump_json() 把它转成 JSON 字符串
                # 这完全符合 RTC 要求的 OpenAI 兼容格式
                chunk_json = chunk.model_dump_json()

                # 2. 构造 SSE 协议格式： "data: {json数据}\n\n"
                yield f"data: {chunk_json}\n\n"

        # 3. 循环结束后，必须发送结束符 (RTC 要求的)
        yield "data: [DONE]\n\n"

    # --- 返回流式响应 ---
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",  # <--- 必须是这个 Header
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # 如果存在跨域问题，可以加上 Access-Control-Allow-Origin
            "Access-Control-Allow-Origin": "*",
        },
    )


from typing import List, Optional


# ==================== 模块 5：调试接口 ====================
# 以下数据模型只用于 /debug/chat，方便不经过 RTC 直接测试对话链路。
class ChatMessage(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str


class DebugRequest(BaseModel):
    history: Optional[List[ChatMessage]] = []
    question: str


# 调试完整链路：用户问题 -> RAG 检索 -> 大模型流式回答。
@app.post("/debug/chat")
async def debug_chat(request: DebugRequest):


    # 构造当前发送给 LLM 的消息列表
    current_messages = []
    for msg in request.history:
        current_messages.append({"role": msg.role, "content": msg.content})

    # 放入用户最新问题
    current_messages.append({"role": "user", "content": request.question})

    async def generate_text():
        full_ai_response = ""
        total_usage = None

            # 1. 记录总开始时间
        start_t = time.time()
        # 查询知识库
        rag_content = await rag_service.retrieve(request.question)

        rag_duration = time.time() - start_t

        print(f"DEBUG: 知识库查询耗时: {rag_duration:.2f}s")
        # print(f"DEBUG: 知识库返回检索内容: {rag_content}")

        # 2. 记录 LLM 调用开始时间
        llm_start_t = time.time()

        # 调用 llm_service
        stream = llm_service.chat_stream(current_messages, rag_content)

        for chunk in stream:
            if chunk and chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    content = delta.content
                    full_ai_response += content  # 累积 AI 的回答
                    yield content
            # 记录 Token 消耗
            if hasattr(chunk, "usage") and chunk.usage:
                total_usage = chunk.usage

        # 3. 记录 LLM 调用耗时
        llm_duration = time.time() - llm_start_t
        print(f"DEBUG: LLM 调用耗时: {llm_duration:.2f}s")

        if total_usage:
            print(
                f"🎫 Token 统计: Total={total_usage.total_tokens} (P:{total_usage.prompt_tokens}, C:{total_usage.completion_tokens})"
            )

        # --- 重点：在流结束后构造并打印 history 结构 ---
        # 构造完整的 history 列表
        new_history = []
        # 添加旧历史
        for m in request.history:
            new_history.append({"role": m.role, "content": m.content})
        # 添加最新的一轮对话
        new_history.append({"role": "user", "content": request.question})
        new_history.append({"role": "assistant", "content": full_ai_response})

        # 打印到控制台，方便你直接复制
        print("\n" + "=" * 50)
        print("🐞 调试完成！以下是可用于下次请求的 history 结构：")
        print(json.dumps({"history": new_history}, ensure_ascii=False, indent=2))
        print("=" * 50 + "\n")

    return StreamingResponse(generate_text(), media_type="text/plain")


# ... 其他导入保持不变 ...
from services.rag_service import rag_service  # 确保已导入 rag_service


# 只调试 RAG 检索，不调用大模型，适合排查“知识库是否召回内容”。
@app.get("/debug/rag")
async def debug_rag(query: str):
    """
    调试接口：直接返回知识库检索到的原始文本内容
    用法：浏览器访问 http://127.0.0.1:8000/debug/rag?query=你的问题
    """
    if not query:
        return {"error": "请提供 query 参数"}

    print(f"🔍 [Debug] 正在检索知识库: {query}")

    # 调用我们在 rag_service.py 中实现的异步 retrieve 方法
    context = await rag_service.retrieve(query)

    return {
        "query": query,
        "retrieved_context": context,
        "length": len(context) if context else 0,
        "status": "success" if context else "no_results_or_error",
    }






# ==================== 模块 6：程序启动入口 ====================
# 直接执行 `python main.py` 时，在 3001 端口启动开发服务器。
if __name__ == "__main__":
    import uvicorn

    print(f"🚀 Server running at {settings.SERVER_URL}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3001,
        reload=True,
        reload_dirs=[".", "services"],
        # 依然建议排除缓存文件，防止编译行为触发重启
        reload_excludes=[
            "*/__pycache__/*",
            "*.pyc",
            ".venv/*",  # 排除根目录下的虚拟环境
            "*/.venv/*",
        ],
    )
