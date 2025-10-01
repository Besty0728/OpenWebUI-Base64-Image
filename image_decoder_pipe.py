"""
title: OpenWebUI-Base图片解码器
id: image_decoder_pipe
author: Besty0728
author_url: https://github.com/Besty0728
git_url: https://github.com/Besty0728/OpenWebUI-Base64-Image/blob/main/image_decoder_pipe.py
description:一个专门用于处理返回Base64编码图像的API模型的Pipe。
version: 0.1.0
license: Apache2.0
"""

import aiohttp
import json
from typing import AsyncGenerator, Dict, Any, List
from pydantic import BaseModel, Field  # <-- 拼写已修正

AIOHTTP_SESSION = None


async def get_aiohttp_session() -> aiohttp.ClientSession:
    global AIOHTTP_SESSION
    if AIOHTTP_SESSION is None or AIOHTTP_SESSION.closed:
        AIOHTTP_SESSION = aiohttp.ClientSession()
    return AIOHTTP_SESSION


class Pipe:
    """
    OpenWebUI Pipe:图像生成器
    """

    type: str = "manifold"
    id: str = "final_correct_pipe"

    class Valves(BaseModel):
        API_BASE_URL: str = Field(
            default="https://generativelanguage.googleapis.com/v1beta",
            title="API 基础 URL",
        )
        API_KEY: str = Field(default="", title="API Key", extra={"type": "password"})
        MODEL_ID: str = Field(default="gemini-2.5-flash-image-preview", title="模型 ID")
        COST_PER_IMAGE: float = Field(default=0.1, title="每次生成费用 (元)")
        REQUEST_TIMEOUT: int = Field(default=300, title="请求超时时间 (秒)")

    def __init__(self):
        self.valves = self.Valves()

    async def pipes(self) -> List[Dict[str, str]]:
        if not self.valves.MODEL_ID:
            return []
        display_name = f"最终计费图像模型: {self.valves.MODEL_ID}"
        return [{"id": self.valves.MODEL_ID, "name": display_name}]

    async def pipe(
        self, body: dict, __user__: dict, **kwargs: Any
    ) -> AsyncGenerator[str, None]:

        try:
            target_base_url, api_key, model_id, timeout = (
                self.valves.API_BASE_URL,
                self.valves.API_KEY,
                self.valves.MODEL_ID,
                self.valves.REQUEST_TIMEOUT,
            )

            full_api_url = f"{target_base_url.strip('/')}/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            # 仅保留最后一个用户提示
            original_messages = body.get("messages", [])
            last_user_message = next(
                (
                    msg
                    for msg in reversed(original_messages)
                    if msg.get("role") == "user"
                ),
                None,
            )
            messages_to_send = [last_user_message] if last_user_message else []

            payload = {
                "model": model_id,
                "messages": messages_to_send,
                "stream": False,
                **{
                    k: v
                    for k, v in body.items()
                    if k not in ["model", "messages", "stream"]
                },
            }

            yield "⏳ 任务已提交，正在生成图片..."

            session = await get_aiohttp_session()
            async with session.post(
                full_api_url, headers=headers, json=payload, timeout=timeout
            ) as response:
                raw_response_text = await response.text()
                if response.status >= 400:
                    yield f"API请求失败：{response.status}\n{raw_response_text}"
                    return

                result_json = json.loads(raw_response_text)

            content_str = result_json["choices"][0]["message"]["content"]
            cost = self.valves.COST_PER_IMAGE
            cost_string = f"本次生成消耗{cost:.4f}元"
            final_output = f"{content_str}\n\n{cost_string}"

            yield final_output

            # 使用一个空的 'return' 来正确结束生成器
            return

        except Exception as e:
            import traceback

            yield f"发生未知错误: {e}\n{traceback.format_exc()}"
