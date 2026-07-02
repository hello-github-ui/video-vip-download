#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys

from video_parser import VideoParser


class CLI:
    """
    命令行界面类
    提供视频解析的命令行操作接口
    """

    def __init__(self):
        """初始化命令行解析器"""
        self.parser = VideoParser()
        self.args = None

    def parse_args(self):
        """
        解析命令行参数
        
        Returns:
            argparse.Namespace: 解析后的参数对象
        """
        parser = argparse.ArgumentParser(
            prog='vippj',
            description='VIP 视频解析工具 - 支持多平台视频解析和下载',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用示例:
  vippj -a https://v.qq.com/x/cover/mzc00200q0y2d9q.html
  vippj -b https://www.bilibili.com/video/BV1xx411c7mZ
  vippj -c https://www.iqiyi.com/v_19rr7qvl6w.html
  vippj -l                          # 列出所有可用解析线路
  vippj -d https://xxx.com/video    # 下载视频（默认最佳画质）
  vippj -d https://xxx.com/video -q 720p  # 指定画质下载
            """
        )

        group = parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            '-a', '--api-a',
            metavar='URL',
            help='使用万能稳定解析(推荐)'
        )

        group.add_argument(
            '-b', '--api-b',
            metavar='URL',
            help='使用夜幕解析(已不可用)'
        )

        group.add_argument(
            '-c', '--api-c',
            metavar='URL',
            help='使用虾米解析'
        )

        group.add_argument(
            '-d', '--api-d',
            metavar='URL',
            help='使用冰豆解析'
        )

        group.add_argument(
            '-e', '--api-e',
            metavar='URL',
            help='使用JSON解析'
        )

        group.add_argument(
            '-f', '--api-f',
            metavar='URL',
            help='使用m3u8解析(已不可用)'
        )

        group.add_argument(
            '-g', '--api-g',
            metavar='URL',
            help='使用阳途解析'
        )

        group.add_argument(
            '-H', '--api-H',
            metavar='URL',
            help='使用千奇解析'
        )

        group.add_argument(
            '-i', '--api-i',
            metavar='URL',
            help='使用CK解析'
        )

        group.add_argument(
            '-l', '--list',
            action='store_true',
            help='列出所有可用的解析线路'
        )

        group.add_argument(
            '-D', '--download',
            metavar='URL',
            help='下载视频'
        )

        group.add_argument(
            '-N', '--next',
            metavar='URL',
            help='获取下一集并解析（支持腾讯、爱奇艺）'
        )

        group.add_argument(
            '-E', '--episodes',
            metavar='URL',
            help='获取剧集列表（支持腾讯、爱奇艺）'
        )

        group.add_argument(
            '-B', '--batch',
            metavar='URL',
            help='批量下载电视剧全部剧集（支持腾讯、爱奇艺）'
        )

        parser.add_argument(
            '-q', '--quality',
            metavar='QUALITY',
            default='best',
            choices=['best', 'worst', '1080p', '720p', '480p', '360p'],
            help='下载画质选择，默认best'
        )

        parser.add_argument(
            '-o', '--output',
            metavar='PATH',
            default=None,
            help='下载输出目录'
        )

        parser.add_argument(
            '-m', '--max',
            metavar='N',
            type=int,
            default=None,
            help='最大下载集数，默认下载全部'
        )

        parser.add_argument(
            '-n', '--no-open',
            action='store_true',
            help='解析后不自动打开浏览器'
        )

        self.args = parser.parse_args()
        return self.args

    def get_api_key(self):
        """
        根据命令行参数获取解析线路标识
        
        Returns:
            str: 解析线路标识
        """
        if self.args.api_a:
            return 'a', self.args.api_a
        elif self.args.api_b:
            return 'b', self.args.api_b
        elif self.args.api_c:
            return 'c', self.args.api_c
        elif self.args.api_d:
            return 'd', self.args.api_d
        elif self.args.api_e:
            return 'e', self.args.api_e
        elif self.args.api_f:
            return 'f', self.args.api_f
        elif self.args.api_g:
            return 'g', self.args.api_g
        elif self.args.api_H:
            return 'h', self.args.api_H
        elif self.args.api_i:
            return 'i', self.args.api_i
        return None, None

    def print_api_list(self):
        """打印所有解析线路列表"""
        apis = self.parser.get_all_apis()

        print("\n" + "=" * 60)
        print("📡 可用解析线路列表")
        print("=" * 60)

        print(f"{'序号':<6} {'接口名称':<12} {'状态':<8} {'备注':<15}")
        print("-" * 60)

        for key, api in apis.items():
            status = '✅ 可用' if api['status'] == 'active' else '❌ 不可用'
            note = api['note'] if api['note'] else '-'

            print(f"{key:<6} {api['name']:<12} {status:<8} {note:<15}")

        print("=" * 60)
        print("\n使用示例:")
        print("  vippj -b https://v.qq.com/x/cover/mzc00200q0y2d9q.html")
        print("  vippj -c https://www.bilibili.com/video/BV1xx411c7mZ")
        print()

    def run(self):
        """
        执行命令行操作
        
        Returns:
            int: 退出码，0表示成功，非0表示失败
        """
        try:
            self.parse_args()

            if self.args.list:
                self.print_api_list()
                return 0

            if self.args.download:
                return self.handle_download()

            if self.args.next:
                return self.handle_next_episode()

            if self.args.episodes:
                return self.handle_episode_list()

            if self.args.batch:
                return self.handle_batch_download()

            api_key, video_url = self.get_api_key()
            if api_key is None or video_url is None:
                print("❌ 无效的参数组合")
                return 1

            return self.handle_parse(api_key, video_url)

        except KeyboardInterrupt:
            print("\n\n⏹️ 用户中断操作")
            return 0
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")
            return 1

    def handle_parse(self, api_key, video_url):
        """
        处理视频解析请求
        
        Args:
            api_key (str): 解析线路标识
            video_url (str): 视频链接
            
        Returns:
            int: 退出码
        """
        print(f"\n🔍 正在解析视频: {video_url}")
        # 转换字符串索引为列表索引
        api_index = ord(api_key.lower()) - ord('a')
        api_name = self.parser.parse_apis[api_index]['name'] if 0 <= api_index < len(self.parser.parse_apis) else api_key
        print(f"📡 使用解析线路: {api_name}")

        result = self.parser.parse_url(video_url, api_key)

        if result['success']:
            parsed_url = result['data']['parsed_url']

            print("\n✅ 解析成功!")
            print(f"🔗 解析链接: {parsed_url}")
            print(f"📺 平台: {self.parser.detect_platform(video_url)}")

            if not self.args.no_open:
                print("\n🌐 正在打开浏览器...")
                if self.parser.open_in_browser(parsed_url):
                    print("✅ 浏览器已打开")
                else:
                    print("❌ 打开浏览器失败，请手动复制链接")

            return 0
        else:
            print(f"\n❌ 解析失败: {result['message']}")
            return 1

    def handle_download(self):
        """
        处理视频下载请求
        
        Returns:
            int: 退出码
        """
        video_url = self.args.download
        quality = self.args.quality
        output_path = self.args.output

        print(f"\n📥 准备下载视频: {video_url}")
        print(f"🎬 画质选择: {quality}")
        if output_path:
            print(f"📁 输出目录: {output_path}")

        result = self.parser.download_video(video_url, output_path, quality, video_url)

        if result['success']:
            print(f"\n✅ {result['message']}")
            print(f"📁 保存位置: {result['data']['output_path']}")
            return 0
        else:
            print(f"\n❌ {result['message']}")
            return 1

    def handle_next_episode(self):
        """
        处理获取下一集请求
        
        Returns:
            int: 退出码
        """
        current_url = self.args.next
        platform = self.parser.detect_platform(current_url)

        print(f"\n⏭️ 正在获取下一集: {current_url}")
        print(f"📺 平台: {platform}")

        result = self.parser.get_next_episode(current_url)

        if result['success']:
            next_url = result['data']['next_url']
            episode_num = result['data']['episode_num']

            print(f"\n✅ 找到下一集：第{episode_num}集")
            print(f"🔗 下一集链接: {next_url}")

            # 自动解析下一集
            print("\n🔍 正在自动解析下一集...")
            api_key = 'a'  # 使用默认解析线路
            parse_result = self.parser.parse_url(next_url, api_key)

            if parse_result['success']:
                parsed_url = parse_result['data']['parsed_url']
                print(f"\n✅ 解析成功!")
                print(f"🔗 解析链接: {parsed_url}")

                if not self.args.no_open:
                    print("\n🌐 正在打开浏览器...")
                    if self.parser.open_in_browser(parsed_url):
                        print("✅ 浏览器已打开")
                    else:
                        print("❌ 打开浏览器失败，请手动复制链接")

                return 0
            else:
                print(f"\n❌ 解析失败: {parse_result['message']}")
                return 1
        else:
            print(f"\n❌ {result['message']}")
            return 1

    def handle_episode_list(self):
        """
        处理获取剧集列表请求

        Returns:
            int: 退出码
        """
        video_url = self.args.episodes
        platform = self.parser.detect_platform(video_url)

        print(f"\n📋 正在获取剧集列表: {video_url}")
        print(f"📺 平台: {platform}")

        result = self.parser.get_episode_list(video_url)

        if result['success']:
            episodes = result['data']['episodes']

            print(f"\n✅ 共找到 {len(episodes)} 集")
            print("\n" + "-" * 60)
            print(f"{'集数':<8} {'链接/ID':<50}")
            print("-" * 60)

            for ep in episodes[:20]:  # 最多显示20集
                ep_num = ep.get('episode_num', '?')
                url = ep.get('url', '') or ep.get('vid', '')
                print(f"{ep_num:<8} {url:<50}")

            if len(episodes) > 20:
                print(f"... 还有 {len(episodes) - 20} 集")

            print("-" * 60)
            return 0
        else:
            print(f"\n❌ {result['message']}")
            return 1

    def handle_batch_download(self):
        """
        处理批量下载请求

        Returns:
            int: 退出码
        """
        video_url = self.args.batch
        quality = self.args.quality
        output_path = self.args.output
        max_episodes = self.args.max

        platform = self.parser.detect_platform(video_url)

        print(f"\n📥 开始批量下载电视剧")
        print(f"🔗 起始链接: {video_url}")
        print(f"📺 平台: {platform}")
        print(f"🎬 画质: {quality}")
        if output_path:
            print(f"📁 输出目录: {output_path}")
        if max_episodes:
            print(f"📊 最大下载集数: {max_episodes}")

        if platform not in ['腾讯视频', '爱奇艺']:
            print(f"\n❌ 暂不支持{platform}的批量下载")
            return 1

        def progress_callback(episode_num, total, status, message):
            if status == 'success':
                print(f"  ✅ {message}")
            elif status == 'failed':
                print(f"  ❌ {message}")
            else:
                print(f"  ⏳ {message}")

        result = self.parser.batch_download(
            video_url,
            output_path,
            quality,
            'a',  # 默认使用万能稳定解析
            max_episodes,
            progress_callback
        )

        if result['success']:
            data = result['data']
            print(f"\n✅ 批量下载完成!")
            print(f"📊 统计: 成功 {len(data['downloaded'])} 集 / 失败 {len(data['failed'])} 集 / 总计 {data['total']} 集")
            print(f"📁 保存位置: {data['output_path']}")

            if data['failed']:
                print(f"\n⚠️ 以下集数下载失败:")
                for item in data['failed']:
                    print(f"  第{item['episode']}集: {item['reason']}")

            return 0
        else:
            print(f"\n❌ {result['message']}")
            return 1


def main():
    """命令行入口函数"""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
