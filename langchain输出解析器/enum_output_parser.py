from dotenv import load_dotenv
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from enum import Enum

load_dotenv()

class Sentiment(Enum):
    HIGH_CONFIDENCE = "高置信度"
    MEDIUM_CONFIDENCE = "中等置信度"
    LOW_CONFIDENCE = "低置信度"

class SentimentAnalysis(BaseModel):
    sentiment: Sentiment = Field(description="请分析以下文本的置信度")

parser = PydanticOutputParser(pydantic_object=SentimentAnalysis)

llm = ChatOpenAI(temperature=0, model="gpt-5-nano-2025-08-07")

template = """
请分析以下文本的置信度：{text}

{format_instructions}

请根据文本内容选择最合适的置信度等级。
"""

prompt = PromptTemplate(
    template=template,
    input_variables=["text"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

chain = prompt | llm | parser

# 测试
texts = [
    "今天股市大涨，沪指突破6000点，老曹赚麻了",
    "根据最新财报，公司今年净利润增长15%",
    "学习是为了自己，而不是为了别人",
]

for text in texts:
    result = chain.invoke({"text": text})
    print(f"文本: {text}")
    print(f"置信度:Key:{result.sentiment}, Value:{result.sentiment.value}")
    print("-" * 50)