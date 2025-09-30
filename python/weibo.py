#!/usr/bin/env python
## -*- coding: utf-8 -*-

import argparse
import requests
import json
from datetime import datetime
import logging
import urllib3

## 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
            ## 提取基本信息
            weibo = {
                'id': weibo_info['id'],
                'screen_name': weibo_info['user']['screen_name'],
                'text': weibo_info['text'],
                'attitudes_count': weibo_info['attitudes_count'],
                'comments_count': weibo_info['comments_count'],
                'reposts_count': weibo_info['reposts_count'],
                'created_at': weibo_info['created_at']
            }
            
            ## 获取视频信息
            if weibo_info.get("page_info"):
                page_info = weibo_info["page_info"]
                if page_info.get("type") == "video":
                    weibo['play_count'] = page_info.get("play_count", "0")
                    weibo['video_title'] = page_info.get("title", "")
            
            return weibo
            
        return None
            
    except Exception as e:
        logger.error(f"获取微博信息出错: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='获取微博数据并输出到命令行')
    parser.add_argument('--id', type=str, required=True, help='微博ID')
    args = parser.parse_args()
    
    weibo_info = get_single_weibo(args.id)
    if weibo_info:
        ## 输出微博信息到命令行
        print(f"用户: {weibo_info['screen_name']}")
        print(f"创建时间: {weibo_info['created_at']}")
        print(f"内容: {weibo_info['text']}")
        print(f"点赞数: {weibo_info['attitudes_count']}")
        print(f"评论数: {weibo_info['comments_count']}")
        print(f"转发数: {weibo_info['reposts_count']}")
        if 'play_count' in weibo_info:
            print(f"播放量: {weibo_info['play_count']}")
            print(f"视频标题: {weibo_info['video_title']}")
    else:
        logger.error("获取微博信息失败")

if __name__ == "__main__":
    main()