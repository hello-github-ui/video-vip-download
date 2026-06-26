#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2026/6/22 10:26
# @Author  : 19921224
# @File    : function_test.py
# @Software: PyCharm
# @Description: 功能测试
import json
import re
from urllib.parse import urlparse


def get_tencent_episode_list(first_url: str):
    """
    获取腾讯视频电视剧全部集数URL列表

    原理：
    1. 使用 Playwright 加载页面，等待页面完全渲染
    2. 从页面的剧集列表元素(dt-params属性)中提取所有vid
    3. 使用 cid + vid 拼接每一集的完整URL

    @param first_url: 第一集视频的url，例如：
        https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html
    @return: dict，包含成功状态、消息、剧集列表数据
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            'success': False,
            'message': '请先安装 playwright: pip install playwright && playwright install chromium',
            'data': None
        }

    try:
        parsed = urlparse(first_url)
        match = re.search(r'/x/cover/([^/]+)/([^/\.]+)\.html', first_url)
        if not match:
            return {
                'success': False,
                'message': f'URL格式错误，无法解析cid: {first_url}',
                'data': None
            }
        cid = match.group(1)
        current_vid = match.group(2)
        print(f"解析得到 cid: {cid}, 当前vid: {current_vid}")

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, channel="chrome")
                print("  使用系统安装的 Chrome 浏览器")
            except Exception:
                try:
                    browser = p.chromium.launch(headless=True, channel="msedge")
                    print("  使用系统安装的 Edge 浏览器")
                except Exception:
                    browser = p.chromium.launch(headless=True)
                    print("  使用 Playwright 内置浏览器")

            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            print("正在加载页面，请稍候...")
            try:
                page.goto(first_url, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                print("  首次加载超时，尝试等待后继续...")

            page.wait_for_timeout(5000)

            vids = []

            print("方案1: 使用 JavaScript 提取所有剧集项的 vid...")
            try:
                all_episodes = page.evaluate("""
                    () => {
                        const result = [];
                        const items = document.querySelectorAll('.episode-item, [data-video-idx]');
                        items.forEach(item => {
                            const dtParams = item.getAttribute('dt-params');
                            if (dtParams) {
                                const match = dtParams.match(/[?&]vid=([^&]+)/);
                                if (match && match[1]) {
                                    result.push(match[1]);
                                }
                            }
                        });
                        return result;
                    }
                """)
                print(f"  JavaScript提取到 {len(all_episodes)} 个 vid")
                for vid in all_episodes:
                    if vid and vid not in vids:
                        vids.append(vid)
            except Exception as e:
                print(f"  方案1失败: {e}")

            print("  检查分页按钮并切换...")
            try:
                tabs = page.evaluate("""
                    () => {
                        const result = [];
                        const seen = new Set();
                        const allButtons = document.querySelectorAll('button, a, span');
                        allButtons.forEach(btn => {
                            const text = btn.innerText.trim();
                            if (text && text.match(/^\\d+-\\d+$/) && !seen.has(text)) {
                                seen.add(text);
                                result.push(text);
                            }
                        });
                        return result;
                    }
                """)
                print(f"  找到的分页标签: {tabs}")

                for tab_text in tabs:
                    if tab_text and tab_text != "1-30":
                        print(f"  尝试点击分页: {tab_text}")
                        try:
                            page.evaluate(f"""
                                () => {{
                                    const buttons = document.querySelectorAll('button, a, span');
                                    for (const btn of buttons) {{
                                        if (btn.innerText.trim() === '{tab_text}') {{
                                            btn.click();
                                            return true;
                                        }}
                                    }}
                                    return false;
                                }}
                            """)
                            page.wait_for_timeout(3000)

                            more_episodes = page.evaluate("""
                                () => {
                                    const result = [];
                                    const items = document.querySelectorAll('.episode-item, [data-video-idx]');
                                    items.forEach(item => {
                                        const dtParams = item.getAttribute('dt-params');
                                        if (dtParams) {
                                            const match = dtParams.match(/[?&]vid=([^&]+)/);
                                            if (match && match[1]) {
                                                result.push(match[1]);
                                            }
                                        }
                                    });
                                    return result;
                                }
                            """)
                            print(f"    从新分页提取到 {len(more_episodes)} 个 vid")
                            for vid in more_episodes:
                                if vid and vid not in vids:
                                    vids.append(vid)
                        except Exception as e:
                            print(f"    点击失败: {e}")

            except Exception as e:
                print(f"  分页处理失败: {e}")

            if not vids:
                print("方案2: 从 window.__INITIAL_STATE__ 中提取...")
                try:
                    state_js = page.evaluate("() => window.__INITIAL_STATE__")
                    if state_js:
                        state_str = json.dumps(state_js, ensure_ascii=False)
                        vid_matches = re.findall(r'"vid"\s*:\s*"([a-zA-Z0-9]+)"', state_str)
                        for vid in vid_matches:
                            if vid and vid != cid and vid not in vids:
                                vids.append(vid)
                        print(f"  从 __INITIAL_STATE__ 提取到 {len(vid_matches)} 个 vid，去重后 {len(vids)} 个")
                except Exception as e:
                    print(f"  方案2失败: {e}")

            if not vids:
                print("方案3: 从渲染后的HTML中提取所有vid...")
                html = page.content()
                vid_matches = re.findall(r'["\']vid["\']\s*[:=]\s*["\']([a-zA-Z0-9]{8,})["\']', html)
                for vid in vid_matches:
                    if vid and vid != cid and vid not in vids:
                        vids.append(vid)
                print(f"  从HTML提取到 {len(vid_matches)} 个 vid，去重后 {len(vids)} 个")

            print(f"\n  总共提取到 {len(vids)} 个不重复的 vid")

            browser.close()

        if not vids:
            return {
                'success': False,
                'message': '未能从页面提取到任何vid',
                'data': None
            }

        episodes = []
        for i, vid in enumerate(vids):
            episodes.append({
                'episode_num': i + 1,
                'vid': vid,
                'url': f'https://v.qq.com/x/cover/{cid}/{vid}.html'
            })

        return {
            'success': True,
            'message': f'共找到 {len(episodes)} 集',
            'data': {
                'episodes': episodes,
                'cid': cid,
                'current_vid': current_vid,
                'total': len(episodes),
                'platform': '腾讯视频'
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'获取剧集列表失败: {str(e)}',
            'data': None
        }


if __name__ == "__main__":
    test_url = "https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html"
    print("=" * 60)
    print(f"测试URL: {test_url}")
    print("=" * 60)

    result = get_tencent_episode_list(test_url)

    print("\n" + "=" * 60)
    print("最终结果:")
    print("=" * 60)
    if result['success']:
        data = result['data']
        print(f"状态: 成功")
        print(f"cid: {data['cid']}")
        print(f"总集数: {data['total']}")
        print(f"\n剧集列表:")
        for ep in data['episodes']:
            print(f"  第{ep['episode_num']:2d}集 | vid: {ep['vid']} | {ep['url']}")
    else:
        print(f"状态: 失败")
        print(f"原因: {result['message']}")
