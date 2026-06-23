"""最小连通性测试: 用 playwright 真正打开 Boss 企业端登录页。

目的: 验证 browser-use / playwright 能拉起浏览器、能访问 Boss。
不调用任何 DeepSeek、不打招呼,纯粹是"能不能打开网页"。

运行(在 src/ 目录下):
    python test_open_boss.py

你会看到:
    1. 一个 Chrome 窗口弹出
    2. 打开 Boss 直聘企业端登录页
    3. 控制台打印页面标题,然后浏览器停留(方便你扫码登录)
    4. 扫码登录后,在控制台按回车,脚本退出
"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


async def main() -> None:
    # 用 playwright 直接驱动(比 browser-use 更底层,先验证最基础的能力)
    from playwright.async_api import async_playwright

    user_data = os.environ.get("CHROME_USER_DATA_DIR", "").strip()
    async with async_playwright() as p:
        launch_kwargs = {"headless": False}
        # 如果配了 Chrome profile,复用以保持登录态;否则用全新临时 profile
        if user_data:
            context = await p.chromium.launch_persistent_context(user_data, **launch_kwargs)
            page = context.pages[0] if context.pages else await context.new_page()
        else:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context()
            page = await context.new_page()

        print("[1/3] 浏览器已启动,正在打开 Boss 企业端...")
        await page.goto("https://www.zhipin.com/web/boss/", wait_until="domcontentloaded")
        title = await page.title()
        print(f"[2/3] 页面已打开,标题: {title}")
        print()
        print("=" * 50)
        print("现在请在弹出的浏览器窗口里扫码登录企业端账号。")
        print("登录完成后,回到这个终端按【回车】继续...")
        print("=" * 50)
        # 阻塞等待你扫码 + 回车
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input)

        # 登录后,打印当前 URL 和一段页面文本,帮我们判断是否登录成功
        print("[3/3] 当前 URL:", page.url)
        body_text = await page.inner_text("body")
        print("页面文字前 300 字:", body_text[:300])

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
