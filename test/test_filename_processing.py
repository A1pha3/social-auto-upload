import unittest
import os
import sys

# 添加项目根目录到Python路径，确保可以导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.files_times import process_filename

class TestFilenameProcessing(unittest.TestCase):
    def test_standard_cases(self):
        """测试标准文件名格式"""
        test_cases = [
            # (输入文件名, 期望结果)
            ("test_video_part2.mp4", "test_video"),
            ("document_v1.2.3_final.mp4", "document_v1.2.3"),
            ("multiple_underscores_example_v3_test.mp4", "multiple_underscores_example_v3"),
        ]

        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = process_filename(filename)
                self.assertEqual(result, expected, f"File '{filename}' should process to '{expected}', got '{result}'")

    def test_files_with_dots(self):
        """测试包含点的文件名"""
        test_cases = [
            ("file.name_with.dots_v1.mp4", "file.name_with.dots"),
            ("version.1.2.3_release.mp4", "version.1.2.3"),
            ("project.files.backup_2023.mp4", "project.files.backup"),
        ]

        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = process_filename(filename)
                self.assertEqual(result, expected, f"File '{filename}' should process to '{expected}', got '{result}'")
    
    def test_no_underscore(self):
        """测试没有下划线的文件名"""
        test_cases = [
            ("nounderscores.mp4", "nounderscores"),
            ("simple.mp4", "simple"),
            ("justname", "justname"),  # 无扩展名
        ]

        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = process_filename(filename)
                self.assertEqual(result, expected, f"File '{filename}' should process to '{expected}', got '{result}'")
    
    def test_special_cases(self):
        """测试特殊情况"""
        test_cases = [
            ("_start_with_underscore_v1.mp4", "_start_with_underscore"),
            ("ends_with_underscore_.mp4", "ends_with_underscore"),
            ("中文文件名_测试版.mp4", "中文文件名"),
            ("file with spaces_v1.mp4", "file with spaces"),
            ("特殊字符!@#$%^&()_version.mp4", "特殊字符!@#$%^&()"),
            # 添加问题文件名测试用例
            ("特斯拉出了个啥财报？【2025-04-22】_x7VR7CzcopQ.mp4", "特斯拉出了个啥财报？【2025-04-22】"),
        ]

        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = process_filename(filename)
                self.assertEqual(result, expected, f"File '{filename}' should process to '{expected}', got '{result}'")
    
    def test_edge_cases(self):
        """测试边缘情况"""
        test_cases = [
            ("", ""),  # 空文件名
            ("   ", "   "),  # 空白文件名
            ("a.mp4", "a"),  # 最短文件名
            ("a_b.mp4", "a"),  # 最短带下划线
            (".hidden_file.mp4", ".hidden"),  # 隐藏文件
            ("_.mp4", "_"),  # 只有下划线
            ("verylongfilename" * 10 + "_version.mp4", "verylongfilename" * 10),  # 非常长的文件名
        ]

        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = process_filename(filename)
                self.assertEqual(result, expected, f"File '{filename}' should process to '{expected}', got '{result}'")
    
    def test_path_handling(self):
        """测试带路径的文件名"""
        test_cases = [
            ("/path/to/file_v1.mp4", "file"),
            ("C:\\Windows\\file_name_v2.mp4", "file_name"),
            ("../relative/path/document_final.mp4", "document"),
            ("~/user/files/video_part1.mp4", "video"),
        ]

        for filepath, expected in test_cases:
            with self.subTest(filepath=filepath):
                result = process_filename(filepath)
                self.assertEqual(result, expected, f"Path '{filepath}' should process to '{expected}', got '{result}'")
    
    def test_multiple_extensions(self):
        """测试多重扩展名"""
        test_cases = [
            ("file_v1.tar.gz", "file"),
            ("backup_2023.tar.bz2", "backup"),
            ("document_final.txt.bak", "document"),
        ]

        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = process_filename(filename)
                self.assertEqual(result, expected, f"File '{filename}' should process to '{expected}', got '{result}'")
        
    def test_youtube_id_patterns(self):
        """测试不同形式的YouTube ID模式"""
        test_cases = [
            # 标准YouTube视频ID格式
            ("视频名称_x7VR7CzcopQ.mp4", "视频名称"),
            # 使用ytvid前缀的格式
            ("标题_ytvid123456789_其他信息.mp4", "标题"),
            # 复杂文件名带特殊字符和YouTube ID
            ("特斯拉出了个啥财报？【2025-04-22】_x7VR7CzcopQ.mp4", "特斯拉出了个啥财报？【2025-04-22】"),
            # 包含多个下划线，后面是YouTube ID
            ("AAA_BBB_CCC_DDDD_x7VR7CzcopQ.mp4", "AAA_BBB_CCC_DDDD"),
        ]
        
        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                result = process_filename(filename)
                self.assertEqual(result, expected, f"File '{filename}' should process to '{expected}', got '{result}'")

if __name__ == '__main__':
    unittest.main()