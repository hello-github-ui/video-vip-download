#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VIP 视频解析工具 - 统一入口

支持三种运行模式:
1. GUI 模式: python main.py 或 python main.py --gui
2. CLI 模式: python main.py --cli [参数]
3. Web 模式: python main.py --web

工程化设计说明:
- 入口层（main.py）: 负责参数解析和模式选择，不包含具体业务逻辑
- 核心层（video_parser.py）: 视频解析和下载的核心逻辑，独立于界面
- 界面层（gui.py/cli.py/web.py）: 三种用户界面实现，依赖核心层
"""

import sys


def print_help():
    """打印帮助信息"""
    help_text = """
🎥 VIP 视频解析工具 - 使用说明

运行模式:
  python main.py                      # 启动图形界面（默认）
  python main.py --gui                # 启动图形界面
  python main.py --cli [参数]          # 使用命令行模式
  python main.py --web                # 启动 Web 服务（默认端口 5000）
  python main.py --web --port 8080    # 指定 Web 端口

CLI 模式参数:
  -a <URL>       使用万能稳定解析(推荐)
  -b <URL>       使用夜幕解析
  -c <URL>       使用虾米解析
  -d <URL>       使用冰豆解析
  -e <URL>       使用JSON解析
  -f <URL>       使用m3u8解析
  -g <URL>       使用阳途解析
  -H <URL>       使用千奇解析
  -i <URL>       使用CK解析
  -l             列出所有可用解析线路
  -D <URL>       下载视频
  -q QUALITY     指定下载画质 (best/1080p/720p/480p/360p/worst)
  -o PATH        指定下载目录

使用示例:
  python main.py --cli -a https://v.qq.com/x/cover/xxx.html
  python main.py --cli -D https://www.bilibili.com/video/BVxxx -q 720p
  python main.py --cli -l
    """
    print(help_text)


def run_gui_mode():
    """启动图形界面模式"""
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
    """启动命令行模式"""
    try:
        sys.argv = ['vippj'] + cli_args
        from cli import main as cli_main
        cli_main()
        return 0
    except ImportError as e:
        print(f'导入命令行模块失败: {e}')
        return 1
    except SystemExit as e:
        return e.code if e.code else 0
    except Exception as e:
        print(f'命令行执行失败: {e}')
        return 1


def run_web_mode(args):
    """启动 Web 界面模式"""
    host = '127.0.0.1'
    port = 5000
    i = 0
    while i < len(args):
        if args[i] == '--host' and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == '--port' and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                print(f'无效的端口号: {args[i + 1]}')
                return 1
            i += 2
        else:
            i += 1
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
    """VIP 视频解析工具主入口"""
    if len(sys.argv) < 2:
        return run_gui_mode()

    mode = sys.argv[1]

    if mode == '--help' or mode == '-h':
        print_help()
        return 0
    elif mode == '--gui':
        return run_gui_mode()
    elif mode == '--cli':
        return run_cli_mode(sys.argv[2:])
    elif mode == '--web':
        return run_web_mode(sys.argv[2:])
    else:
        print(f'未知参数: {mode}')
        print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())