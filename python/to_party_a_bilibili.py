import os
import sys
import re
import pandas as pd
import traceback
from datetime import datetime
import urllib3
import yt_dlp
import requests
import json
import logging

## 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

## 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def format_youtube_date(date_str):
    try:
        if date_str and len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        return date_str
    except Exception as e:
        print(f"日期格式转换错误: {e}")
        return date_str

def format_weibo_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        return date_obj.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"微博日期格式转换错误: {e}")
        return date_str

def get_video_info(video_url):
    ydl_opts = {
        'quiet': True,
        'format': 'best',
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            title = info_dict.get('title', 'N/A')
            upload_date = format_youtube_date(info_dict.get('upload_date', 'N/A'))
            view_count = info_dict.get('view_count', 0)
            like_count = info_dict.get('like_count', 0)
            comment_count = info_dict.get('comment_count', 0) or 0

            return [
                'YouTube',
                title, 
                video_url, 
                upload_date, 
                str(view_count), 
                str(like_count), 
                str(comment_count)
            ]
    except Exception as e:
        print(f"获取YouTube视频信息失败: {e}")
        return None

def convert_play_count(play_count_str):
    """
    将微博播放量文字转换为数值
    例如：
    '10万次播放' -> 100000
    '2千次播放' -> 2000
    '892次播放' -> 892
    """
    if not play_count_str:
        return 0
    
    play_count_str = str(play_count_str).replace('次播放', '').replace(' ', '')
    
    multipliers = {
        '万': 10000,
        '千': 1000,
    }
    
    for unit, multiplier in multipliers.items():
        if unit in play_count_str:
            try:
                number = float(play_count_str.replace(unit, ''))
                return int(number * multiplier)
            except ValueError:
                return 0
    
    try:
        return int(play_count_str)
    except ValueError:
        return 0

def get_single_weibo(weibo_id, headers=None):
    """获取指定ID的单条微博信息"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'
        }
    
    try:
        url = f"<https://m.weibo.cn/detail/{weibo_id}>"
        response = requests.get(url, headers=headers, verify=False)
        html = response.text
        html = html[html.find('"status":'):]
        html = html[:html.rfind('"call"')]
        html = html[:html.rfind(",")]
        html = "{" + html + "}"
        js = json.loads(html, strict=False)
        weibo_info = js.get("status")
        
        if weibo_info:
            ## 获取播放量
            play_count = 0
            if weibo_info.get("page_info"):
                page_info = weibo_info["page_info"]
                if page_info.get("type") == "video":
                    play_count_str = page_info.get("play_count", "0")
                    play_count = convert_play_count(play_count_str)
            
            ## 格式化返回数据，与原有输出列保持一致
            weibo = {
                '平台': '微博',
                '标题': weibo_info['text'],
                '链接': f"<https://weibo.com/{weibo_info['user']['id']}/{weibo_info['bid']}>",
                '发布时间': format_weibo_date(weibo_info['created_at']),
                '播放量': str(play_count),
                '点赞': str(weibo_info['attitudes_count']),
                '评论': str(weibo_info['comments_count']),
                '转发': str(weibo_info['reposts_count'])
            }
            
            return list(weibo.values())
            
        return None
    
    except Exception as e:
        logger.error(f"获取微博信息出错: {e}")
        return None

def extract_platform_name(filename):
    match = re.search(r'^([^\\-]+)', filename)
    return match.group(1) if match else filename

def match_column(df, target_columns):
    for col in df.columns:
        for target in target_columns.split('/'):
            if target in str(col):
                return col
    return None

def process_files(search_keyword, input_dir=None, sub_folder=None):
    ## 如果没有提供输入目录，使用默认路径
    if input_dir is None:
        today = datetime.now().strftime("%Y-%m-%d")
        input_dir = os.path.join('G:\\\\zdh\\\\platformdata', today)
        if sub_folder:
            input_dir = os.path.join(input_dir, sub_folder)
    
    ## 平台处理顺序
    platform_order = ['bilibili', '抖音', '小红书', '公众号', '视频号', '快手', '头条号']
    
    ## 输出列及其可能的列名
    output_columns = {
        '平台': '',
        '标题': '作品/标题/描述',
        '链接': '链接/url',
        '发布时间': '发布时间/发表时间',
        '播放量': '播放量/观看量/总阅读次数',
        '点赞': '点赞/喜欢',
        '评论': '评论',
        '转发': '转发/转发次数/分享',
        '收藏': '收藏'
    }
    
    ## 输出目录和文件名
    output_dir = 'G:\\\\zdh\\\\to_party_a'
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f'output_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
    output_file_path = os.path.join(output_dir, output_filename)
    
    ## 获取所有输入文件，按指定顺序排序
    input_files = [
        os.path.join(input_dir, f) 
        for f in os.listdir(input_dir)
        if f.endswith(('.csv', '.xlsx', '.xls', '.et')) 
        and not f.startswith('~$') 
        and not f.startswith('.')
    ]
    
    ## 按平台顺序排序
    input_files.sort(key=lambda x: next((i for i, p in enumerate(platform_order) if p in os.path.basename(x)), len(platform_order)))
    
    ## 初始化输出行
    output_rows = [list(output_columns.keys())]
    
    for file_path in input_files:
        filename = os.path.basename(file_path)
        platform = extract_platform_name(filename)
        print(f"\\n正在处理文件: {filename}")
        
        try:
            ## 读取文件
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            elif file_path.endswith('.xls'):
                df = pd.read_excel(file_path, engine='xlrd')
            else:
                if '小红书' in filename:
                    df = pd.read_excel(file_path, header=1)
                else:
                    df = pd.read_excel(file_path, engine='openpyxl')
            
            print(f"文件列名: {list(df.columns)}")
            print(f"文件行数: {len(df)}")
            
            ## 在第一列中搜索关键词
            matched_rows = df[df.iloc[:, 0].astype(str).str.contains(search_keyword, case=False, na=False)]
            
            if not matched_rows.empty:
                print(f"找到 {len(matched_rows)} 行匹配数据")
                
                for _, row in matched_rows.iterrows():
                    ## 创建新行
                    new_row = [platform]
                    
                    ## 匹配其他列
                    for col_name, possible_names in list(output_columns.items())[1:]:
                        if possible_names:
                            matched_col = match_column(df, possible_names)
                            value = row[matched_col] if matched_col else ''
                            new_row.append(str(value))
                        else:
                            new_row.append('')
                    
                    output_rows.append(new_row)
            else:
                print(f"文件 {filename} 未找到匹配项")
        
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")
            traceback.print_exc()
    
    ## 询问微博和 YouTube 链接
    print("\\n请输入微博链接（以空格分隔，没有则直接回车）:")
    weibo_links = input().split()
    
    for link in weibo_links:
        weibo_id = link.split('/')[-1]
        weibo_data = get_single_weibo(weibo_id)
        if weibo_data:
            output_rows.append(weibo_data)
    
    print("\\n请输入 YouTube 链接（以空格分隔，没有则直接回车）:")
    youtube_links = input().split()
    
    for link in youtube_links:
        youtube_data = get_video_info(link)
        if youtube_data:
            output_rows.append(youtube_data)
    
    ## 保存输出文件
    output_df = pd.DataFrame(output_rows[1:], columns=output_rows[0])
    output_df.to_excel(output_file_path, index=False)
    print(f"\\n匹配结果已保存到: {output_file_path}")

## 主程序入口
if __name__ == '__main__':
    ## 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python 脚本.py <搜索关键词> [子文件夹]")
        sys.exit(1)
    
    ## 获取命令行参数
    search_keyword = sys.argv[1]
    sub_folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    ## 调用处理函数
    process_files(search_keyword, sub_folder=sub_folder)