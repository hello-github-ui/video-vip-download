#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys


def main():
    """
    VIP 视频解析工具主入口
    
    支持两种运行模式:
    1. 图形界面模式: python main.py 或 python main.py -g
    2. 命令行模式: python main.py -c [参数]
    
    命令行模式支持的参数:
    -a/-b/-c/-d/-e/-f/-g/-h/-i <URL>  : 使用对应解析线路解析视频
    -l                                  : 列出所有解析线路
    -D <URL>                            : 下载视频
    -N <URL>                            : 获取下一集并解析（支持腾讯、爱奇艺）
    -E <URL>                            : 获取剧集列表（支持腾讯、爱奇艺）
    -B <URL>                            : 批量下载电视剧全部剧集（支持腾讯、爱奇艺）
    -q QUALITY                          : 指定下载画质
    -o PATH                             : 指定下载目录
    -m N                                : 最大下载集数（配合-B使用）
    -n                                  : 解析后不自动打开浏览器
    """
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == '-g'):
        run_gui()
    elif len(sys.argv) >= 2 and sys.argv[1] == '-c':
        run_cli(sys.argv[2:])
    else:
        print_help()


def run_gui():
    """启动图形界面版本"""
    try:
        from gui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"❌ 导入图形界面模块失败: {e}")
        print("💡 请确保已安装 PyQt5: pip install PyQt5")
        sys.exit(1)


def run_cli(args):
    """启动命令行版本"""
    try:
        from cli import main as cli_main
        sys.argv = ['vippj'] + args
        cli_main()
    except ImportError as e:
        print(f"❌ 导入命令行模块失败: {e}")
        sys.exit(1)


def print_help():
    """打印帮助信息"""
    help_text = """
🎥 VIP 视频解析工具 - 使用说明

运行模式:
  python main.py           # 启动图形界面版本
  python main.py -g        # 启动图形界面版本
  python main.py -c [参数]  # 使用命令行模式

命令行模式参数:
  -a <URL>       使用万能稳定解析(推荐)
  -b <URL>       使用夜幕解析
  -c <URL>       使用虾米解析
  -d <URL>       使用冰豆解析
  -e <URL>       使用JSON解析
  -f <URL>       使用m3u8解析
  -g <URL>       使用阳途解析
  -h <URL>       使用千奇解析
  -i <URL>       使用CK解析
  -l             列出所有可用解析线路
  -D <URL>       下载视频
  -N <URL>       获取下一集并解析（支持腾讯、爱奇艺）
  -E <URL>       获取剧集列表（支持腾讯、爱奇艺）
  -B <URL>       批量下载电视剧全部剧集（支持腾讯、爱奇艺）
  -q QUALITY     指定下载画质 (best/1080p/720p/480p/360p/worst)
  -o PATH        指定下载目录
  -m N           最大下载集数（配合-B使用）
  -n             解析后不自动打开浏览器

使用示例:
  python main.py -c -b https://v.qq.com/x/cover/mzc00200q0y2d9q.html
  python main.py -c -l
  python main.py -c -D https://www.bilibili.com/video/BV1xx411c7mZ -q 720p
  python main.py -c -N https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html
  python main.py -c -E https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html
  python main.py -c -B https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html -o ~/Downloads -m 5

支持平台:
  腾讯视频、优酷、哔哩哔哩、爱奇艺、芒果TV、搜狐视频等
    """
    print(help_text)


if __name__ == '__main__':
    main()
