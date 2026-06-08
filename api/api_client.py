import time
from openai import OpenAI
from typing import Dict, List, Optional

class APIClient:

    def __init__(
        self,
        api_url: str,
        api_key: str,
        judge_model: str = "deepseek-v3.2",
        plaintiff_model: str = "qwen3-32b",
        defendant_model: str = "qwen3-32b",
        summary_model: str = "qwen3-32b",
        embedding_model: str = "text-embedding-v4",
        judge_enable_thinking: Optional[bool] = None,
        plaintiff_enable_thinking: Optional[bool] = None,
        defendant_enable_thinking: Optional[bool] = None,
        summary_enable_thinking: Optional[bool] = None,
        judge_stream: Optional[bool] = None,
        plaintiff_stream: Optional[bool] = None,
        defendant_stream: Optional[bool] = None,
        summary_stream: Optional[bool] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        judge_base_url: Optional[str] = None,
        plaintiff_base_url: Optional[str] = None,
        defendant_base_url: Optional[str] = None,
        summary_base_url: Optional[str] = None,
        embedding_base_url: Optional[str] = None,
        judge_api_key: Optional[str] = None,
        plaintiff_api_key: Optional[str] = None,
        defendant_api_key: Optional[str] = None,
        summary_api_key: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
    ):

        self.default_api_url = api_url
        self.default_api_key = api_key
        self.role_models = {
            "judge": judge_model,
            "plaintiff": plaintiff_model,
            "defendant": defendant_model,
        }
        self.summary_model = summary_model
        self.embedding_model = embedding_model
        self.role_enable_thinking = {
            "judge": judge_enable_thinking,
            "plaintiff": plaintiff_enable_thinking,
            "defendant": defendant_enable_thinking,
        }
        self.summary_enable_thinking = summary_enable_thinking
        self.role_stream = {
            "judge": judge_stream,
            "plaintiff": plaintiff_stream,
            "defendant": defendant_stream,
        }
        self.summary_stream = summary_stream
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.role_base_urls = {
            "judge": judge_base_url,
            "plaintiff": plaintiff_base_url,
            "defendant": defendant_base_url,
        }
        self.summary_base_url = summary_base_url
        self.embedding_base_url = embedding_base_url
        self.role_api_keys = {
            "judge": judge_api_key,
            "plaintiff": plaintiff_api_key,
            "defendant": defendant_api_key,
        }
        self.summary_api_key = summary_api_key
        self.embedding_api_key = embedding_api_key
        self._client_cache: Dict[tuple[str, str], OpenAI] = {}

    def _get_client(self, api_url: str, api_key: str) -> OpenAI:

        cache_key = (api_url, api_key)
        client = self._client_cache.get(cache_key)
        if client is None:
            client = OpenAI(api_key=api_key, base_url=api_url)
            self._client_cache[cache_key] = client
        return client

    def _get_role_client(self, role: str) -> OpenAI:

        api_url = self.role_base_urls.get(role) or self.default_api_url
        api_key = self.role_api_keys.get(role) or self.default_api_key
        return self._get_client(api_url, api_key)

    def _get_summary_client(self) -> OpenAI:

        api_url = self.summary_base_url or self.default_api_url
        api_key = self.summary_api_key or self.default_api_key
        return self._get_client(api_url, api_key)

    def _get_embedding_client(self) -> OpenAI:

        api_url = self.embedding_base_url or self.default_api_url
        api_key = self.embedding_api_key or self.default_api_key
        return self._get_client(api_url, api_key)

    def _call_chat_model(
        self,
        client: OpenAI,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        enable_thinking: Optional[bool] = None,
        use_stream: Optional[bool] = None,
    ) -> str:

        request_kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        if enable_thinking is not None:
            request_kwargs["extra_body"] = {"enable_thinking": enable_thinking}
        if use_stream:
            request_kwargs["stream"] = True

        last_error = None
        total_attempts = self.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                response = client.chat.completions.create(**request_kwargs)

                if use_stream:
                    answer_content = ""
                    for chunk in response:
                        if not chunk.choices:
                            continue

                        delta = chunk.choices[0].delta
                        content = getattr(delta, "content", None)
                        if content is not None:
                            answer_content += content

                    return answer_content.strip()

                return (response.choices[0].message.content or "").strip()
            except Exception as e:
                last_error = e
                if attempt >= total_attempts:
                    break
                print(
                    f"API调用失败，准备重试 {attempt}/{self.max_retries}，"
                    f"{self.retry_delay} 秒后再次尝试: {e}"
                )
                time.sleep(self.retry_delay)

        raise last_error

    def call_role(self, role: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:

        model = self.role_models.get(role)
        if model is None:
            raise ValueError(f"未知角色: {role}")
        enable_thinking = self.role_enable_thinking.get(role)
        use_stream = self.role_stream.get(role)
        client = self._get_role_client(role)

        try:
            return self._call_chat_model(
                client,
                model,
                messages,
                temperature,
                enable_thinking=enable_thinking,
                use_stream=use_stream,
            )
        except Exception as e:
            print(f"调用{role}模型({model})时出错: {e}")
            raise

    def call_qwen(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:

        return self.call_summary(messages, temperature)

    def call_deepseek(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:

        return self.call_role("judge", messages, temperature)

    def call_summary(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:

        client = self._get_summary_client()
        try:
            return self._call_chat_model(
                client,
                self.summary_model,
                messages,
                temperature,
                enable_thinking=self.summary_enable_thinking,
                use_stream=self.summary_stream,
            )
        except Exception as e:
            print(f"调用总结模型({self.summary_model})时出错: {e}")
            raise

    def get_embedding(self, text: str) -> List[float]:

        last_error = None
        total_attempts = self.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                client = self._get_embedding_client()
                response = client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                last_error = e
                if attempt >= total_attempts:
                    print(f"获取embedding时出错(模型: {self.embedding_model}): {e}")
                    break
                print(
                    f"获取embedding失败，准备重试 {attempt}/{self.max_retries}，"
                    f"{self.retry_delay} 秒后再次尝试: {e}"
                )
                time.sleep(self.retry_delay)

        raise last_error
