"""
version: 0.1.0
description: 一个专门用于处理返回Base64编码图像的API模型的Pipe。
"""

import aiohttp
import json
import base64
from typing import AsyncGenerator, Dict, Any, List
from pydantic import BaseModel, Field

# 全局管理 aiohttp.ClientSession 以复用连接池
AIOHTTP_SESSION = None

async def get_aiohttp_session() -> aiohttp.ClientSession:
    """获取或创建全局 aiohttp 客户端会话。"""
    global AIOHTTP_SESSION
    if AIOHTTP_SESSION is None or AIOHTTP_SESSION.closed:
        AIOHTTP_SESSION = aiohttp.ClientSession()
    return AIOHTTP_SESSION


class Pipe:
    """
    OpenWebUI Pipe: Base64 图像解码器

    这个Pipe会调用一个指定的API端点。它期望API返回一个JSON对象，
    该对象中包含了Base64编码的图像数据。Pipe会自动寻找、解码
    这个数据，并将其格式化为Data URL，以便在前端直接显示为图片。
    """

    type: str = "manifold"
    id: str = "image_decoder_pipe"

    class Valves(BaseModel):
        """
        这些是此Pipe的配置项，可以在OpenWebUI的管理员后台进行设置。
        """
        API_URL: str = Field(
            default="https://manager.ai0728.com.cn/api/v1/inlet",
            title="图像模型 API URL",
            description="您的图像生成模型的API端点地址。",
        )
        API_KEY: str = Field(
            default="",
            title="API Key (可选)",
            description="如果您的API需要认证，请在此处填入API密钥。",
            extra={"type": "password"},
        )
        MODEL_ID: str = Field(
            default="gemini-2.5-flash-image-preview",
            title="模型 ID",
            description="要调用的具体模型ID。",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.name = f"图像解码器: {self.valves.MODEL_ID}"

    async def pipes(self) -> List[Dict[str, str]]:
        """
        动态注册在Valves中配置的模型。
        """
        if not self.valves.MODEL_ID:
            return []
        
        # 美化模型在前端下拉菜单中的显示名称
        display_name = f"图像模型: {self.valves.MODEL_ID.split('/')[-1]}"
        return [{"id": self.valves.MODEL_ID, "name": display_name}]

    def _find_base64_in_response(self, data: Any) -> str | None:
        """
        在JSON响应中递归地、智能地查找Base64字符串。
        这使得Pipe对不同的API响应结构具有更好的适应性。
        """
        if isinstance(data, dict):
            for key, value in data.items():
                # 优先查找常见的关键字
                if isinstance(value, str) and ("b64" in key or "base64" in key or "image" in key):
                    # 简单验证一下长度，排除空字符串或简短的元数据
                    if len(value) > 100:
                        return value
                
                # 递归深入查找
                found = self._find_base64_in_response(value)
                if found:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_base64_in_response(item)
                if found:
                    return found
        return None

    async def pipe(
        self, body: dict, __user__: dict, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        
        # 1. 从后台配置中获取必要的参数
        api_url = self.valves.API_URL
        api_key = self.valves.API_KEY
        model_id = self.valves.MODEL_ID

        if not all([api_url, model_id]):
            yield "错误：Pipe配置不完整。请在管理员后台设置 'API_URL' 和 'MODEL_ID'。"
            return

        # 2. 准备请求头和请求体
        headers = { "Content-Type": "application/json" }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # 参照 demo.txt 构建请求体，同时保持与OpenWebUI的兼容性
        payload = {
            "model": model_id,
            "messages": body.get("messages", []),
            "stream": body.get("stream", False), # 即使是图片，API也可能支持非流式
            **body  # 将OpenWebUI传来的其他参数（如temperature等）也一并传入
        }

        try:
            # 3. 发送异步HTTP POST请求
            session = await get_aiohttp_session()
            async with session.post(api_url, headers=headers, json=payload) as response:
                response.raise_for_status() # 如果状态码是 4xx 或 5xx，将直接抛出异常
                result_json = await response.json()

            # 4. 在响应中寻找Base64数据
            base64_data = self._find_base64_in_response(result_json)

            if base64_data:
                # 5. 成功找到，格式化为Data URL并返回
                # OpenWebUI前端可以识别这种格式并直接渲染成图片
                yield f"data:image/png;base64,{base64_data}"
            else:
                # 6. 未找到，返回错误信息并打印整个响应体，方便调试
                yield "错误：API成功返回，但在JSON响应中未能找到有效的Base64图像数据。"
                print("--- [Image Decoder Pipe] DEBUG: UNABLE TO FIND BASE64 ---")
                print(json.dumps(result_json, indent=2, ensure_ascii=False))
                print("---------------------------------------------------------")

        except aiohttp.ClientResponseError as e:
            error_body = await e.response.text()
            yield f"API请求失败：{e.status} {e.message}\n服务器响应：\n{error_body}"
        except json.JSONDecodeError:
            raw_text = await response.text()
            yield f"错误：无法将API响应解析为JSON。收到的原始文本：'{raw_text[:500]}...'"
        except Exception as e:
            import traceback
            yield f"发生未知错误: {e}\n{traceback.format_exc()}"