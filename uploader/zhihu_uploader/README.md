# 知乎文章自动上传工具

本工具用于自动化将 Markdown 格式的文章上传至知乎平台。它使用 Playwright 进行浏览器自动化，能够通过 cookie 认证登录知乎，并将文章批量上传。

## 功能特点

- 使用 cookie 认证方式登录知乎
- 自动读取指定目录中的 Markdown 文件
- 自动填写文章标题、内容和标签
- 支持批量上传多篇文章
- 支持记录已上传的文章，避免重复上传
- 自动处理上传过程中的各种界面交互

## 使用方法

### 准备工作

1. 确保已安装所需依赖：
2. 配置文件结构：
   - 创建 `cookies/zhihu_uploader` 目录用于存储登录凭证
   - 准备包含文章路径的配置文件

### 运行示例

使用示例脚本 `examples/zhihu_up_alpha.py` 进行批量上传：

配置文件格式示例：
### 文章要求

- 文章应为 Markdown 格式（.md 文件）
- 建议文章第一行使用 `# 标题` 格式作为文章标题
- 如果第一行不是标题格式，将使用文件名作为文章标题

## 故障排除

如果在使用过程中遇到问题：

1. 检查 cookie 是否有效，可能需要重新登录
2. 观察日志输出，了解错误发生的位置
3. 如果页面结构有变化，可能需要更新选择器

## 注意事项

- 避免短时间内上传大量文章，以防被平台视为异常行为
- 默认两篇文章之间有 10 分钟间隔，可以根据需要调整