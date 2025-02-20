import os
import sys
import glob
import time
import datetime
import argparse
from pathlib import Path

from uploader.bilibili_uploader.main import read_cookie_json_file, extract_keys_from_json, random_emoji, BilibiliUploader
from conf import BASE_DIR
from utils.constant import VideoZoneTypes
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags

def wait_for_doing_file(video_path):
    """
    循环检测指定目录下doing.txt文件是否存在，如果存在则等待。

    Args:
        video_path (str): 视频文件所在的绝对路径。
    """
    doing_file_path = os.path.join(video_path, 'doing.txt') # doing.txt 文件路径，在指定的 video_path 目录下

    while True: # 无限循环，持续检测文件
        if os.path.exists(doing_file_path): # 检查doing.txt文件是否存在
            print(f"发现 {doing_file_path} 文件，等待5分钟...") # 打印等待信息
            time.sleep(5 * 60) # 睡眠5分钟 (5 * 60 秒)
        else:
            break # doing.txt 文件不存在，跳出循环


def get_mp4_files(video_path):
    """
    获取指定目录下所有的mp4文件，并按文件名排序。

    Args:
        video_path (str): 视频文件所在的绝对路径。

    Returns:
        list: 排序后的mp4文件名列表。
    """
    mp4_pattern = os.path.join(video_path, "*.mp4") # 构建匹配mp4文件的glob模式
    video_files = glob.glob(mp4_pattern) # 使用glob查找所有匹配的文件
    return sorted(video_files) # 对文件名进行排序并返回

def update_up_done_file(filename):
    """
    将成功处理的文件名写入updone.txt文件。
    Args:
        filename (str): 成功处理的mp4文件名（不包含路径，仅文件名）。
    """
    up_done_file_path = 'updone.txt' # updone.txt 文件路径，相对于脚本所在目录
    try:
        with open(up_done_file_path, 'a', encoding='utf-8') as f: # 以追加模式打开updone.txt文件
            f.write(filename + '\n') # 将文件名写入文件，并添加换行符
    except Exception as e: # 捕获文件写入可能发生的异常
        print(f"警告: 写入 {up_done_file_path} 文件时发生错误: {e}") # 打印警告信息

def load_up_done_files():
    """
    加载updone.txt文件中已处理的文件名到集合中。
    如果文件不存在则创建。

    Returns:
        set: 已处理的文件名集合。
    """
    up_done_file_path = 'updone.txt' # updone.txt 文件路径，相对于脚本所在目录
    up_done_files = set() # 初始化一个空的集合，用于存储已处理的文件名

    if os.path.exists(up_done_file_path): # 检查updone.txt文件是否存在
        try:
            with open(up_done_file_path, 'r', encoding='utf-8') as f: # 以只读模式打开文件，指定UTF-8编码
                for line in f: # 逐行读取文件内容
                    filename = line.strip() # 去除行尾的换行符和空白字符
                    if filename: # 确保文件名非空
                        up_done_files.add(filename) # 将文件名添加到集合中
        except Exception as e: # 捕获文件读取可能发生的异常
            print(f"警告: 读取 {up_done_file_path} 文件时发生错误: {e}") # 打印警告信息
    else:
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 获取当前时间并格式化
            with open(up_done_file_path, 'w', encoding='utf-8') as f: # 创建新的updone.txt文件
                f.write(f"Doing task started at: {current_time}\n") # 写入包含开始时间的文本

            print(f"{up_done_file_path} 文件不存在，已创建。时间：{current_time}") # 打印文件创建信息
            up_done_files.add(current_time)
        except Exception as e: # 捕获文件创建可能发生的异常
            print(f"错误: 创建 {up_done_file_path} 文件时发生错误: {e}") # 打印错误信息

    return up_done_files # 返回已处理的文件名集合


