# -*- coding: utf-8 -*-
import os
import asyncio
import json
import time
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import traceback

from playwright.async_api import Playwright, async_playwright
import markdown

from conf import BASE_DIR, LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import zhihu_logger

# 设置日志
zhihu_logger = zhihu_logger.bind(name="zhihu")

async def cookie_auth(account_file):
    """
    验证知乎cookie是否有效
    
    Args:
        account_file: cookie文件路径
    
    Returns:
        bool: cookie是否有效
    """
    # 读取cookie
    try:
        with open(account_file, 'r') as f:
            storage = json.load(f)
    except Exception as e:
        zhihu_logger.error(f'读取cookie文件失败：{e}')
        return False
    
    # 检查cookie
    async with async_playwright() as playwright:
        # 启动浏览器，使用更简单的配置
        try:
            zhihu_logger.info('尝试启动浏览器...')
            browser = await playwright.chromium.launch(
                headless=True,
                slow_mo=50
            )
            zhihu_logger.info('浏览器启动成功')
        except Exception as e:
            zhihu_logger.error(f'浏览器启动失败: {e}')
            try:
                executable_path = playwright.chromium.executable_path
                zhihu_logger.info(f'Chromium 路径: {executable_path}')
            except Exception as exe_error:
                zhihu_logger.error(f'无法获取浏览器路径: {exe_error}')
            return False
        
        # 创建上下文
        try:
            context = await browser.new_context(storage_state=storage)
            context = await set_init_script(context)
            page = await context.new_page()
        except Exception as e:
            zhihu_logger.error(f'创建浏览器上下文或页面失败: {e}')
            await browser.close()
            return False
        
        try:
            await page.goto("https://www.zhihu.com/creator/manage/creation/article")
            await page.wait_for_load_state("networkidle")
            
            login_button = await page.locator("button:has-text('登录')").count()
            if login_button > 0:
                zhihu_logger.info('[+] cookie已失效')
                await browser.close()
                return False
            else:
                zhihu_logger.info('[+] cookie有效')
                await browser.close()
                return True
        except Exception as e:
            zhihu_logger.error(f'检查cookie时发生错误：{e}')
            await browser.close()
            return False

async def zhihu_setup(account_file, handle=False):
    """
    设置知乎cookie，如果cookie不存在或无效，则自动打开浏览器等待用户登录
    
    Args:
        account_file: cookie文件路径
        handle: 是否处理cookie无效的情况
    
    Returns:
        bool: 设置是否成功
    """
    account_file = get_absolute_path(account_file, "zhihu_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            zhihu_logger.info('[+] cookie文件不存在或已失效，因为handle为False，所以不去登录')
            return False
        zhihu_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await get_zhihu_cookie(account_file)
    return True

async def get_zhihu_cookie(account_file):
    """
    打开浏览器，让用户登录知乎，并获取cookie
    
    Args:
        account_file: cookie文件保存路径
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--no-sandbox',
                '--lang=zh-CN,zh'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        context = await set_init_script(context)
        
        await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en']
        });
        """)
        
        page = await context.new_page()
        
        await page.goto("https://www.zhihu.com/signin")
        
        zhihu_logger.info('[+] 请在浏览器中登录知乎')
        zhihu_logger.info('[+] 登录完成后，请按下Enter键继续...')
        await page.pause()
        
        await page.wait_for_timeout(3000)
        
        await context.storage_state(path=account_file)
        zhihu_logger.success('[+] cookie保存成功')
        return True

