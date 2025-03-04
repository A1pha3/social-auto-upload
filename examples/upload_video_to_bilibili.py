import os
import sys
import glob
import time
import datetime
import argparse
from pathlib import Path

#from uploader.bilibili_uploader.main import random_emoji
from uploader.bilibili_uploader.main import read_cookie_json_file, extract_keys_from_json, BilibiliUploader
from conf import BASE_DIR
from utils.constant import VideoZoneTypes
#from utils.files_times import get_title_and_hashtags
from utils.files_times import generate_schedule_time_next_day 

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

def update_up_done_file(filename, video_path_name):
    """
    将成功处理的文件名写入updone.txt文件。
    Args:
        filename (str): 成功处理的mp4文件名（不包含路径，仅文件名）。
    """
    up_done_file_path = video_path_name + '_updone.txt' # updone.txt 文件路径，相对于脚本所在目录
    try:
        with open(up_done_file_path, 'a', encoding='utf-8') as f: # 以追加模式打开updone.txt文件
            f.write(filename + '\n') # 将文件名写入文件，并添加换行符
    except Exception as e: # 捕获文件写入可能发生的异常
        print(f"警告: 写入 {up_done_file_path} 文件时发生错误: {e}") # 打印警告信息

def load_up_done_files(video_path_name):
    """
    加载updone.txt文件中已处理的文件名到集合中。如果文件不存在则创建。
    Returns:
        set: 已处理的文件名集合。
    """
    up_done_file = video_path_name + '_updone.txt' # updone.txt 文件路径，相对于脚本所在目录
    up_done_files = set() # 初始化一个空的集合，用于存储已处理的文件名

    if os.path.exists(up_done_file): # 检查updone.txt文件是否存在
        try:
            with open(up_done_file, 'r', encoding='utf-8') as f: # 以只读模式打开文件，指定UTF-8编码
                for line in f: # 逐行读取文件内容
                    filename = line.strip() # 去除行尾的换行符和空白字符
                    if filename: # 确保文件名非空
                        up_done_files.add(filename) # 将文件名添加到集合中
        except Exception as e: # 捕获文件读取可能发生的异常
            print(f"警告: 读取 {up_done_file} 文件时发生错误: {e}") # 打印警告信息
    else:
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 获取当前时间并格式化
            with open(up_done_file, 'w', encoding='utf-8') as f: # 创建新的updone.txt文件
                f.write(f"Doing task started at: {current_time}\n") # 写入包含开始时间的文本

            print(f"{up_done_file} 文件不存在，已创建。时间：{current_time}") # 打印文件创建信息
            up_done_files.add(current_time)
        except Exception as e: # 捕获文件创建可能发生的异常
            print(f"错误: 创建 {up_done_file} 文件时发生错误: {e}") # 打印错误信息

    return up_done_files # 返回已处理的文件名集合

def parse_config_file(config_file_path):
    """
    解析配置文件，将要上传的视频文件路径存储到set中。
    Args:
        config_file_path (str): 配置文件的路径。
    Returns:
        set: 视频文件路径集合。
             如果配置文件读取失败，返回 None。
    """
    video_path_set = set() # 初始化一个空的集合，用于存储已处理的文件名
    if os.path.exists(config_file_path): 
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    video_path = line.strip() # 去除行首尾的空白字符
                    if not video_path or video_path.startswith('#'): # 忽略空行和注释行
                        continue
                    if ' ' in video_path:
                        print(f"错误: 文件路径中包含空格，路径: {video_path}。请检查配置文件，文件路径中不应包含空格。")
                        continue

                    video_path_set.add(video_path) # 将文件路径添加到集合中  
        except FileNotFoundError:
            print(f"错误: 配置文件未找到: {config_file_path}")
            return None
        except Exception as e:
            print(f"读取配置文件时发生错误: {e}")
            return None
    else:
        print(f"错误: 配置文件不存在: {config_file_path}")
        return None 
    return video_path_set

def generate_filename_from_path(file_path):
    """
    根据文件路径生成文件名，处理特殊路径情况。
    Args:
        file_path (str): 文件路径，例如 "/damon/sun", "/damon/sun/shorts", "/damon/sun/videos"。
    Returns:
        str: 生成的文件名，例如 "sun.txt", "sun_shorts.txt", "sun_videos.txt"。
             如果路径为空或无法处理，则返回 None。
    """
    if not file_path:
        return None  # 处理空路径的情况

    file_path = file_path.strip('/') # 去除路径首尾的斜杠，避免影响basename和dirname的处理

    base_name = os.path.basename(file_path) # 获取路径的最后部分，例如 "sun", "shorts", "videos"
    dir_name = os.path.dirname(file_path)  # 获取路径的目录部分，例如 "/damon/sun", "/damon/sun"

    if not dir_name:
        return base_name # 处理类似 "sun" 这种没有目录的情况

    parent_dir_name = os.path.basename(dir_name) # 获取父目录的名字, 例如 "sun", "damon"

    if base_name == "shorts":
        return f"{parent_dir_name}_shorts" #  处理 /damon/sun/shorts 情况
    elif base_name == "videos":
        return f"{parent_dir_name}_videos" #  处理 /damon/sun/videos 情况
    else:
        return base_name #  默认情况，使用basename作为文件名

