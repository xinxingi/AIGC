from dotenv import load_dotenv
from langchain_core.callbacks import StreamingStdOutCallbackHandler
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.outputs import LLMResult
from typing import Any, Dict, List
from datetime import datetime
from langchain_openai import ChatOpenAI


class PlanVisualizerCallback(BaseCallbackHandler):
    """
    "黑盒" -> "透明盒"
    """

    def __init__(self):
        self.step_count = 0
        self.plan_steps = []

    # LLM 开始调用时
    def on_llm_start(
            self,
            serialized: Dict[str, Any],
            prompts: List[str],
            **kwargs: Any
    ) -> None:
        print("on_llm_start 开始")
        print("执行计划 - LLM 调用\n")
        print(f"时间: {datetime.now().strftime('%H:%M:%S')}")
        print(f"提示词: {prompts[0][:100]}...")
        print("on_llm_start 结束\n")
        self.plan_steps.append({"type": "LLM调用", "prompt": prompts[0][:50]})

    # LLM 结束时
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        print("on_llm_end 开始")
        output = response.generations[0][0].text
        print(f"LLM 响应: {output[:100]}...")
        print("on_llm_end 结束\n")
    # Chain 开始时
    def on_chain_start(
            self,
            serialized: Dict[str, Any],
            inputs: Dict[str, Any],
            **kwargs: Any
    ) -> None:
        chain_name = serialized.get('name', serialized.get('id', ['未知链'])[-1])
        print(f"\nChain 开始: {chain_name}")
        print(f"输入: {inputs}")

    # Chain 结束时
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        print(f"\nChain 完成")
        print(f"   输出: {str(outputs)[:100]}...")

    # 显示完整执行计划
    def show_plan_summary(self):
        print("\n" + "=" * 50)
        print("执行计划总结")
        print("=" * 50)
        for i, step in enumerate(self.plan_steps, 1):
            print(f"{i}. {step}")

def test_default_callback():
    """测试 1: 使用默认回调（无输出）"""
    llm = ChatOpenAI(model="gpt-5-nano-2025-08-07",temperature=0,callbacks=[StreamingStdOutCallbackHandler()])

    print(f"Callback参数: {llm.callbacks}")

    question = "如何提升自制力？请给出100字的建议。"

    # 不传入任何 callback
    response = llm.invoke(question)

    print(f"\n回答:\n{response.content}\n")

def test_custom_callback():
    """测试 2: 使用自定义回调"""
    llm = ChatOpenAI(model="gpt-5-nano-2025-08-07",temperature=0.5,callbacks=[PlanVisualizerCallback()])

    print(f"Callback参数: {llm.callbacks}")

    question = "如何提升自制力？请给出100字的建议。"

    response = llm.invoke(question)

    print(f"\n回答:\n{response.content}\n")

if __name__ == "__main__":
    load_dotenv()
    test_default_callback()
    print("\n" + "=" * 50 + "\n")
    test_custom_callback()