#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import glob
import datetime
import asyncio
import argparse
from pathlib import Path

from conf import BASE_DIR
from uploader.zhihu_uploader.main import zhihu_setup, ZhihuArticle
from utils.files_times import generate_filename_from_path


def wait_for_doing_file(article_path):
    """
    循环检测指定目录下doing.txt文件是否存在，如果存在则等待。
    Args:
        article_path (str): 文章文件所在的绝对路径。
    """
    doing_file_path = os.path.join(article_path, 'doing.txt')

    while True:
        if os.path.exists(doing_file_path):
            print(f"发现 {doing_file_path} 文件，等待5分钟...")
            time.sleep(5 * 60)
        else:
            break


def get_md_files(article_path):
    """
    获取指定目录下所有的md文件，并按文件名排序。
    Args:
        article_path (str): 文章文件所在的绝对路径。
    Returns:
        list: 排序后的md文件名列表。
    """
    md_pattern = os.path.join(article_path, "*.md")
    article_files = glob.glob(md_pattern)
    return sorted(article_files)


def update_up_done_file(filename, article_path_name):
    """
    将成功处理的文件名写入updone.txt文件。
    Args:
        filename (str): 成功处理的md文件名（不包含路径，仅文件名）。
        article_path_name (str): 文件路径名称，用于生成updone文件名。
    """
    up_done_file_path = article_path_name + '_updone.txt'
    try:
        with open(up_done_file_path, 'a', encoding='utf-8') as f:
            f.write(filename + '\n')
    except Exception as e:
        print(f"警告: 写入 {up_done_file_path} 文件时发生错误: {e}")


def load_up_done_files(article_path_name):
    """
    加载updone.txt文件中已处理的文件名到集合中。如果文件不存在则创建。
    Args:
        article_path_name (str): 文件路径名称，用于生成updone文件名。
    Returns:
        set: 已处理的文件名集合。
    """
    up_done_file = article_path_name + '_updone.txt'
    up_done_files = set()

    if os.path.exists(up_done_file):
        try:
            with open(up_done_file, 'r', encoding='utf-8') as f:
                for line in f:
                    filename = line.strip()
                    if filename:
                        up_done_files.add(filename)
        except Exception as e:
            print(f"警告: 读取 {up_done_file} 文件时发生错误: {e}")
    else:
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(up_done_file, 'w', encoding='utf-8') as f:
                f.write(f"Doing task started at: {current_time}\n")

            print(f"{up_done_file} 文件不存在，已创建。时间：{current_time}")
            up_done_files.add(current_time)
        except Exception as e:
            print(f"错误: 创建 {up_done_file} 文件时发生错误: {e}")

    return up_done_files


def parse_config_file(config_file_path):
    """
    解析配置文件，将要上传的文章文件路径存储到set中。
    Args:
        config_file_path (str): 配置文件的路径。
    Returns:
        set: 文章文件路径集合。如果配置文件读取失败，返回 None。
    """
    article_path_set = set()
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    article_path = line.strip()
                    if not article_path or article_path.startswith('#'):
                        continue
                    if ' ' in article_path:
                        print(f"错误: 文件路径中包含空格，路径: {article_path}。请检查配置文件，文件路径中不应包含空格。")
                        continue

                    article_path_set.add(article_path)
        except FileNotFoundError:
            print(f"错误: 配置文件未找到: {config_file_path}")
            return None
        except Exception as e:
            print(f"读取配置文件时发生错误: {e}")
            return None
    else:
        print(f"错误: 配置文件不存在: {config_file_path}")
        return None
    return article_path_set


def get_article_title_from_file(file_path):
    """
    从Markdown文件中提取文章标题，假设标题是文件的第一行，以#开头
    Args:
        file_path (str): Markdown文件路径
    Returns:
        str: 文章标题
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('# '):
                return first_line[2:]  # 移除'# '前缀
            else:
                # 如果不是标准格式，使用文件名作为标题
                filename = os.path.basename(file_path)
                return filename.replace('.md', '')
    except Exception as e:
        print(f"读取文件标题时发生错误: {e}")
        # 使用文件名作为标题
        filename = os.path.basename(file_path)
        return filename.replace('.md', '')


if __name__ == '__main__':
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="批量上传文章到知乎脚本，从配置文件中读取文章文件路径。")
    parser.add_argument("config_file", help="包含文章文件路径的配置文件路径")
    args = parser.parse_args()

    config_file_path = args.config_file
    article_path_set = parse_config_file(config_file_path)
    if article_path_set is None:
        print("article_path_set is None, so exit.")
        sys.exit(1)

    # 设置两篇文章之间的等待时间
    sleep_time = 600  # 10分钟，可根据需要调整

    # 设置知乎账号文件
    cookies_dir = Path(BASE_DIR / "cookies" / "zhihu_uploader")
    cookies_dir.mkdir(parents=True, exist_ok=True)
    account_file = cookies_dir / "account.json"
    
    # 设置cookie
    cookie_setup = asyncio.run(zhihu_setup(account_file, handle=True))
    if not cookie_setup:
        print("Zhihu cookie setup failed, program exit.")
        sys.exit(2)

    # 设置文章标签
    tags = ["科技", "互联网", "程序员", "编程", "Python"]

    print(f" -- sleeptime:{sleep_time} ----tags：{tags}")
    print(f"-----程序启动，config: {config_file_path} -- article_path:{article_path_set}----")
    
    while True:  # 无限循环，持续执行文件上传逻辑
        for article_path in article_path_set:
            wait_for_doing_file(article_path)  # 检测doing.txt文件是否存在，存在则等待
            folder_path = Path(article_path)  # 获取文章目录
            
            # 检查目录是否存在
            if not folder_path.exists():
                print(f"警告: 目录不存在: {article_path}，跳过")
                continue
                
            # 获取文件夹中的所有Markdown文件
            article_files = list(folder_path.glob("*.md"))
            file_num = len(article_files)
            
            if file_num == 0:
                print(f"警告: 在目录 {article_path} 中未找到Markdown文件，跳过")
                continue
                
            article_path_name = generate_filename_from_path(article_path)  # 根据路径生成文件名
            up_done_files = load_up_done_files(article_path_name)  # 读取updone.txt，加载已处理的文件名列表
            if not up_done_files:
                print("updone.txt 文件创建失败，程序退出。")
                sys.exit(3)

            print(f"\n-------process article_path：{article_path}-----start-------\n")
            for index, article_file in enumerate(article_files):
                filename = os.path.basename(article_file)  # 提取文件名 (不包含路径)
                if filename.startswith("._"):  # 检查文件名是否以"._"开头
                    continue

                if filename not in up_done_files:  # 检查文件是否已处理过
                    # 从文章文件中获取标题
                    title = get_article_title_from_file(article_file)
                    print(f"-------上传文章文件名：{filename} -----标题：{title} ------------")
                    
                    # 创建知乎文章对象并上传
                    app = ZhihuArticle(title, article_file, tags, None, account_file)
                    asyncio.run(app.main())
                    
                    # 更新已处理文件记录
                    update_up_done_file(filename, article_path_name)
                    
                    # 等待一段时间再处理下一个文件
                    print(f"---------wait to process next file--------sleep time：{sleep_time}-----")
                    time.sleep(sleep_time)

            print(f"\n-------process article_path：{article_path}-----done-------\n")
        
        print(f"所有文件处理完成，休眠1小时... {time.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(1 * 3600)  # 休眠1小时