import os
import platform
import re
import subprocess
import sys
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup
from api import parse_apis

class VideoParser:
    """
    视频解析核心类
    支持多种解析线路，提供视频解析和下载功能
    """

    # ffmpeg 下载地址（使用 gyany.dev 的官方构建，稳定可靠）
    FFMPEG_DOWNLOAD_URLS = {
        'Windows': 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
        'Darwin': 'https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip',  # macOS
        'Linux': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz'
    }

    def __init__(self):
        """初始化解析器，定义支持的解析线路"""
        # 以下属性暂不使用，已注释
        # self._ffmpeg_path = None
        # self._m3u8_url = None
        # self._context = None
        # self._page = None
        # self._playwright = None
        # 获取最新可用的api解析接口
        self.parse_apis = parse_apis()

        self.supported_platforms = {
            '腾讯视频': ['v.qq.com', 'qq.com'],
            '优酷': ['youku.com', 'ykimg.com'],
            '哔哩哔哩': ['bilibili.com', 'b23.tv'],
            '爱奇艺': ['iqiyi.com', 'iq.com'],
            '芒果TV': ['mgtv.com'],
            '搜狐视频': ['sohu.com'],
            'PP视频': ['ppvideo.com'],
            '乐视视频': ['le.com'],
            '土豆视频': ['tudou.com'],
            'AcFun': ['acfun.cn']
        }

    def get_active_apis(self):
        """获取可用的解析接口"""
        return {key: api for key, api in self.parse_apis.items() if api['status'] == 'active'}

    def is_valid_url(self, url):
        """
        验证URL是否有效，严格说是验证url中必须有scheme和（主机和端口）
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def detect_platform(self, url):
        """
        检测视频URL所属平台
        """
        for platform, domains in self.supported_platforms.items():
            for domain in domains:
                if domain in url:
                    return platform
        return '其他'

    def parse_url(self, video_url, api):
        """
        根据选择的解析线路生成解析链接
        """
        if not self.is_valid_url(video_url):
            return {
                'success': False,
                'message': '无效的视频链接',
                'data': None
            }

        if api not in self.parse_apis:
            return {
                'success': False,
                'message': '无效的解析线路选择',
                'data': None
            }

        api_info = api

        if api_info['status'] == 'deprecated':
            return {
                'success': False,
                'message': f"{api_info['name']}已不可用，请选择其他线路",
                'data': None
            }

        encoded_url = quote(video_url, safe='')
        parsed_url = api_info['url'] + encoded_url

        return {
            'success': True,
            'message': f"已使用{api_info['name']}解析",
            'data': {
                'original_url': video_url,
                'parsed_url': parsed_url,
                'api_name': api_info['name'],
                'api': api_info
            }
        }

    def open_in_browser(self, url):
        """
        在浏览器中打开链接
        """
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"打开默认浏览器失败: {str(e)}")
            return False

    def _get_program_dir(self):
        """获取程序目录"""
        if getattr(sys, 'frozen', False):
            # 打包后的 exe
            return os.path.dirname(sys.executable)
        else:
            # 开发环境
            return os.path.dirname(os.path.abspath(__file__))

    # ==================== ffmpeg 相关功能（暂不使用，已注释） ====================
    '''
    def _download_ffmpeg(self):
        """
        自动下载 ffmpeg 到程序目录

        Returns:
            str: 下载后的 ffmpeg 可执行文件路径，None 表示下载失败
        """
        import shutil
        import tempfile

        system = platform.system()
        download_url = self.FFMPEG_DOWNLOAD_URLS.get(system)
        if not download_url:
            print(f"不支持自动下载 ffmpeg: {system}")
            return None

        program_dir = self._get_program_dir()
        ffmpeg_target = os.path.join(program_dir, 'ffmpeg.exe' if system == 'Windows' else 'ffmpeg')

        try:
            print(f"下载 ffmpeg: {download_url}")
            print("这可能需要几分钟，请耐心等待...")

            # 下载到临时目录
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, 'ffmpeg.zip')

            # 流式下载，显示进度
            response = requests.get(download_url, stream=True, timeout=300)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int(50 * downloaded / total_size)
                            print(f"\r下载进度: [{('#' * progress).ljust(50)}] {int(100 * downloaded / total_size)}%",
                                  end='', flush=True)

            print("\n下载完成，正在解压...")

            # 解压 zip 文件
            if system == 'Windows':
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # 找到 ffmpeg.exe
                    for file in zip_ref.namelist():
                        if file.endswith('ffmpeg.exe'):
                            # 解压到临时目录
                            zip_ref.extract(file, temp_dir)
                            extracted_path = os.path.join(temp_dir, file)
                            # 复制到程序目录
                            shutil.copy2(extracted_path, ffmpeg_target)
                            print(f"ffmpeg 已安装到: {ffmpeg_target}")
                            break
            else:
                # Linux/MacOS 需要额外处理 tar.xz
                import tarfile
                tar_path = os.path.join(temp_dir, 'ffmpeg.tar.xz')
                shutil.move(zip_path, tar_path)
                with tarfile.open(tar_path, 'r:xz') as tar:
                    for member in tar.getmembers():
                        if member.name.endswith('ffmpeg'):
                            tar.extract(member, temp_dir)
                            extracted_path = os.path.join(temp_dir, member.name)
                            shutil.copy2(extracted_path, ffmpeg_target)
                            os.chmod(ffmpeg_target, 0o755)
                            print(f"ffmpeg 已安装到: {ffmpeg_target}")
                            break

            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)

            if os.path.exists(ffmpeg_target):
                return ffmpeg_target
            else:
                print("解压后未找到 ffmpeg 可执行文件")
                return None

        except requests.exceptions.Timeout:
            print("下载超时，请检查网络连接")
            return None
        except requests.exceptions.RequestException as e:
            print(f"下载失败: {str(e)}")
            return None
        except zipfile.BadZipFile:
            print("下载的文件损坏，请重试")
            return None
        except Exception as e:
            print(f"安装 ffmpeg 时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _check_ffmpeg_available(self):
        """检查 ffmpeg 是否可用"""
        return self._get_ffmpeg_path() is not None

    def _get_ffmpeg_executable(self):
        """获取 ffmpeg 可执行文件路径（供外部调用）"""
        return self._get_ffmpeg_path()
    '''

    def download_video(self, video_url, output_path=None, quality='best', original_url=None):
        """
        使用 yt-dlp 下载视频（直接下载原始视频URL）

        Args:
            video_url (str): 视频链接（原始视频链接）
            output_path (str): 输出目录，默认为当前目录
            quality (str): 视频质量
            original_url (str): 原始视频链接（保留参数，兼容调用）

        Returns:
            dict: 下载结果
            
        日志输出说明：
            所有 print 输出都会被全局 LogStream 拦截（在 gui.py 中设置），
            用户勾选"显示详细日志"后会显示在 GUI 的解析结果文本框中。
            这里直接用 print 输出即可，不需要额外的回调机制。
        """
        # 优先使用 original_url（原始视频链接，如腾讯视频页面URL）
        # 因为 yt-dlp 直接支持各大视频平台的原始链接解析
        actual_url = original_url if original_url else video_url

        if not self.is_valid_url(actual_url):
            msg = '无效的视频链接'
            print(msg)
            return {
                'success': False,
                'message': msg,
                'data': None
            }

        if output_path is None:
            output_path = os.getcwd()

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        print(f"\n开始下载: {actual_url}")
        print(f"保存目录: {output_path}")
        print(f"画质: {quality}")

        # 构建 yt-dlp 命令，直接下载原始视频URL
        cmd = self._build_yt_dlp_cmd(actual_url, output_path, quality, actual_url)

        try:
            print(f"执行命令: {' '.join(cmd)}")

            # 使用 Popen 实时读取输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=output_path,
                bufsize=1,
                universal_newlines=True
            )

            output_lines = []
            for line in process.stdout:
                line = line.rstrip('\n\r')
                output_lines.append(line)
                print(line)

            process.wait()
            returncode = process.returncode

            if returncode == 0:
                return {
                    'success': True,
                    'message': '视频下载成功（yt-dlp）',
                    'data': {
                        'output_path': output_path,
                        'stdout': '\n'.join(output_lines)
                    }
                }
            else:
                error_msg = '\n'.join(output_lines[-20:]) if output_lines else '未知错误'
                print(f"下载失败: {error_msg[:500]}")
                return {
                    'success': False,
                    'message': f'下载失败: {error_msg[:500]}',
                    'data': None
                }
        except FileNotFoundError:
            msg = '未找到 yt-dlp，请确保已安装（pip install yt-dlp）'
            print(msg)
            return {
                'success': False,
                'message': msg,
                'data': None
            }
        except Exception as e:
            msg = f'下载过程发生错误: {str(e)}'
            print(msg)
            return {
                'success': False,
                'message': msg,
                'data': None
            }

    def _build_yt_dlp_cmd(self, actual_url, output_path, quality, referer_url):
        """构建 yt-dlp 命令"""
        quality_map = {
            'best': 'best',
            'worst': 'worst',
            '1080p': 'best[height<=1080]',
            '720p': 'best[height<=720]',
            '480p': 'best[height<=480]',
            '360p': 'best[height<=360]'
        }
        format_spec = quality_map.get(quality, 'best')

        cmd = [
            'yt-dlp',
            '-f', format_spec,
            '-o', os.path.join(output_path, '%(title)s.%(ext)s'),
            '--merge-output-format', 'mp4',
            '--no-warnings',
            '--retries', '10',
            '--fragment-retries', '10',
            '--no-check-certificate',
            '--no-playlist',
            '--user-agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--referer', referer_url,
            actual_url
        ]

        return cmd

    # ==================== 以下功能暂不使用，已注释 ====================
    # 包含: ffmpeg下载、m3u8路径修复、批量下载、获取下一集、剧集列表等
    '''
    def _download_with_ffmpeg(self, m3u8_url, output_path, referer_url=None):
        """
        使用 ffmpeg 下载 m3u8 视频

        Args:
            m3u8_url (str): m3u8 视频地址
            output_path (str): 输出目录
            referer_url (str): Referer 地址，可选

        Returns:
            dict: 下载结果
        """
        ffmpeg_path = self._get_ffmpeg_path()
        if not ffmpeg_path:
            return {
                'success': False,
                'message': 'ffmpeg 不可用',
                'data': None
            }

        try:
            output_file = os.path.join(output_path, 'video_download.mp4')

            # 先下载 m3u8 文件并修复相对路径
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            if referer_url:
                headers['Referer'] = referer_url

            print("正在下载并修复 m3u8 文件...")
            m3u8_response = requests.get(m3u8_url, headers=headers, timeout=30)
            if m3u8_response.status_code != 200:
                return {
                    'success': False,
                    'message': f'获取 m3u8 文件失败: HTTP {m3u8_response.status_code}',
                    'data': None
                }

            m3u8_content = m3u8_response.text
            base_url = m3u8_url.rsplit('/', 1)[0] + '/'
            m3u8_abs_path = self._fix_m3u8_relative_paths(m3u8_content, base_url)

            # 保存修复后的 m3u8 文件
            fixed_m3u8_path = os.path.join(output_path, 'video_fixed.m3u8')
            with open(fixed_m3u8_path, 'w', encoding='utf-8') as f:
                f.write(m3u8_abs_path)

            print(f"已修复 m3u8 文件，保存到: {fixed_m3u8_path}")

            cmd = [
                ffmpeg_path,
                '-user_agent',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]

            if referer_url:
                cmd.extend(['-headers', f'Referer: {referer_url}\r\n'])

            cmd.extend([
                '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
                '-i', fixed_m3u8_path,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-y',
                output_file
            ])

            print(f"执行ffmpeg命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=output_path
            )

            # 清理临时文件
            if os.path.exists(fixed_m3u8_path):
                os.remove(fixed_m3u8_path)

            if result.returncode == 0:
                return {
                    'success': True,
                    'message': '视频下载成功（通过ffmpeg）',
                    'data': {
                        'output_path': output_file,
                        'stdout': result.stdout
                    }
                }
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                return {
                    'success': False,
                    'message': f'ffmpeg下载失败: {error_msg}',
                    'data': None
                }
        except FileNotFoundError:
            return {
                'success': False,
                'message': '未找到ffmpeg，请确保已安装',
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'ffmpeg下载过程发生错误: {str(e)}',
                'data': None
            }

    def _fix_m3u8_relative_paths(self, m3u8_content, base_url):
        """
        修复 m3u8 文件中的相对路径，转换为绝对路径

        Args:
            m3u8_content (str): m3u8 文件内容
            base_url (str): 基础URL（用于拼接相对路径）

        Returns:
            str: 修复后的 m3u8 内容
        """
        from urllib.parse import urljoin

        lines = m3u8_content.split('\n')
        fixed_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                fixed_lines.append('')
                continue

            # 注释行保留原样
            if line.startswith('#'):
                fixed_lines.append(line)
                continue

            # URL行，处理相对路径
            url = line
            if not url.startswith('http'):
                # 处理各种相对路径情况
                if url.startswith('//'):
                    # 协议相对路径: //example.com/path
                    url = 'https:' + url
                elif url.startswith('/'):
                    # 绝对路径: /path
                    parsed = urlparse(base_url)
                    url = f"{parsed.scheme}://{parsed.netloc}{url}"
                else:
                    # 相对路径: path
                    url = urljoin(base_url, url)

            fixed_lines.append(url)

        return '\n'.join(fixed_lines)

    # ==================== 批量下载功能 ====================

    def batch_download(self, start_url, output_path, quality='best', api_key='a',
                       max_episodes=None, progress_callback=None, max_workers=3):
        """
        批量下载电视剧所有剧集（支持多线程并发下载）
        
        Args:
            start_url (str): 起始视频链接
            output_path (str): 下载保存目录
            quality (str): 视频质量
            api_key (str): 解析线路
            max_episodes (int): 最大下载集数，None表示全部
            progress_callback (callable): 进度回调函数，接收(episode_num, total, status, message)
            max_workers (int): 最大并发下载线程数，默认3
            
        Returns:
            dict: 批量下载结果
        """
        if not output_path:
            output_path = os.getcwd()

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        platform = self.detect_platform(start_url)

        if platform not in ['腾讯视频', '爱奇艺']:
            return {
                'success': False,
                'message': f'暂不支持{platform}的批量下载',
                'data': None
            }

        # 获取剧集列表
        list_result = self.get_episode_list(start_url)
        if not list_result['success']:
            return {
                'success': False,
                'message': f'获取剧集列表失败: {list_result["message"]}',
                'data': None
            }

        episodes = list_result['data']['episodes']

        if not episodes:
            return {
                'success': False,
                'message': '未找到任何剧集',
                'data': None
            }

        # 限制下载集数
        if max_episodes and max_episodes > 0:
            episodes = episodes[:max_episodes]

        total = len(episodes)
        downloaded = []
        failed = []
        completed_count = 0

        def download_single_episode(ep):
            """下载单集，返回结果字典"""
            ep_num = ep.get('episode_num', 0)
            ep_url = ep.get('url', '')

            if not ep_url:
                return {'success': False, 'episode': ep_num, 'reason': '无有效链接'}

            try:
                # 解析视频
                parse_result = self.parse_url(ep_url, api_key)
                if not parse_result['success']:
                    return {'success': False, 'episode': ep_num, 'reason': parse_result['message']}

                parsed_url = parse_result['data']['parsed_url']

                # 下载视频
                download_result = self.download_video(
                    parsed_url,
                    output_path=output_path,
                    quality=quality,
                    original_url=ep_url
                )

                if download_result['success']:
                    return {'success': True, 'episode': ep_num, 'url': ep_url}
                else:
                    return {'success': False, 'episode': ep_num, 'reason': download_result['message']}
            except Exception as e:
                return {'success': False, 'episode': ep_num, 'reason': str(e)}

        if progress_callback:
            progress_callback(0, total, 'start', f'开始批量下载，共{total}集，并发数:{max_workers}')

        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(download_single_episode, ep): ep
                for ep in episodes
            }

            for future in as_completed(futures):
                result = future.result()
                completed_count += 1
                ep_num = result['episode']

                if result['success']:
                    downloaded.append({'episode': ep_num, 'url': futures[future].get('url', '')})
                    if progress_callback:
                        progress_callback(
                            completed_count, total, 'success',
                            f'第{ep_num}集下载成功 ({completed_count}/{total})'
                        )
                else:
                    failed.append({'episode': ep_num, 'reason': result['reason']})
                    if progress_callback:
                        progress_callback(
                            completed_count, total, 'failed',
                            f'第{ep_num}集下载失败: {result["reason"]} ({completed_count}/{total})'
                        )

        return {
            'success': len(failed) < total,
            'message': f'下载完成：成功{len(downloaded)}集，失败{len(failed)}集，共{total}集',
            'data': {
                'downloaded': downloaded,
                'failed': failed,
                'total': total,
                'output_path': output_path,
                'platform': platform,
                'max_workers': max_workers
            }
        }

    # ==================== 自动获取下一集功能 ====================

    def get_next_episode(self, current_url):
        """
        根据当前视频URL自动获取下一集URL
        """
        platform = self.detect_platform(current_url)

        if platform == '腾讯视频':
            return self._get_qq_next_episode(current_url)
        elif platform == '爱奇艺':
            return self._get_iqiyi_next_episode(current_url)
        else:
            return {
                'success': False,
                'message': f'暂不支持{platform}的自动获取下一集功能',
                'data': None
            }

    def _get_qq_next_episode(self, current_url):
        """获取腾讯视频下一集（使用 Playwright 获取完整剧集列表）"""
        try:
            match = re.search(r'/x/cover/([^/]+)/([^/\.]+)\.html', current_url)
            if not match:
                return {
                    'success': False,
                    'message': '无法解析腾讯视频URL格式',
                    'data': None
                }

            cid = match.group(1)
            current_vid = match.group(2)

            # 获取完整剧集列表
            list_result = self._get_qq_episode_list(current_url)
            if not list_result['success']:
                return {
                    'success': False,
                    'message': f'获取剧集列表失败: {list_result["message"]}',
                    'data': None
                }

            episodes = list_result['data']['episodes']
            if not episodes:
                return {
                    'success': False,
                    'message': '未找到任何剧集',
                    'data': None
                }

            # 找到当前剧集的位置
            current_index = -1
            for i, ep in enumerate(episodes):
                if ep['vid'] == current_vid:
                    current_index = i
                    break

            # 如果找不到当前vid，默认为第一集
            if current_index == -1:
                current_index = 0

            # 检查是否有下一集
            if current_index + 1 < len(episodes):
                next_ep = episodes[current_index + 1]
                return {
                    'success': True,
                    'message': f'找到下一集：第{next_ep["episode_num"]}集',
                    'data': {
                        'next_url': next_ep['url'],
                        'next_vid': next_ep['vid'],
                        'episode_num': next_ep['episode_num'],
                        'current_episode': episodes[current_index]['episode_num'],
                        'total_episodes': len(episodes),
                        'platform': '腾讯视频'
                    }
                }

            return {
                'success': False,
                'message': '未找到下一集，可能当前已是最后一集',
                'data': {
                    'current_vid': current_vid,
                    'current_episode': episodes[current_index]['episode_num'] if current_index < len(episodes) else 1,
                    'total_episodes': len(episodes),
                    'platform': '腾讯视频'
                }
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'获取腾讯视频下一集失败: {str(e)}',
                'data': None
            }

    def _get_iqiyi_next_episode(self, current_url):
        """获取爱奇艺下一集"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.iqiyi.com/'
            }

            response = requests.get(current_url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            html = response.text

            album_id_match = re.search(r'albumId["\']?\s*[:=]\s*["\']?(\d+)["\']?', html)
            album_id = album_id_match.group(1) if album_id_match else None

            tv_id_match = re.search(r'tvId["\']?\s*[:=]\s*["\']?(\d+)["\']?', html)
            tv_id = tv_id_match.group(1) if tv_id_match else None

            current_ep_match = re.search(r'(第\s*(\d+)\s*集|EP(\d+)|episode["\']?\s*[:=]\s*["\']?(\d+))', html)
            current_ep = None
            if current_ep_match:
                for g in current_ep_match.groups():
                    if g and g.isdigit():
                        current_ep = int(g)
                        break

            if not album_id:
                album_match = re.search(r'href=["\'](https?://www\.iqiyi\.com/a_[^"\']+)["\']', html)
                if album_match:
                    album_url = album_match.group(1)
                    album_id_match2 = re.search(r'a_(\w+)\.html', album_url)
                    if album_id_match2:
                        album_id = album_id_match2.group(1)

            episodes = []

            if album_id and album_id.isdigit():
                try:
                    api_url = f'https://pcw-api.iqiyi.com/albums/album/avlistinfo?aid={album_id}&page=1&size=50'
                    api_response = requests.get(api_url, headers=headers, timeout=10)
                    api_data = api_response.json()

                    if api_data.get('data') and api_data['data'].get('epsodelist'):
                        for ep in api_data['data']['epsodelist']:
                            episodes.append({
                                'tv_id': str(ep.get('tvId', '')),
                                'episode_num': ep.get('order', 0),
                                'title': ep.get('name', ''),
                                'url': ep.get('playUrl', '')
                            })
                except Exception as e:
                    print(f"爱奇艺API请求失败: {e}")

            if not episodes:
                ep_links = re.findall(
                    r'href=["\'](https?://www\.iqiyi\.com/v_\w+\.html)["\'][^>]*>\s*(?:<[^>]+>)*\s*(\d+)\s*(?:<[^>]+>)*\s*</a>',
                    html)
                for url, num in ep_links:
                    episodes.append({
                        'url': url,
                        'episode_num': int(num),
                        'tv_id': ''
                    })

                if not episodes:
                    ep_data = re.findall(
                        r'data-episode=["\'](\d+)["\'][^>]*href=["\'](https?://www\.iqiyi\.com/v_\w+\.html)["\']', html)
                    for num, url in ep_data:
                        episodes.append({
                            'url': url,
                            'episode_num': int(num),
                            'tv_id': ''
                        })

            seen_urls = set()
            unique_episodes = []
            for ep in episodes:
                url_key = ep.get('url', '') or ep.get('tv_id', '')
                if url_key and url_key not in seen_urls:
                    seen_urls.add(url_key)
                    unique_episodes.append(ep)

            unique_episodes.sort(key=lambda x: x['episode_num'])

            current_index = -1
            for i, ep in enumerate(unique_episodes):
                ep_url = ep.get('url', '')
                ep_tv_id = ep.get('tv_id', '')
                if current_url in ep_url or ep_tv_id == tv_id or ep['episode_num'] == current_ep:
                    current_index = i
                    break

            if current_index == -1:
                vid_match = re.search(r'v_(\w+)\.html', current_url)
                if vid_match:
                    current_vid = vid_match.group(1)
                    for i, ep in enumerate(unique_episodes):
                        ep_url = ep.get('url', '')
                        if current_vid in ep_url:
                            current_index = i
                            break

            if current_index >= 0 and current_index + 1 < len(unique_episodes):
                next_ep = unique_episodes[current_index + 1]
                next_url = next_ep.get('url', '')

                if not next_url and next_ep.get('tv_id'):
                    next_url = f'https://www.iqiyi.com/v_{next_ep["tv_id"]}.html'

                return {
                    'success': True,
                    'message': f'找到下一集：第{next_ep["episode_num"]}集',
                    'data': {
                        'next_url': next_url,
                        'episode_num': next_ep['episode_num'],
                        'title': next_ep.get('title', ''),
                        'current_episode': unique_episodes[current_index]['episode_num'],
                        'total_episodes': len(unique_episodes),
                        'platform': '爱奇艺'
                    }
                }

            return {
                'success': False,
                'message': '未找到下一集，可能当前已是最后一集或页面结构已变更',
                'data': {
                    'current_url': current_url,
                    'episodes_found': len(unique_episodes),
                    'platform': '爱奇艺'
                }
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'获取爱奇艺下一集失败: {str(e)}',
                'data': None
            }

    def get_episode_list(self, video_url):
        """
        获取视频的所有剧集列表
        """
        platform = self.detect_platform(video_url)

        if platform == '腾讯视频':
            return self._get_qq_episode_list(video_url)
        elif platform == '爱奇艺':
            return self._get_iqiyi_episode_list(video_url)
        else:
            return {
                'success': False,
                'message': f'暂不支持{platform}的剧集列表获取',
                'data': None
            }

    def _get_qq_episode_list(self, video_url):
        """
        获取腾讯视频完整剧集列表（使用 Playwright）

        原理：
        1. 使用 Playwright 加载页面，等待页面完全渲染
        2. 从页面的剧集列表元素(dt-params属性)中提取所有vid和集数
        3. 自动切换分页获取所有剧集
        4. 使用 cid + vid 拼接每一集的完整URL
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
            match = re.search(r'/x/cover/([^/]+)/([^/\.]+)\.html', video_url)
            if not match:
                return {'success': False, 'message': 'URL格式错误，无法解析cid', 'data': None}

            cid = match.group(1)
            current_vid = match.group(2)

            with sync_playwright() as p:
                # 尝试使用系统浏览器，提高兼容性
                browser = None
                for channel in ['chrome', 'msedge', None]:
                    try:
                        if channel:
                            browser = p.chromium.launch(headless=True, channel=channel)
                        else:
                            browser = p.chromium.launch(headless=True)
                        break
                    except Exception:
                        continue

                if not browser:
                    return {'success': False, 'message': '无法启动浏览器', 'data': None}

                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )

                try:
                    page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    pass

                page.wait_for_timeout(5000)

                episodes_dict = {}

                def extract_episodes():
                    items = page.evaluate("""
                        () => {
                            const result = [];
                            const listContainer = document.querySelector('.episode-list-container, #mvp_pc_web_episode_list, .episode-list');
                            if (!listContainer) {
                                return result;
                            }
                            const items = listContainer.querySelectorAll('.episode-item, [data-video-idx]');
                            items.forEach(item => {
                                const dtParams = item.getAttribute('dt-params');
                                const videoIdx = item.getAttribute('data-video-idx');
                                if (dtParams) {
                                    const match = dtParams.match(/[?&]vid=([^&]+)/);
                                    if (match && match[1]) {
                                        let idx = -1;
                                        if (videoIdx) {
                                            idx = parseInt(videoIdx);
                                        }
                                        result.push({vid: match[1], idx: idx});
                                    }
                                }
                            });
                            return result;
                        }
                    """)
                    for ep in items:
                        vid = ep.get('vid')
                        idx = ep.get('idx', -1)
                        if vid and vid not in episodes_dict:
                            episodes_dict[vid] = idx

                # 第一页
                extract_episodes()

                # 检查并切换分页
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

                for tab_text in tabs:
                    if tab_text and not tab_text.startswith('1-'):
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
                        extract_episodes()

                browser.close()

            if not episodes_dict:
                return {'success': False, 'message': '未能从页面提取到任何vid', 'data': None}

            # 按索引排序，没有索引的放后面
            sorted_vids = sorted(
                episodes_dict.keys(),
                key=lambda v: (episodes_dict[v] if episodes_dict[v] >= 0 else 9999)
            )

            episodes = []
            for i, vid in enumerate(sorted_vids):
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
            return {'success': False, 'message': f'获取剧集列表失败: {str(e)}', 'data': None}

    def _get_iqiyi_episode_list(self, video_url):
        """获取爱奇艺完整剧集列表"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(video_url, headers=headers, timeout=15)
            html = response.text

            album_id_match = re.search(r'albumId["\']?\s*[:=]\s*["\']?(\d+)["\']?', html)
            album_id = album_id_match.group(1) if album_id_match else None

            episodes = []

            if album_id and album_id.isdigit():
                try:
                    api_url = f'https://pcw-api.iqiyi.com/albums/album/avlistinfo?aid={album_id}&page=1&size=50'
                    api_response = requests.get(api_url, headers=headers, timeout=10)
                    api_data = api_response.json()

                    if api_data.get('data') and api_data['data'].get('epsodelist'):
                        for ep in api_data['data']['epsodelist']:
                            episodes.append({
                                'episode_num': ep.get('order', 0),
                                'title': ep.get('name', ''),
                                'url': ep.get('playUrl', ''),
                                'tv_id': str(ep.get('tvId', ''))
                            })
                except:
                    pass

            return {
                'success': True,
                'message': f'共找到 {len(episodes)} 集',
                'data': {
                    'episodes': episodes,
                    'album_id': album_id,
                    'platform': '爱奇艺'
                }
            }

        except Exception as e:
            return {'success': False, 'message': str(e), 'data': None}
    '''

    def check_api_status(self, api_key):
        """检查解析接口状态"""
        if api_key not in self.parse_apis:
            return False
        return self.parse_apis[api_key]['status'] == 'active'

    def extract_video_info(self, url):
        """尝试从视频页面提取基本信息"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            title = soup.title.string if soup.title else '未知标题'
            title = title.strip()

            return {
                'success': True,
                'message': '提取成功',
                'data': {
                    'title': title,
                    'url': url,
                    'platform': self.detect_platform(url)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'提取信息失败: {str(e)}',
                'data': None
            }
