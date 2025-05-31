from datetime import timedelta
from datetime import datetime
from pathlib import Path
import os
import re

from conf import BASE_DIR


def get_absolute_path(relative_path: str, base_dir: str = None) -> str:
    # Convert the relative path to an absolute path
    absolute_path = Path(BASE_DIR) / base_dir / relative_path
    return str(absolute_path)


def get_title_and_hashtags(filename):
    """
  获取视频标题和 hashtag

  Args:
    filename: 视频文件名

  Returns:
    视频标题和 hashtag 列表
  """

    # 获取视频标题和 hashtag txt 文件名
    txt_filename = filename.replace(".mp4", ".txt")

    # 读取 txt 文件
    with open(txt_filename, "r", encoding="utf-8") as f:
        content = f.read()

    # 获取标题和 hashtag
    splite_str = content.strip().split("\n")
    title = splite_str[0]
    hashtags = splite_str[1].replace("#", "").split(" ")

    return title, hashtags


def generate_filename_from_path(file_path):
    """
    根据文件路径生成文件名，处理特殊路径情况。
    
    Args:
        file_path (str): 文件路径，例如 "/damon/sun", "/damon/sun/articles", "/damon/sun/blogs",
                         "/damon/sun/shorts", "/damon/sun/videos"。
        
    Returns:
        str: 生成的文件名，例如 "sun", "sun_articles", "sun_blogs", "sun_shorts.txt", "sun_videos.txt"。
             如果路径为空或无法处理，则返回 None。
    """
    if not file_path:
        return None

    file_path = file_path.strip('/')

    base_name = Path(file_path).name
    dir_name = str(Path(file_path).parent)

    if not dir_name or dir_name == '.':
        return base_name

    parent_dir_name = Path(dir_name).name

    if base_name == "articles":
        return f"{parent_dir_name}_articles"
    elif base_name == "blogs":
        return f"{parent_dir_name}_blogs"
    elif base_name == "shorts":
        return f"{parent_dir_name}_shorts"
    elif base_name == "videos":
        return f"{parent_dir_name}_videos"
    else:
        return base_name


def process_filename(video_file):
    """提取用于测试的文件名处理逻辑
    
    文件名格式通常为 '实际标题_ytvid标识符_其他信息.mp4'
    或者 'AAA_BBB_CCC_DDDD_ytvid11_yyyy.mp4' 等包含多个下划线的形式。
    此函数会提取YouTube视频ID标识符(_ytvid)前的全部内容。
    如果文件名中没有找到这种模式，则使用整个文件名（去除路径和扩展名）。
    
    Args:
        video_file (str): 文件路径或文件名
        
    Returns:
        str: 处理后的文件名，仅保留YouTube视频ID标识前的部分
    """
    # 规范化路径分隔符，确保跨平台兼容性
    video_file = video_file.replace('\\', '/')
    
    # 获取基本文件名（不含路径和扩展名）
    base_name = os.path.splitext(os.path.basename(video_file))[0]
    
    # 方法1: 先尝试查找"_ytvid"模式
    ytvid_index = base_name.find('_ytvid11_')
    if ytvid_index != -1:
        # 获取YouTube视频ID标识前的部分
        title_part = base_name[:ytvid_index]
        # 特殊情况：如果分割后左侧为空，保留原始基本名
        return title_part if title_part else base_name

    # 方法2: 使用正则表达式匹配YouTube ID模式 (_xxxxxxxxxx)
    # 查找形如 _xxxxxxxxxxx 的模式，其中xxxxxxxxxx是11位字母数字组合
    match = re.search(r'_([a-zA-Z0-9_-]{11})(\.|_|$)', base_name)
    if match:
        youtube_id_start = match.start()  # 获取下划线的位置
        return base_name[:youtube_id_start]

    return base_name


def truncate_title_string(s):
    """从文件名中提取标题部分并截断过长的字符串
    
    最后，确保标题长度不超过80个字符。

    Args:
        s (str): 原始文件名字符串
        
    Returns:
        str: 提取并截断后的标题字符串，最大长度为80
    """
    
    # 截断标题至80个字符
    if len(s) > 80:
        return s[:80]
    return s


def process_video_title(video_file):
    """从视频文件名生成格式化的视频标题
    
    Args:
        video_file (str): 视频文件路径或文件名
        
    Returns:
        str: 处理并截断后的视频标题
    """
    base_name = process_filename(video_file)
    return truncate_title_string(base_name)


def generate_schedule_time_next_day(total_videos, videos_per_day, daily_times=None, timestamps=False, start_days=0):
    """
    Generate a schedule for video uploads, starting from the next day.

    Args:
    - total_videos: Total number of videos to be uploaded.
    - videos_per_day: Number of videos to be uploaded each day.
    - daily_times: Optional list of specific times of the day to publish the videos.
    - timestamps: Boolean to decide whether to return timestamps or datetime objects.
    - start_days: Start from after start_days.

    Returns:
    - A list of scheduling times for the videos, either as timestamps or datetime objects.
    """
    if videos_per_day <= 0:
        raise ValueError("videos_per_day should be a positive integer")

    if daily_times is None:
        # Default times to publish videos if not provided
        daily_times = [6, 11, 14, 16, 22]

    if videos_per_day > len(daily_times):
        raise ValueError("videos_per_day should not exceed the length of daily_times")

    # Generate timestamps
    schedule = []
    current_time = datetime.now()

    for video in range(total_videos):
        day = video // videos_per_day + start_days + 1  # +1 to start from the next day
        daily_video_index = video % videos_per_day

        # Calculate the time for the current video
        hour = daily_times[daily_video_index]
        time_offset = timedelta(days=day, hours=hour - current_time.hour, minutes=-current_time.minute,
                                seconds=-current_time.second, microseconds=-current_time.microsecond)
        timestamp = current_time + time_offset

        schedule.append(timestamp)

    if timestamps:
        schedule = [int(time.timestamp()) for time in schedule]
    return schedule
