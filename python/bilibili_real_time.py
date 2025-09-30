import asyncio
import logging
import argparse
from datetime import datetime
from bilibili_api import video
import requests

## 配置日志
logging.basicConfig(
    level=logging.INFO,  ## 日志级别
    format='%(asctime)s - %(levelname)s - %(message)s',  ## 日志格式
    handlers=[
        logging.FileHandler("video_monitor.log"),  ## 日志文件
        logging.StreamHandler()  ## 控制台输出
    ]
)

## 飞书 Webhook URL
FEISHU_WEBHOOK_URL = '<https://open.feishu.cn/open-apis/bot/>'  ## 输入飞书 Bot url

## 设置命令行参数
parser = argparse.ArgumentParser(description='Monitor Bilibili video.')
parser.add_argument('bv_id', type=str, help='The BV ID of the video to monitor.')
args = parser.parse_args()

async def fetch_video_data(bvid: str) -> None:
    ## 实例化 Video 类
    v = video.Video(bvid=bvid)  ## 使用传入的 BV 号
    ## 获取信息
    info = await v.get_info()

    ## 获取视频发布时间
    pub_time_str = info['pubdate']  
    pub_time = datetime.fromtimestamp(pub_time_str)  

    ## 计算当前时间和视频发布时间的差值
    now = datetime.now()
    time_diff = now - pub_time

    ## 获取统计信息
    name = info['owner']['name']
    views = info['stat']['view']
    likes = info['stat']['like']
    replies = info['stat']['reply']
    coins = info['stat']['coin']
    favorites = info['stat']['favorite']
    shares = info['stat']['share']
    danmaku_count = info['stat']['danmaku']

    ## 计算互动总数、互动占比和投币占比
    interaction_total = likes + replies + coins + favorites + shares + danmaku_count
    interaction_ratio = (interaction_total / views) * 100 if views > 0 else 0  ## 避免除以零
    coin_ratio = (coins / interaction_total) * 100 if interaction_total > 0 else 0  ## 避免除以零

    ## 构建飞书卡片消息格式
    card_message = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{info['owner']['name']} | {info['title']}"  ## 修改消息头
                },
                "template": "orange"  ## 设置标题主题颜色
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"[该视频](<https://www.bilibili.com/video/{bvid}>)距今已发布 {time_diff.days} 天 {time_diff.seconds // 3600} 小时，当前 B 站播放量为 **{views / 10000:.1f} 万**，\\n\\n互动总数为 **{interaction_total / 10000:.1f} 万**，互动占比为 **{interaction_ratio:.2f}%**，投币占比为 **{coin_ratio:.2f}%**。\\n\\n详细数据 👉 播放量: {views}  互动总数: {interaction_total} 点赞数: {likes}  评论数: {replies}  投币数: {coins}  收藏数: {favorites}  转发数: {shares}  弹幕数: {danmaku_count}"
                    }
                }
            ]
        }
    }

    ## 发送消息到飞书
    await send_to_feishu(card_message)

async def send_to_feishu(data):
    requests.post(FEISHU_WEBHOOK_URL, json=data)

## 主函数
async def main():
    await fetch_video_data(args.bv_id)  ## 使用命令行参数中的 BV ID

## 执行主函数
if __name__ == "__main__":
    asyncio.run(main())