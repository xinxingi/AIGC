import pandas as pd
import json

def group_by_category_and_type(df):
    grouped = df.groupby(['学科门类']).size().reset_index(name='专业数量')
    return grouped['学科门类'].to_json(orient='records', force_ascii=False)

def group_by_category_and_type_nested(df):
    result = []
    for category, group in df.groupby('学科门类'):
        type_counts = group.groupby('专业类').size().reset_index(name='专业数量')
        types = [
            {
                '专业类': row['专业类'],
                '专业数量': int(row['专业数量'])
            }
            for _, row in type_counts.iterrows()
        ]
        result.append({
            '学科门类': category,
            '专业类数量': len(types),
            '专业类列表': types
        })
    return result

def main():
    df = pd.read_csv('2025年本科专业目录.csv',
                     dtype={
                         '学科门类代码': str,
                         '学科门类': str,
                         '专业类代码': str,
                         '专业类': str,
                         '专业代码': str,
                         '专业名称': str,
                         '是否特设专业': str,
                         '是否国家控制布点专业': str,
                         '特殊标识': str,
                         '学位授予说明': str,
                     })
    # result = group_by_category_and_type_nested(df)
    # print(json.dumps(result, ensure_ascii=False, indent=2))

    print(group_by_category_and_type(df))

if __name__ == '__main__':
    main()