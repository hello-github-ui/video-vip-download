#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VIP 视频解析工具 - 统一入口

支持三种运行模式:
1. GUI 模式: python main.py --gui 或 python main.py
2. CLI 模式: python main.py --cli [参数]
3. Web 模式: python main.py --web

工程化设计说明:
- 入口层（main.py）: 负责参数解析和模式选择，不包含具体业务逻辑
- 核心层（video_parser.py）: 视频解析和下载的核心逻辑，独立于界面
- 界面层（gui.py/cli.py/web.py）: 三种用户界面实现，依赖核心层
- 这种分层设计使得:
  - 核心逻辑可被多种界面复用
  - 界面层可以独立替换和扩展
  - 符合单一职责和依赖倒置原则
"""

import argparse
import sys


def create_argument_parser():
    """
    创建命令行参数解析器
    
    Returns:
        argparse.ArgumentParser: 参数解析器对象
    """
    parser = argparse.ArgumentParser(
        prog='vip-video-parser',
        description='VIP 视频解析工具 - 支持多平台视频解析和下载',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # GUI 模式（默认）
  python main.py
  python main.py --gui

  # CLI 模式
  python main.py --cli -a https://v.qq.com/x/cover/xxx.html
  python main.py --cli -D https://www.bilibili.com/video/BVxxx -q 720p
  python main.py --cli -l  # 列出解析线路

  # Web 模式
  python main.py --web
  python main.py --web --port 8080
        '''
    )

    # 模式选择参数（互斥）
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--gui',
        action='store_true',
        default=True,
        help='启动图形界面模式（默认）'
    )
    mode_group.add_argument(
        '--cli',
        action='store_true',
        help='启动命令行模式'
    )
    mode_group.add_argument(
        '--web',
        action='store_true',
        help='启动 Web 界面模式'
    )

    # Web 模式参数
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Web 模式监听地址（默认 127.0.0.1）'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Web 模式监听端口（默认 5000）'
    )

    # CLI 模式参数（透传给 cli.py）
    # 这些参数只有在 --cli 模式下才有意义
    parser.add_argument(
        'cli_args',
        nargs='*',
        help='CLI 模式下的额外参数（如 -a URL, -D URL, -l 等）'
    )

    return parser


def run_gui_mode():
    """
    启动图形界面模式
    
    Returns:
        int: 退出码
    """
    try:
        from gui import main as gui_main
        gui_main()
        return 0
    except ImportError as e:
        print(f'导入图形界面模块失败: {e}')
        print('请确保已安装 PyQt5: pip install PyQt5')
        return 1
    except Exception as e:
        print(f'启动图形界面失败: {e}')
        return 1


def run_cli_mode(cli_args):
    """
    启动命令行模式
    
    Args:
        cli_args: CLI 参数列表
        
    Returns:
        int: 退出码
    """
    try:
        # CLI 使用 argparse，需要直接修改 sys.argv
        sys.argv = ['main.py'] + cli_args
        from cli import main as cli_main
        cli_main()
        return 0
    except ImportError as e:
        print(f'导入命令行模块失败: {e}')
        return 1
    except SystemExit as e:
        # argparse 会调用 sys.exit，捕获并返回退出码
        return e.code if e.code else 0
    except Exception as e:
        print(f'命令行执行失败: {e}')
        return 1


def run_web_mode(host, port):
    """
    启动 Web 界面模式
    
    Args:
        host: 监听地址
        port: 监听端口
        
    Returns:
        int: 退出码
    """
    try:
        from web import WebApp
        app = WebApp()
        app.run(host=host, port=port, debug=False)
        return 0
    except ImportError as e:
        print(f'导入 Web 模块失败: {e}')
        print('请确保已安装 Flask: pip install flask')
        return 1
    except Exception as e:
        print(f'启动 Web 服务失败: {e}')
        return 1


def main():
    """
    VIP 视频解析工具主入口
    
    根据命令行参数选择运行模式:
    - GUI 模式: 图形界面，适合普通用户
    - CLI 模式: 命令行，适合脚本和自动化
    - Web 模式: Web 界面，适合远程访问
    
    Returns:
        int: 退出码（0 成功，非0 失败）
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # 根据参数选择模式
    if args.cli:
        return run_cli_mode(args.cli_args)
    elif args.web:
        return run_web_mode(args.host, args.port)
    else:
        # 默认 GUI 模式
        return run_gui_mode()


if __name__ == '__main__':
    sys.exit(main())