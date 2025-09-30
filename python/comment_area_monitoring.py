from bilibili_api import comment, Credential
import asyncio
import json
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import logging
import argparse

## 配置日志
def setup_logging(bvid):
    log_dir = os.path.join(r'G:\\zdh\\data\\comments', bvid)
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'bilibili_comment_crawler.log')
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s: %(message)s',
        filename=log_file,
        filemode='a'
    )

## 定义时间记录文件路径
def get_last_run_file(bvid):
    return os.path.join(r'G:\\zdh\\data\\comments', bvid, 'last_run_time.txt')

def read_last_run_time(bvid):
    """读取上次运行时间"""
    last_run_file = get_last_run_file(bvid)
    if os.path.exists(last_run_file):
        with open(last_run_file, 'r') as f:
            lines = f.readlines()
            ## 如果文件不为空，返回最后一行的时间戳
            return int(lines[-1].split()[0]) if lines else 0
    return 0  ## 如果文件不存在，返回0表示获取所有评论

def write_last_run_time(bvid, timestamp):
    """写入本次运行时间"""
    last_run_file = get_last_run_file(bvid)
    ## 转换时间戳为可读格式
    readable_time = datetime.fromtimestamp(timestamp).strftime('%Y/%m/%d %H:%M')
    
    with open(last_run_file, 'a') as f:
        ## 写入时间戳和可读时间
        f.write(f"{timestamp} ## {readable_time}\\n")

def flatten_comment(comment, bvid):
    """展平单个评论"""
    try:
        rpid = comment.get("rpid", 0)
        flattened_comment = {
            "uname": comment["member"]["uname"],
            "message": comment["content"]["message"],
            "like": comment.get("like", 0),
            "ctime": comment["ctime"],
            "ip_location": comment.get('reply_control', {}).get('location', '未知'),
            "rpid": rpid,
            "comment_url": f"<https://www.bilibili.com/video/{bvid}/#reply{rpid}>"
        }
        return flattened_comment
    except Exception as e:
        logging.error(f"解析评论时出错: {e}")
        return None

def extract_comments(comments, bvid, last_run_time):
    """
    递归提取评论，仅保留指定时间后的评论
    
    :param comments: 评论列表
    :param bvid: 视频ID
    :param last_run_time: 上次运行的时间戳
    :return: 过滤后的评论列表
    """
    all_comments = []
    for comment in comments:
        ## 检查评论时间是否在上次运行之后
        if comment["ctime"] > last_run_time:
            flattened = flatten_comment(comment, bvid)
            if flattened:
                all_comments.append(flattened)
        
        ## 递归处理子评论
        if "replies" in comment and comment["replies"]:
            ## 递归时传入 last_run_time
            child_comments = extract_comments(comment["replies"], bvid, last_run_time)
            all_comments.extend(child_comments)
    
    return all_comments

async def get_new_comments(bvid, last_run_time):
    """获取视频的新评论"""
    comments = []
    page = 1
    
    while True:
        try:
            c = await comment.get_comments(
                bvid, 
                comment.CommentResourceType.VIDEO, 
                page,
                credential=credential
            )
            
            replies = c.get('replies', [])
            if not replies:
                break
            
            ## 检查当前页是否还有新的评论
            new_comments = [r for r in replies if r["ctime"] > last_run_time]
            comments.extend(new_comments)
            
            ## 如果没有新评论或已经到最后一页，退出
            if not new_comments or page > c['page']['count'] // c['page']['size'] + 1:
                break
            
            page += 1
        
        except Exception as e:
            logging.error(f"获取评论时出错: {e}")
            break
    
    return comments

def append_to_excel(new_df, bvid):
    """
    追加新数据到现有Excel文件
    如果文件不存在，则创建新文件
    """
    filename = os.path.join(r'G:\\zdh\\data\\comments', bvid, f'{bvid}_comments.xlsx')
    
    try:
        ## 如果文件存在，读取现有数据
        if os.path.exists(filename):
            existing_df = pd.read_excel(filename)
            
            ## 去重
            combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['rpid'])
            combined_df.to_excel(filename, index=False)
        else:
            ## 如果文件不存在，直接保存
            new_df.to_excel(filename, index=False)
        
        logging.info(f"数据已成功保存到 {filename}")
    except Exception as e:
        logging.error(f"保存Excel文件时出错: {e}")

async def main(bvid):
    ## 设置日志
    setup_logging(bvid)
    
    try:
        ## 读取上次运行时间
        last_run_time = read_last_run_time(bvid)
        logging.info(f"上次运行时间: {last_run_time}")
        
        ## 获取新评论
        new_video_comments = await get_new_comments(bvid, last_run_time)
        
        ## 展平并提取新评论
        flattened_comments = extract_comments(new_video_comments, bvid, last_run_time)
        
        ## 打印总新评论数
        logging.info(f"共获取到 {len(flattened_comments)} 条新评论")
        
        ## 筛选包含关键词的评论
        filtered_comments = [
            comment for comment in flattened_comments 
            if any(keyword in comment['message'] for keyword in FILTER_KEYWORDS)
        ]
        
        ## 记录关键词评论
        logging.info(f"包含关键词的评论共 {len(filtered_comments)} 条")
        
        ## 转换为 DataFrame
        df = pd.DataFrame(flattened_comments)
        
        ## 导出到 xlsx 文件，使用追加模式
        append_to_excel(df, bvid)
        
        ## 记录本次运行时间
        current_timestamp = int(datetime.now().timestamp())
        write_last_run_time(bvid, current_timestamp)
        logging.info(f"本次运行时间已记录: {current_timestamp}")
        
    except Exception as e:
        logging.error(f"脚本执行出错: {e}", exc_info=True)

## 添加依赖检查
try:
    import bilibili_api
    import pandas as pd
except ImportError as e:
    print(f"缺少必要依赖: {e}")
    print("请运行 pip install bilibili-api-python pandas openpyxl")
    sys.exit(1)

if __name__ == "__main__":
    ## 设置命令行参数解析
    parser = argparse.ArgumentParser(description='bilibili评论爬取脚本')
    parser.add_argument('bvid', help='要爬取评论的视频BV号')
    
    ## 解析参数
    args = parser.parse_args()
    
    ## 实例化 Credential
    credential = Credential(
        sessdata="your_sessdata",
        bili_jct="your_bili_jct",
        buvid3="your_buvid3",
        dedeuserid="your_dedeuserid",
        ac_time_value="your_ac_time_value"
    )

    ## 定义关键词列表
    FILTER_KEYWORDS = ['恰饭', '恰', '广告', '推广', '剪辑', '调色', '字幕']

    ## 运行主程序
    asyncio.run(main(args.bvid))