if __name__ == '__main__':
    # 检查命令行参数
    #if len(sys.argv) != 2:
    #    print("Usage: python main.py <video folder path>")
    #    exit()
    #else:
    #    # 检查文件夹是否存在
    #    video_path = sys.argv[1]
    #    if not os.path.isdir(video_path):
    #        print(f"Error: {video_path} is not a valid directory.")
    #        exit()

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="Upload mp4 video files from a given directory.") 
    parser.add_argument("video_path", help="The absolute path to the video directory.") # 添加参数 video_path

    args = parser.parse_args() # 解析命令行参数
    video_path = args.video_path # 获取命令行参数指定的视频文件夹路径

    if not os.path.isdir(video_path): # 检查video_path是否是有效目录
        print(f"错误: '{video_path}' 不是一个有效的目录。") # 打印错误信息
        sys.exit(1) # 退出程序，返回错误代码 1


    sleep_time = 188
    #filepath = Path(BASE_DIR) / "videos"
    # how to get cookie, see the file of get_bilibili_cookie.py.
    account_file = Path(BASE_DIR / "cookies" / "bilibili_uploader" / "account.json")
    if not account_file.exists():
        print(f"{account_file.name} 配置文件不存在")
        sys.exit(2) # 退出程序，返回错误代码 2

    # config the cookie data and zone id 
    cookie_data = read_cookie_json_file(account_file)
    cookie_data = extract_keys_from_json(cookie_data)
    tid = VideoZoneTypes.TECH_COMPUTER_TECH.value  # 设置分区id
    tags = ["#区块链", "#blockchain", "#cryptocoin", "#数字货币", "#加密货币"]
    tags_str = ','.join([tag for tag in tags])
    print(f"Zone Type: {tid} Hashtag：{tags}")
    print("-----程序启动，开始循环检测...") # 打印程序启动信息
    while True: # 无限循环，持续执行文件上传逻辑
        wait_for_doing_file(video_path)   # 检测doing.txt文件是否存在，存在则等待
        folder_path = Path(video_path)    # 获取视频目录
        video_files = list(folder_path.glob("*.mp4")) # 获取文件夹中的所有mp4文件
        file_num = len(video_files)
        timestamps = generate_schedule_time_next_day(file_num, 1, daily_times=[16], timestamps=True)

        up_done_files = load_up_done_files() # 加载已处理的文件名列表
        if not up_done_files:
            print("updone.txt 文件创建失败，程序退出。")
            sys.exit(3)
        
        for index, video_file in enumerate(video_files):
            filename = os.path.basename(video_file) # 提取文件名 (不包含路径)
            if filename.startswith("._"): # 检查文件名是否以"._"开头
                print(f"文件 {filename} 是临时文件，跳过。") # 打印临时文件信息
                continue
            if filename not in up_done_files: # 检查文件是否已处理过
            # 获取视频标题和txt 文件名
                title = filename.replace(".mp4", "")
                #title, tags = get_title_and_hashtags(str(file))
                # just avoid error, bilibili don't allow same title of video.
                #title += random_emoji()
                # 打印视频文件名、标题和 hashtag
                print(f"上传视频文件名：{filename}")
                print(f"标题：{title}")
                # I set desc same as title, do what u like.
                desc = title
                #bili_uploader = BilibiliUploader(cookie_data, file, title, desc, tid, tags, timestamps[index])
                bili_uploader = BilibiliUploader(cookie_data, video_file, title, desc, tid, tags, None)
                bili_uploader.upload()
                update_up_done_file(filename) # 处理成功，更新updone.txt文件
                # life is beautiful don't so rush. be kind be patience
                print(f"----sleep time：{sleep_time}")
                time.sleep(sleep_time)
            else:
                print(f"文件 {filename} 已处理过，跳过。") # 打印文件已处理信息

        print(f"所有文件处理完成，休眠2小时... {time.strftime('%Y-%m-%d %H:%M:%S')}") # 打印休眠信息和当前时间
        time.sleep(2 * 3600) # 休眠2小时 (2 * 60 * 60 秒)

