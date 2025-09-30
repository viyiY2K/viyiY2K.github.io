import os
import pandas as pd
import glob
from datetime import datetime

def process_files(search_keyword, input_dir=None, sub_folder=None):
    ## 输出路径和文件名
    output_dir = r'G:\\zdh\\data'
    os.makedirs(output_dir, exist_ok=True)  ## 确保目录存在

    ## 如果没有提供输入目录，使用默认路径
    if input_dir is None:
        today = datetime.now().strftime("%Y-%m-%d")
        input_dir = os.path.join('G:\\\\zdh\\\\platformdata', today)
        if sub_folder:
            input_dir = os.path.join(input_dir, sub_folder)

    ## 输出文件
    output_file = os.path.join(output_dir, f'Douyin_Daily.xlsx')
    
    ## 创建或读取输出文件
    try:
        df_output = pd.read_excel(output_file)
    except FileNotFoundError:
        ## 如果文件不存在，创建一个带有预定义列的空DataFrame
        columns = [
            '作品名称', '发布时间', '体裁', '审核状态', '播放量', '完播率', '5s完播率', 
            '封面点击率', '2s跳出率', '平均播放时长', '点赞量', '分享量', '评论量', 
            '收藏量', '主页访问量', '粉丝增量', 
            '小红书-观看量', '小红书-点赞', '小红书-涨粉',
            '快手-播放量', '快手-点赞量', '快手-涨粉量',
            '视频号-播放量', 
            'bilibili2-播放量', 'bilibili2-涨粉量'
        ]
        df_output = pd.DataFrame(columns=columns)

    ## 按顺序处理不同平台文件
    platforms = [
        {'name': '抖音', 'filename': '*抖音*.xlsx', 'search_column': 0, 'header': 0, 'data_columns': [
            '作品名称', '发布时间', '体裁', '审核状态', '播放量', '完播率', '5s完播率', 
            '封面点击率', '2s跳出率', '平均播放时长', '点赞量', '分享量', '评论量', 
            '收藏量', '主页访问量', '粉丝增量'
        ]},
        {'name': '小红书', 'filename': '*小红书*.xlsx', 'search_column': 0, 'header': 1, 'data_columns': [
            {'column': '小红书-观看量', 'source_column': '观看量'},
            {'column': '小红书-点赞', 'source_column': '点赞'},
            {'column': '小红书-涨粉', 'source_column': '涨粉'}
        ]},
        {'name': '快手', 'filename': '*快手*.xlsx', 'search_column': 0, 'header': 0, 'data_columns': [
            {'column': '快手-播放量', 'source_column': '播放量'},
            {'column': '快手-点赞量', 'source_column': '点赞量'},
            {'column': '快手-涨粉量', 'source_column': '涨粉量'}
        ]},
        {'name': '视频号', 'filename': ['*视频号*.csv', '*视频号*.xlsx'], 'search_column': 0, 'header': 0, 'data_columns': [
            {'column': '视频号-播放量', 'source_column': '播放量'}
        ]},
        {'name': 'bilibili2', 'filename': ['*bilibili2*.csv', '*bilibili*.xlsx'], 'search_column': 0, 'header': 0, 'data_columns': [
            {'column': 'bilibili2-播放量', 'source_column': '播放量'},
            {'column': 'bilibili2-涨粉量', 'source_column': '涨粉量'}
        ]}
    ]

    ## 创建一个新的空行用于存储数据
    new_row = pd.DataFrame(columns=df_output.columns)

    for platform in platforms:
        ## 处理可能的多个文件名模式
        filenames = platform['filename'] if isinstance(platform['filename'], list) else [platform['filename']]
        
        matched_file = None
        for filename in filenames:
            search_pattern = os.path.join(input_dir, filename)
            files = [f for f in glob.glob(search_pattern) if not os.path.basename(f).startswith('~$')]
            
            if files:
                matched_file = files[0]
                break
        
        if matched_file:
            try:
                ## 根据文件类型读取
                if matched_file.endswith('.xlsx'):
                    df = pd.read_excel(matched_file, header=platform['header'])
                elif matched_file.endswith('.csv'):
                    df = pd.read_csv(matched_file, encoding='utf-8', header=platform['header'])
            except Exception as e:
                print(f"读取文件 {matched_file} 时发生错误：{e}")
                continue
            
            ## 搜索关键词
            try:
                matched_rows = df[df.iloc[:, platform['search_column']].str.contains(search_keyword, na=False)]
            except:
                matched_rows = df[df.apply(lambda row: row.astype(str).str.contains(search_keyword).any(), axis=1)]
            
            if not matched_rows.empty:
                row = matched_rows.iloc[0]
                
                ## 根据平台特定列名提取数据
                for col_info in platform['data_columns']:
                    if isinstance(col_info, dict):
                        source_column = col_info['source_column']
                        if source_column in df.columns:
                            new_row.loc[0, col_info['column']] = row[source_column]
                    else:
                        if col_info in df.columns:
                            col_index = df.columns.get_loc(col_info)
                            new_row.loc[0, col_info] = row.iloc[col_index]

    ## 如果找到了数据，添加到输出DataFrame
    if not new_row.empty and not new_row.loc[0].isnull().all():
        df_output = pd.concat([df_output, new_row], ignore_index=True)

    ## 保存结果
    df_output.to_excel(output_file, index=False)
    print(f"数据处理完成，结果已保存到 {output_file}")
    return df_output

## 使用示例
if __name__ == "__main__":
    keyword = input("请输入要检索的关键词：")
    result = process_files(keyword)
    print(result)
