import os
from volcenginesdkarkruntime import Ark 
from config import settings

class LLMService:
    def __init__(self):
        api_key = settings.ARK_API_KEY 
        self.client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",    
            api_key=api_key, 
            timeout=1800, 

        )

    def chat_stream(self, history_messages: list, rag_context: str = ""):
        """
        流式对话
        :param history_messages: 对话历史
        :param rag_context: 从 rag_service 检索出来的背景知识
        """
        if not self.client:
            yield "服务配置错误"
            return

        system_content = "你是一个问答助手。请用简短、清楚的中文回答。资料不足时，说明还需要哪些信息。"
        if rag_context.strip():
            system_content += f"\n\n参考资料：\n{rag_context.strip()}"
        messages = [{"role": "system", "content": system_content}]
        messages.extend(history_messages)

        try:
            print(f"🚀 发起流式调用 (Endpoint: {settings.ARK_ENDPOINT_ID})")
            
            stream = self.client.chat.completions.create(
                model=settings.ARK_ENDPOINT_ID,
                messages=messages,
                temperature=0.3, # 降低随机性，确保回答更严谨地贴合 RAG
                stream=True,
                stream_options={"include_usage": True},
            )

            for chunk in stream:
                yield chunk

        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            yield None

llm_service = LLMService()