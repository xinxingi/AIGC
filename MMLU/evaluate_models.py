import pandas as pd
from openai import OpenAI
import time
from typing import List
import os
from tqdm import tqdm

from dotenv import load_dotenv
load_dotenv()

# 初始化客户端
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 模型列表
MODEL_NAMES = ["gpt-3.5-turbo","gpt-4.1-nano"]


def parse_choices(choices_str: str) -> List[str]:
    """解析选项字符串"""
    try:
        choices = eval(choices_str)
        return choices
    except:
        return []


def format_question(question: str, choices: List[str]) -> str:
    """格式化问题（用户提示词）"""
    prompt = f"""问题：{question}

选项：
A. {choices[0]}
B. {choices[1]}
C. {choices[2]}
D. {choices[3]}

请回答选项字母（A、B、C、D）"""
    return prompt


def call_api_zero_shot(prompt: str, model_name: str, max_retries: int = 1) -> str:
    """调用API - Zero Shot模式"""
    system_prompt = "你是一个准确的选择题答题助手。请直接回答选项字母，不需要解释。"
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=10
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return ""
    return ""


def call_api_zero_shot_cot(prompt: str, model_name: str, max_retries: int = 1) -> str:
    """调用API - Zero Shot CoT模式"""
    system_prompt = "你是一个准确的选择题答题助手。请先进行逐步推理分析，然后给出最终答案。请按以下格式回答：\n推理过程：[你的分析]\n最终答案：[A/B/C/D]"
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return ""
    return ""


def extract_answer(response: str) -> str:
    """提取答案字母"""
    response = response.strip().upper()
    for char in ['A', 'B', 'C', 'D']:
        if char in response:
            return char
    return ""


def extract_answer_and_process(response: str) -> tuple:
    """从CoT响应中提取答案和推理过程"""
    # 提取推理过程
    process = ""
    answer = ""
    
    if "推理过程" in response and "最终答案" in response:
        parts = response.split("最终答案")
        process = parts[0].replace("推理过程", "").replace("：", "").replace(":", "").strip()
        answer_part = parts[1]
        answer = extract_answer(answer_part)
    else:
        # 如果格式不标准，整个作为process，尝试提取答案
        process = response
        answer = extract_answer(response)
    
    return answer, process


def main():
    """主函数"""
    # 数据集路径
    csv_path = "/home/star/PycharmProjects/AIGC/MMLU/dataset/extracted_data/chinese-test-00000-of-00001.csv"
    
    # 检查API密钥
    if not os.getenv('OPENAI_API_KEY'):
        print("警告: 未设置OPENAI_API_KEY环境变量")
        print("请设置环境变量或在代码中手动设置API密钥")
        return
    
    # 读取数据
    print(f"读取数据集: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"共 {len(df)} 条数据")
    
    # 是否使用样本进行测试
    SAMPLE_SIZE = None  # 设置为 None 使用全部数据，或设置为数字进行测试
    if SAMPLE_SIZE:
        df = df.head(SAMPLE_SIZE)
        print(f"使用前 {SAMPLE_SIZE} 条数据进行测试")
    
    # 准备结果列表
    results = []
    
    print(f"\n开始处理，使用模型: {MODEL_NAMES}")
    print("="*60)
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="处理中"):
        question = row['question']
        subject = row['subject']
        choices_str = row['choices']
        answer = row['answer']
        
        choices = parse_choices(choices_str)
        if len(choices) != 4:
            print(f"警告: 第 {idx} 行选项数量不是4，跳过")
            continue
        
        # 生成提示词
        prompt = format_question(question, choices)
        
        # 对每个模型进行测试
        for model_name in MODEL_NAMES:
            print(f"\n处理问题 {idx+1}，模型: {model_name}")
            
            # 1. Zero Shot 调用
            zero_shot_response = call_api_zero_shot(prompt, model_name)
            zero_shot_answer = extract_answer(zero_shot_response)
            time.sleep(0.5)  # 避免请求过快
            
            # 2. Zero Shot CoT 调用
            cot_response = call_api_zero_shot_cot(prompt, model_name)
            cot_answer, cot_process = extract_answer_and_process(cot_response)
            time.sleep(0.5)  # 避免请求过快
            
            # 记录结果
            results.append({
                'question': question,
                'subject': subject,
                'choices': choices_str,
                'answer': answer,
                'model_name': model_name,
                '0-zero-answer': zero_shot_answer,
                '0-zero-cot-answer': cot_answer,
                '0-zero-cot-process': cot_process
            })
    
    # 保存结果
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    
    results_df = pd.DataFrame(results)
    output_path = os.path.join(output_dir, 'combined_results.csv')
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\n{'='*60}")
    print(f"处理完成！")
    print(f"共处理 {len(results)} 条数据")
    print(f"结果已保存至: {output_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
