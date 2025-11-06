# 简易的多模型 API 调用示例（中文注释）
# 支持两类风格：
# 1) 统一 OpenAI 风格（messages + stream）
# 2) 各厂商自定义风格（prompt / instances / Claude 特殊字段）
#
# 使用时替换 API_URL、API_KEY、MODEL 等占位符。

import json
import requests
from typing import Generator, Iterable, Dict, Any, Optional


def send_openai_style(api_url: str, api_key: str, model: str, messages: Iterable[Dict[str, str]],
                      stream: bool = False, timeout: int = 60) -> Any:
    """OpenAI 风格的调用（可用于兼容 OpenAI 协议的厂商）
    非流式返回完整 JSON，流式按行 yield 原始行（SSE 或 chunked）。
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": list(messages), "stream": stream}
    r = requests.post(api_url, json=payload, headers=headers, stream=stream, timeout=timeout)
    r.raise_for_status()
    if not stream:
        return r.json()
    else:
        # 处理 SSE 或 chunked JSON（非常简化）
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            # 许多实现会返回以 "data: " 开头的 SSE 行
            line = raw
            if line.startswith("data: "):
                line = line[len("data: "):]
            if line.strip() == "[DONE]":
                break
            try:
                yield json.loads(line)
            except Exception:
                yield line


def send_prompt_style(api_url: str, api_key: str, prompt: str, max_tokens: int = 512,
                      stream: bool = False, timeout: int = 60, api_key_header: str = "Authorization") -> Any:
    """厂商使用 prompt / input 字段的简单示范
    api_key_header 可按厂商设置为 "Authorization" 或 "x-api-key" 等
    """
    headers = {api_key_header: f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "max_tokens": max_tokens, "stream": stream}
    r = requests.post(api_url, json=payload, headers=headers, stream=stream, timeout=timeout)
    r.raise_for_status()
    if not stream:
        return r.json()
    else:
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw
            if line.startswith("data: "):
                line = line[len("data: "):]
            if line.strip() == "[DONE]":
                break
            try:
                yield json.loads(line)
            except Exception:
                yield line


def send_instances_style(api_url: str, api_key: str, instances: Iterable[Any], parameters: Optional[Dict[str, Any]] = None,
                         stream: bool = False, timeout: int = 60) -> Any:
    """某些 ML 平台使用 instances/inputs 数组的调用格式
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"instances": list(instances)}
    if parameters:
        payload["parameters"] = parameters
    payload["stream"] = stream
    r = requests.post(api_url, json=payload, headers=headers, stream=stream, timeout=timeout)
    r.raise_for_status()
    if not stream:
        return r.json()
    else:
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw
            if line.startswith("data: "):
                line = line[len("data: "):]
            if line.strip() == "[DONE]":
                break
            try:
                yield json.loads(line)
            except Exception:
                yield line


def send_anthropic(api_url: str, api_key: str, prompt: str, max_tokens: int = 300,
                   stream: bool = False, timeout: int = 60) -> Any:
    """Anthropic/Claude 风格的示例（注意 header 与字段名称可能不同）
    - 认证头常见为 x-api-key 或 Authorization
    - 字段：prompt, model, max_tokens_to_sample 等
    """
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    payload = {"prompt": prompt, "max_tokens_to_sample": max_tokens, "stream": stream}
    r = requests.post(api_url, json=payload, headers=headers, stream=stream, timeout=timeout)
    r.raise_for_status()
    if not stream:
        return r.json()
    else:
        # Claude 的流式常为 text/event-stream，每个 event 也可能是 JSON
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw
            if line.startswith("data: "):
                line = line[len("data: "):]
            if line.strip() == "[DONE]":
                break
            try:
                yield json.loads(line)
            except Exception:
                yield line


def call_model(api_url: str, api_key: str, model: str, *,
               messages: Optional[Iterable[Dict[str, str]]] = None,
               prompt: Optional[str] = None,
               instances: Optional[Iterable[Any]] = None,
               parameters: Optional[Dict[str, Any]] = None,
               stream: bool = False, timeout: int = 60) -> Any:
    """统一适配器：根据 model 名选择常见的请求风格并调用对应函数。

    规则（可按需修改）：
    - 如果传入 messages 则优先用 OpenAI 风格
    - model 包含 'claude' 或 'anthropic' 则使用 Anthropic 风格
    - model 包含 'ds' 则使用 instances 风格
    - 其他默认使用 OpenAI 风格（如 glm4.6、qwen3 等厂商若兼容 OpenAI 协议）

    返回值：非流式返回 dict，流式返回 generator
    """
    model_l = model.lower()
    # 优先 messages
    if messages is not None:
        return send_openai_style(api_url, api_key, model, messages, stream=stream, timeout=timeout)

    # Anthropic / Claude
    if 'claude' in model_l or 'anthropic' in model_l:
        if prompt is None:
            raise ValueError('Anthropic/Claude 风格需要提供 prompt')
        return send_anthropic(api_url, api_key, prompt, max_tokens=(parameters or {}).get('max_tokens', 300),
                              stream=stream, timeout=timeout)

    # DS 类平台（instances）
    if model_l.startswith('ds') or model_l.startswith('ds-'):
        if instances is None:
            # 如果没有 instances，则尝试用 prompt 包装为单元素 instances
            if prompt is None:
                raise ValueError('DS 类平台需要提供 instances 或 prompt')
            instances = [ {'input': prompt} ]
        return send_instances_style(api_url, api_key, instances, parameters=parameters, stream=stream, timeout=timeout)

    # 其他厂商，优先尝试 prompt 风格（如果没有 messages）
    if prompt is not None:
        return send_prompt_style(api_url, api_key, prompt, max_tokens=(parameters or {}).get('max_tokens', 512),
                                 stream=stream, timeout=timeout)

    # 最后兜底：尝试 OpenAI 风格但需要 messages
    raise ValueError('缺少必要参数：请提供 messages 或 prompt 或 instances')


# 简短使用说明（示例）
# 1) OpenAI 风格（messages）
# resp = call_model(API_URL, API_KEY, 'glm4.6', messages=[{'role':'user','content':'你好'}], stream=False)
# 2) Claude/Anthropic
# resp = call_model(CLAUDE_API_URL, CLAUDE_KEY, 'claude-2', prompt='人类: 你好\n助手:', stream=False)
# 3) DS 平台（instances）
# resp = call_model(DS_API_URL, DS_KEY, 'ds-v3', prompt='请翻译: Hello', stream=False)

# 需要我为某个模型生成可直接运行的示例吗？例如：
# - GLM4.6（给出具体 endpoint & key）
# - Qwen3
# - DS V3 / R1
# - Claude（Anthropic）


# 简单示例（注释掉，实际使用时替换占位符）
if __name__ == "__main__":
    #OpenAI 风格示例（非流）
    resp = send_openai_style(API_URL := "https://api.example.com/v1/chat/completions",
                             API_KEY := "YOUR_KEY",
                             model := "glm4.6",
                             messages := [{"role": "user", "content": "请总结以下内容..."}],
                             stream=False)
    print(resp)

    #Prompt 风格示例（非流）
    resp = send_prompt_style("https://api.example.com/v1/generate", "YOUR_KEY", "Translate to Chinese: ...")
    print(resp)