class ZhihuArticle:
    """
    知乎文章发布类
    """
    def __init__(self, title: str, content_file: str, tags: List[str], publish_date: Optional[datetime], account_file: str):
        """
        初始化知乎文章发布类
        
        Args:
            title: 文章标题
            content_file: 文章内容文件路径（Markdown格式）
            tags: 文章标签
            publish_date: 发布时间，None表示立即发布
            account_file: cookie文件路径
        """
        self.title = title
        self.content_file = content_file
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y-%m-%d %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
    
    async def handle_human_verification(self, page):
        """处理知乎人机验证页面
        
        Args:
            page: Playwright页面对象
            
        Returns:
            bool: 验证是否成功
        """
        if "unhuman" in page.url:
            zhihu_logger.warning(f"检测到人机验证页面: {page.url}")
            zhihu_logger.info("请在浏览器窗口中完成人机验证...")
            
            # 等待用户手动完成验证
            for i in range(60):  # 最多等待60秒
                await page.wait_for_timeout(1000)
                if "unhuman" not in page.url:
                    zhihu_logger.info("人机验证通过！")
                    await page.wait_for_timeout(1000)  # 额外等待页面加载
                    return True
                
                # 每10秒提醒一次
                if i % 10 == 0 and i > 0:
                    zhihu_logger.info(f"仍在等待验证完成...已等待{i}秒")
            
            zhihu_logger.error("人机验证超时，请检查浏览器状态")
            return False
        
        return True  # 没有验证页面，直接返回成功

    async def upload(self, playwright: Playwright) -> None:
        """
        上传文章到知乎
        
        Args:
            playwright: Playwright实例
        """
        with open(self.content_file, 'r', encoding='utf-8') as f:
            content = f.read()
        zhihu_logger.info(f'成功读取文章内容，文件路径：{self.content_file}')
        
        options = {
            'args': [
                '--lang zh-CN',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ],
            'headless': False,  # 改为有头模式，便于用户看到验证页面
            'slow_mo': 50  # 减缓操作速度，减少被识别为机器人的可能性
        }
        browser = await playwright.chromium.launch(**options)
        
        # 创建更真实的浏览器上下文
        context = await browser.new_context(
            storage_state=self.account_file,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )
        
        context = await set_init_script(context)
        
        page = await context.new_page()
        
        try:
            await page.goto("https://zhuanlan.zhihu.com/write")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            
            # 处理人机验证
            await self.handle_human_verification(page)
            
            # 获取当前URL
            current_url = page.url
            if current_url != "https://zhuanlan.zhihu.com/write":
                zhihu_logger.warning(f'未能直接进入编辑页面，当前URL: {current_url}，尝试通过创作中心进入...')
                
                await page.goto("https://www.zhihu.com/creator")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                # 再次处理可能出现的人机验证
                await self.handle_human_verification(page)
                
                write_button_found = False
                
                selectors = [
                    'a[href="/write"]',
                    'a:has-text("写文章")',
                    'button:has-text("写文章")',
                    '.WriteIndexButton',
                    '[data-za-detail-view-id="172"]'
                ]
                
                for selector in selectors:
                    if await page.locator(selector).count() > 0:
                        zhihu_logger.info(f'找到"写文章"按钮，使用选择器: {selector}')
                        await page.locator(selector).click()
                        write_button_found = True
                        await page.wait_for_timeout(3000)
                        break
                
                if not write_button_found:
                    zhihu_logger.info('未找到"写文章"按钮，直接访问写文章页面')
                    await page.goto("https://zhuanlan.zhihu.com/write")
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(3000)
                    
                    # 再次处理可能出现的人机验证
                    await self.handle_human_verification(page)
            
            if "write" not in page.url:
                # 最后一次尝试处理人机验证
                if "unhuman" in page.url:
                    if await self.handle_human_verification(page):
                        # 验证通过后再次尝试进入编辑页面
                        await page.goto("https://zhuanlan.zhihu.com/write")
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(2000)
                    else:
                        raise Exception("人机验证失败，无法进入编辑页面")
                
                # 再次检查URL
                if "write" not in page.url:
                    zhihu_logger.error(f'未能进入编辑页面，当前URL: {page.url}')
                    raise Exception("未能进入知乎文章编辑页面")
            
            title_selectors = [
                "div[data-slate-editor='true']",
                ".WriteIndex-titleInput",
                "div.notranslate[contenteditable='true']"
            ]
            
            title_input = None
            for selector in title_selectors:
                if await page.locator(selector).count() > 0:
                    title_input = page.locator(selector).first()
                    zhihu_logger.info(f'找到标题输入框，使用选择器: {selector}')
                    break
            
            if title_input:
                await title_input.click()
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type(self.title)
            else:
                zhihu_logger.warning('未找到标题输入框，尝试使用Tab导航到标题区域')
                await page.keyboard.press("Tab")
                await page.keyboard.type(self.title)
            
            await page.keyboard.press("Tab")
            
            import_success = False
            
            try:
                more_buttons = ["button.css-m5a9ul", ".Editable-toolbar button:last-child", "button.WriteIndex-moreButton"]
                for more_selector in more_buttons:
                    if await page.locator(more_selector).count() > 0:
                        await page.locator(more_selector).click()
                        await page.wait_for_timeout(1000)
                        
                        import_options = ["div:has-text('导入Markdown')", "li:has-text('导入Markdown')"]
                        for import_selector in import_options:
                            if await page.locator(import_selector).count() > 0:
                                await page.locator(import_selector).click()
                                await page.wait_for_timeout(1000)
                                
                                markdown_inputs = ["textarea.css-lk63t1", "textarea", ".ImportPanel-input"]
                                for input_selector in markdown_inputs:
                                    if await page.locator(input_selector).count() > 0:
                                        await page.locator(input_selector).fill(content)
                                        await page.wait_for_timeout(1000)
                                        
                                        import_buttons = ["button:has-text('导入')", ".ImportPanel-button", "button.css-lxrmzw"]
                                        for button_selector in import_buttons:
                                            if await page.locator(button_selector).count() > 0:
                                                await page.locator(button_selector).click()
                                                await page.wait_for_timeout(3000)
                                                import_success = True
                                                break
                                        if import_success:
                                            break
                                if import_success:
                                    break
                        if import_success:
                            break
            except Exception as e:
                zhihu_logger.warning(f'使用更多菜单导入Markdown失败: {e}')
            
            if not import_success:
                zhihu_logger.info('尝试直接粘贴内容到编辑器...')
                try:
                    content_editors = ["div.public-DraftEditor-content", "div.notranslate[contenteditable='true']:not(div.WriteIndex-titleInput)", ".Editable-content", ".DraftEditor-root"]
                    for editor_selector in content_editors:
                        if await page.locator(editor_selector).count() > 0:
                            await page.locator(editor_selector).click()
                            await page.keyboard.press("Control+KeyA")
                            await page.keyboard.press("Delete")
                            
                            try:
                                zhihu_logger.info('尝试使用keyboard.type方法写入内容...')
                                await page.keyboard.type(self.title + "\n\n")  # 先输入标题和空行
                                
                                # 分段处理内容以避免一次处理过多数据
                                chunk_size = 1000
                                for i in range(0, len(content), chunk_size):
                                    chunk = content[i:i+chunk_size]
                                    await page.keyboard.type(chunk)
                                    await page.wait_for_timeout(100)
                                
                                await page.wait_for_timeout(2000)
                                import_success = True
                            except Exception as e:
                                zhihu_logger.error(f'使用keyboard.type方法失败，错误详情: {e}\n{traceback.format_exc()}')
                                # 尝试另一种方法
                                try:
                                    # 使用fill方法尝试填充内容
                                    await page.locator(editor_selector).fill(self.title + "\n\n" + content[:1000])
                                    import_success = True
                                except Exception as e2:
                                    zhihu_logger.error(f'使用fill方法也失败: {e2}')
                            break
                except Exception as e:
                    zhihu_logger.warning(f'直接粘贴内容失败: {e}')
            
            if not import_success:
                zhihu_logger.warning('无法导入或粘贴内容，尝试手动输入标题后继续...')
            
            if len(self.tags) > 0:
                tag_buttons = ["div:has-text('添加话题')", ".WriteIndex-tagLine", "button:has-text('添加话题')"]
                tag_button_found = False
                
                for tag_button_selector in tag_buttons:
                    if await page.locator(tag_button_selector).count() > 0:
                        await page.locator(tag_button_selector).click()
                        await page.wait_for_timeout(1000)
                        tag_button_found = True
                        
                        for tag in self.tags[:5]:
                            tag_inputs = ["input.css-1ssna7n", ".WriteIndex-addTagInput", "input[placeholder='搜索话题']"]
                            tag_input_found = False
                            
                            for tag_input_selector in tag_inputs:
                                if await page.locator(tag_input_selector).count() > 0:
                                    tag_input = page.locator(tag_input_selector)
                                    await tag_input.fill(tag)
                                    await page.wait_for_timeout(2000)
                                    tag_input_found = True
                                    
                                    result_selectors = ["div.css-1j6tmgm", ".WriteIndex-searchTagItem", "[role='option']"]
                                    for result_selector in result_selectors:
                                        if await page.locator(result_selector).count() > 0:
                                            await page.locator(result_selector).first().click()
                                            await page.wait_for_timeout(1000)
                                            break
                                    break
                            
                            if not tag_input_found:
                                zhihu_logger.warning(f'未找到标签输入框，跳过添加标签 "{tag}"')
                        break
                
                if not tag_button_found:
                    zhihu_logger.warning('未找到添加话题按钮，跳过添加标签')
            
            if self.publish_date is not None:
                await self.set_schedule_time(page, self.publish_date)
            
            publish_button_found = False
            publish_selectors = ["button:has-text('发布文章')", ".WriteIndex-publishButton", ".PublishPanel-button button"]
            
            for publish_selector in publish_selectors:
                if await page.locator(publish_selector).count() > 0:
                    await page.locator(publish_selector).click()
                    publish_button_found = True
                    await page.wait_for_timeout(2000)
                    break
            
            if not publish_button_found:
                zhihu_logger.warning('未找到发布按钮，尝试使用快捷键 Ctrl+Enter 发布')
                await page.keyboard.press("Control+Enter")
            
            try:
                confirm_selectors = ["button:has-text('确定')", ".PublishConfirmModal-button", "button:has-text('确认发布')"]
                confirm_button = None
                
                for confirm_selector in confirm_selectors:
                    if await page.locator(confirm_selector).count() > 0:
                        confirm_button = page.locator(confirm_selector)
                        break
                        
                if confirm_button:
                    await confirm_button.click()
                    await page.wait_for_timeout(2000)
                else:
                    zhihu_logger.info('无需确认发布')
            except Exception as e:
                zhihu_logger.info(f'确认发布时发生异常: {e}')
            
            success = False
            for _ in range(30):
                current_url = page.url
                if "zhuanlan.zhihu.com/p/" in current_url or "/creator/manage/" in current_url:
                    success = True
                    break
                await page.wait_for_timeout(1000)
            
            if success:
                zhihu_logger.success('文章发布成功！')
            else:
                zhihu_logger.warning('无法确认文章是否发布成功')
            
        except Exception as e:
            zhihu_logger.error(f'发布文章时发生错误：{e}\n{traceback.format_exc()}')
            # 捕获屏幕截图以便调试
            await page.screenshot(path=f"zhihu_error_{int(time.time())}.png", full_page=True)
        finally:
            await context.storage_state(path=self.account_file)
            zhihu_logger.info('cookie更新完毕！')
            await context.close()
            await browser.close()
            zhihu_logger.info('浏览器已关闭')
    
    async def main(self):
        """
        主函数，用于执行上传流程
        """
        async with async_playwright() as playwright:
            await self.upload(playwright)
    
    async def set_schedule_time(self, page, publish_date):
        """
        设置定时发布时间
        
        Args:
            page: 页面对象
            publish_date: 发布时间
        """
        try:
            zhihu_logger.info("设置定时发布...")
            publish_date_str = publish_date.strftime("%Y-%m-%d %H:%M:%S")
            
            timing_selectors = ["div.css-13mfv52:has-text('定时发布')", "div:has-text('定时发布'):not(:has(*))"]
            timing_found = False
            
            for selector in timing_selectors:
                if await page.locator(selector).count() > 0:
                    await page.locator(selector).click()
                    timing_found = True
                    break
            
            if not timing_found:
                zhihu_logger.warning("未找到定时发布选项，跳过设置")
                return
            
            await page.wait_for_timeout(1000)
            
            date_selectors = ["input[placeholder='请选择日期']", ".DateInput input"]
            date_input_found = False
            
            for selector in date_selectors:
                if await page.locator(selector).count() > 0:
                    await page.locator(selector).click()
                    date_input_found = True
                    
                    date_only = publish_date.strftime("%Y-%m-%d")
                    await page.locator(selector).fill(date_only)
                    await page.keyboard.press("Enter")
                    break
            
            if not date_input_found:
                zhihu_logger.warning("未找到日期输入框，跳过设置")
                return
            
            await page.wait_for_timeout(1000)
            
            time_selectors = ["input[placeholder='请选择时间']", ".TimeInput input"]
            time_input_found = False
            
            for selector in time_selectors:
                if await page.locator(selector).count() > 0:
                    time_only = publish_date.strftime("%H:%M")
                    await page.locator(selector).fill(time_only)
                    await page.keyboard.press("Enter")
                    time_input_found = True
                    break
            
            if not time_input_found:
                zhihu_logger.warning("未找到时间输入框，跳过设置")
                return
            
            confirm_selectors = ["button:has-text('确定')", ".ConfirmModal-button"]
            confirm_found = False
            
            for selector in confirm_selectors:
                if await page.locator(selector).count() > 0:
                    await page.locator(selector).click()
                    confirm_found = True
                    break
            
            if not confirm_found:
                zhihu_logger.warning("未找到确认按钮，定时发布可能未成功设置")
                return
            
            zhihu_logger.info(f"定时发布已设置为：{publish_date_str}")
        except Exception as e:
            zhihu_logger.error(f"设置定时发布时发生错误: {e}")
            zhihu_logger.info("继续发布文章...")