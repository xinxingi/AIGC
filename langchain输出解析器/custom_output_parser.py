from dotenv import load_dotenv
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import List

load_dotenv()

class CustomTaskParser(BaseOutputParser):
    """自定义输出解析器"""
    def parse(self, text: str) -> List[dict]:
        """
        解析文本，提取任务信息
        格式：任务名 - 开始时间 - 截止时间 - 优先级
        """
        tasks = []

        lines = text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 按分隔符拆分
            parts = line.split(' - ')

            # 确保有4个部分
            if len(parts) == 4:
                task = {
                    '任务名': parts[0].strip(),
                    '开始时间': parts[1].strip(),
                    '截止时间': parts[2].strip(),
                    '优先级': parts[3].strip()
                }
                tasks.append(task)

        return tasks

    def get_format_instructions(self) -> str:
        """返回格式说明"""
        return """每个任务一行，使用以下格式：
任务名 - 开始时间 - 截止时间 - 优先级

例如：
学习K线基础知识 - 2025-11-22 - 2025-11-30 - 高
开设证券账户 - 2025-11-23 - 2025-11-25 - 高
"""

    @property
    def _type(self) -> str:
        return "custom_task_parser"


# 使用示例
if __name__ == "__main__":
    # 创建解析器实例
    parser = CustomTaskParser()

    prompt = PromptTemplate(
        template="""
为以下项目需求创建任务计划：
    
项目：{project_description}

请用以下格式列出任务：
{format_instructions}
""",
        input_variables=["project_description"],
        partial_variables={"format_instructions": parser.get_format_instructions()}

    )

    llm = ChatOpenAI(model="gpt-5-nano-2025-08-07", temperature=0)

    chain = prompt | llm | parser

    # 执行链
    project_desc = "在股市里赚钱，学习打板，龙头股短线操作，争取每个月赚到100000元。"
    result = chain.invoke({"project_description": project_desc})

    print(f"\n项目描述：{project_desc}")
    print(f"\nLLM生成并解析后的任务（共 {len(result)} 个）：")

    for i, task in enumerate(result, 1):
        print(f"\n任务 {i}:")
        for key, value in task.items():
            print(f"  {key}: {value}")
