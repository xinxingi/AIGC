import json

import pandas
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

import os

categories = {"文学小说", "青春文学", "亲子育儿", "科普读物", "动漫幽默", "人文社科", "艺术收藏", "古籍地理", "旅游休闲", "生活时尚", "经济管理", "励志成长", "外语学习", "法律哲学", "政治军事", "自然科学", "家庭教育", "两性关系", "孕产育儿", "家居生活"}
# 初始化客户端
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_api(text, model_name="kimi-latest"):
    system_prompt = f"你是一个准确的文本分类助手。请根据提供的类别列表:{categories}，将文本分类为其中一个类别。返回类别名称 + 简洁标注理由。使用 json 格式返回结果，例如：{{\"category\": \"文学小说\", \"reason\": \"文本内容涉及文学创作和小说情节。\"}}。如果文本不符合任何类别，category为\"其他\"，reason为\"文本内容不符合任何预定义类别。\"。"
    response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.0,
                max_tokens= 300,
            )
    return response.choices[0].message.content.strip()


def classify_data():
    df = pandas.read_excel('/Users/star/PycharmProjects/AIGC/四组数据打标/数据标注.xlsx', engine='openpyxl')

    for idx, value in enumerate(df['数据'].values):
        response = call_api(value)  # 调用 API
        print(f"API Response for index {idx}: {response}")  # 添加调试打印

        try:
            json_str = json.loads(response)
            category = json_str['category']
            reason = json_str['reason']

            # 写入分类和原因到对应的列
            df.at[idx, '二组的标注分类'] = category
            df.at[idx, '二组的标注原因'] = reason
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError for index {idx}: {e}")

    # 保存更新后的数据到新的 Excel 文件
    df.to_excel('/Users/star/PycharmProjects/AIGC/四组数据打标/数据标注_更新.xlsx', index=False)
if __name__ == "__main__":
    classify_data()