def truncate_title_string(s):
    if len(s) > 80:
        return s[:80]
    return s

if __name__ == '__main__':
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="批量上传视频脚本，从配置文件中读取视频文件路径。")
    parser.add_argument("config_file", help="包含视频文件路径的配置文件路径")

    args = parser.parse_args() # 解析命令行参数
    config_file_path = args.config_file # 获取命令行参数指定的视频文件夹路径

    video_path_set = parse_config_file(config_file_path) # 解析配置文件，获取视频文件路径集合

    sleep_time = 1388 # 设置休眠时间为3588秒 (约59分钟)
    #sleep_time = 23976 # 设置休眠时间为23976秒 (约6.66Hour)
    # how to get cookie, see the file of get_bilibili_cookie.py.
    account_file = Path(BASE_DIR / "cookies" / "bilibili_uploader" / "account.json")
    if not account_file.exists():
        print(f"{account_file.name} 配置文件不存在")
        sys.exit(2) # 退出程序，返回错误代码 2

    # config the cookie data and zone id 
    cookie_data = read_cookie_json_file(account_file)
    cookie_data = extract_keys_from_json(cookie_data)
    tid = VideoZoneTypes.TECH_COMPUTER_TECH.value  # 设置分区id
    #tags = ["#区块链", "#blockchain", "#cryptocoin", "#数字货币", "#加密货币"]
    #tags = ["#佩奇", "#儿童动画 ", "#启蒙早教 ", "#英语启蒙 ", "#peppapig"]
    tags = ["#热舞", "#健康减脂 ", "#完美身材 ", "#火爆现场 ", "#拉拉队美女 "]
    tags_str = ','.join([tag for tag in tags])
    print(f"Zone Type: {tid} Hashtag：{tags}")
    print("-----程序启动，开始循环检测...") # 打印程序启动信息
    while True: # 无限循环，持续执行文件上传逻辑
        for video_path in video_path_set:
            wait_for_doing_file(video_path)   # 检测doing.txt文件是否存在，存在则等待
            folder_path = Path(video_path)    # 获取视频目录
            video_files = list(folder_path.glob("*.mp4")) # 获取文件夹中的所有mp4文件
            file_num = len(video_files)
            timestamps = generate_schedule_time_next_day(file_num, 1, daily_times=[16], timestamps=True)
            video_path_name = generate_filename_from_path(video_path) # 根据路径生成文件名 
            up_done_files = load_up_done_files(video_path_name) # 读取updone.txt，加载已处理的文件名列表
            if not up_done_files:
                print("updone.txt 文件创建失败，程序退出。")
                sys.exit(3)
        
            print(f"\n-------process video_path：{video_path}-----start-------\n")
            for index, video_file in enumerate(video_files):
                filename = os.path.basename(video_file) # 提取文件名 (不包含路径)
                if filename.startswith("._"): # 检查文件名是否以"._"开头
                    #print(f"文件 {filename} 是临时文件，跳过。") # 打印临时文件信息
                    continue
                if filename not in up_done_files: # 检查文件是否已处理过
                    title = filename.replace(".mp4", "")
                    #title, tags = get_title_and_hashtags(str(file))
                    # just avoid error, bilibili don't allow same title of video.
                    #title += random_emoji()
                    title = truncate_title_string(title)
                    print(f"上传视频文件名：{filename} 标题：{title}")
                    # I set desc same as title, do what u like.
                    desc = title
                    #bili_uploader = BilibiliUploader(cookie_data, file, title, desc, tid, tags, timestamps[index])
                    bili_uploader = BilibiliUploader(cookie_data, video_file, title, desc, tid, tags, None)
                    bili_uploader.upload()
                    update_up_done_file(filename, video_path_name) # 处理成功，更新updone.txt文件
                    # life is beautiful don't so rush. be kind be patience
                    print(f"----sleep time：{sleep_time}----wait to process next file----")
                    time.sleep(sleep_time)
                #else:
                #    print(f"文件 {filename} 已处理过，跳过。") # 打印文件已处理信息

            print(f"\n-------process video_path：{video_path}-----done-------\n")
        print(f"所有文件处理完成，休眠1小时... {time.strftime('%Y-%m-%d %H:%M:%S')}") # 打印休眠信息和当前时间
        time.sleep(1 * 3600) # 休眠1小时 (1 * 60 * 60 秒)

