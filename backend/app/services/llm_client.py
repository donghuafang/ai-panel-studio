import os
import json
import httpx
from app.config import settings

SYSTEM_PROMPT_GENERATE_GUESTS = """你是一个圆桌讨论的策划者。用户会提供一个讨论话题和需要的专家人数，请你设计一个AI嘉宾阵容。

要求：
1. 生成 1 位主持人 + N 位专家嘉宾（N = 用户指定的人数）
2. 主持人：立场中立，擅长引导讨论，名字、职业、头衔、立场描述合理
3. 专家嘉宾：从不同角度/立场切入话题，每位专家的立场应当各有侧重、形成观点的碰撞
4. 为每位嘉宾分配一个专属的十六进制颜色码（HEX），主持人用沉稳色（如 #4A90D9），专家用鲜明区分色

返回严格的 JSON 格式（不要包含 markdown 代码块标记）：
{
  "guests": [
    {
      "name": "张三",
      "profession": "软件工程师",
      "title": "资深全栈开发者",
      "stance": "认为 AI 将大幅提升编程效率，但不会完全替代程序员...",
      "color": "#FF6B6B",
      "role": "guest"
    }
  ]
}

注意：第一条为主持人（role="host"），其余为专家（role="guest"）。"""


class LLMClient:
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        self.model = "deepseek-chat"  # Deepseek V4 Pro
        # Mock mode if env var set OR no API key configured
        self.mock_mode = (
            os.environ.get("MOCK_LLM", "").lower() == "true"
            or not self.api_key  # 没有 API key 时自动进入 mock 模式
        )

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat_completion(
        self, messages: list[dict], temperature: float = 0.8
    ) -> str:
        """发送聊天补全请求，返回 assistant 文本回复"""
        if self.mock_mode:
            from app.services.mock_llm_responses import mock_chat_completion
            return mock_chat_completion(messages, temperature)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def generate_guests(self, topic: str, expert_count: int) -> list[dict]:
        """生成 1 位主持人 + N 位专家"""
        if self.mock_mode:
            from app.services.mock_llm_responses import mock_generate_guests
            return mock_generate_guests(topic, expert_count)

        user_message = f"讨论话题：{topic}\n专家人数：{expert_count}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_GENERATE_GUESTS},
            {"role": "user", "content": user_message},
        ]
        raw = await self.chat_completion(messages, temperature=0.9)
        # 清洗可能的 markdown 代码块标记
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)
        result = json.loads(raw)
        return result["guests"]

    async def generate_speech(
        self,
        guest_name: str,
        guest_stance: str,
        role: str,
        discussion_context: list[dict],
        speech_purpose: str,
    ) -> str:
        """为指定嘉宾生成发言内容"""
        if self.mock_mode:
            from app.services.mock_llm_responses import mock_generate_speech
            return mock_generate_speech(
                guest_name, guest_stance, role, discussion_context, speech_purpose
            )

        system_prompt = f"""你正在参加一场AI圆桌讨论。你的身份是：

姓名：{guest_name}
角色：{"主持人" if role == "host" else "专家嘉宾"}
立场：{guest_stance}

发言要求：{speech_purpose}

请以第一人称发言，语气自然、专业，像真实圆桌讨论中的发言。发言长度控制在 150-400 字之间。"""

        messages = [{"role": "system", "content": system_prompt}]
        # 追加讨论上下文（最近 20 条消息以控制 token）
        messages.extend(discussion_context[-20:])

        return await self.chat_completion(messages, temperature=0.8)
