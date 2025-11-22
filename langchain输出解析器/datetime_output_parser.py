from dotenv import load_dotenv
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from datetime import datetime as DateTime

# 加载环境变量
load_dotenv()

# 定义日期时间模型
class DateTimeResponse(BaseModel):
    datetime: DateTime = Field(description="解析出的日期时间")
    description: str = Field(description="对日期时间的描述")

# 初始化模型
model = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)

# 创建日期时间输出解析器
output_parser = PydanticOutputParser(pydantic_object=DateTimeResponse)


# 创建提示模板
prompt = PromptTemplate(
    template="""
    回答用户的问题:
    {question}

    {format_instructions}
    """,
    input_variables=["question","format_instructions"],
)

# 创建 LCEL 链
chain = prompt | model | output_parser

# # 查看生成的完整提示
# formatted_prompt = prompt.invoke({"question": "中华人民共和国成立于哪一年?","format_instructions": output_parser.get_format_instructions()})
# print("=== 发送给AI的完整请求 ===")
# print(formatted_prompt.text)
# print("=" * 50)

result = chain.invoke({"question": "中华人民共和国成立于哪一年?","format_instructions": output_parser.get_format_instructions()})
print(f"结果类型: {type(result)}")
print(f"日期时间: {result.datetime}")
print(f"描述: {result.description}")


