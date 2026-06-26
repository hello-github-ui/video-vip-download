import json
import os
import re
import subprocess
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urlparse, unquote

import requests
from bs4 import BeautifulSoup


class VideoParser:
    """
    视频解析核心类
    支持多种解析线路，提供视频解析和下载功能
    """

    def __init__(self):
        """初始化解析器，定义支持的解析线路"""
        self.parse_apis = {
            'a': {
                'name': '万能稳定解析',
                'url': 'https://jx.m3u8.tv/jiexi/?url=',
                'status': 'active',
                'note': '推荐使用'
            },
            'b': {
                'name': '夜幕解析',
                'url': 'https://www.yemu.xyz/?url=',
                'status': 'deprecated',
                'note': '实测已不可用'
            },
            'c': {
                'name': '虾米解析',
                'url': 'https://jx.xmflv.com/?url=',
                'status': 'active',
                'note': ''
            },
            'd': {
                'name': '冰豆解析',
                'url': 'https://bd.jx.cn/?url=',
                'status': 'active',
                'note': ''
            },
            'e': {
                'name': 'JSON解析',
                'url': 'https://jx.jsonplayer.com/player/?url=',
                'status': 'active',
                'note': ''
            },
            'f': {
                'name': 'm3u8解析',
                'url': 'https://jx.m3u8.tv/jiexi/?url=',
                'status': 'deprecated',
                'note': '实测已不可用'
            },
            'g': {
                'name': '阳途解析',
                'url': 'https://jx.yangtu.top/?url=',
                'status': 'active',
                'note': ''
            },
            'h': {
                'name': '千奇解析',
                'url': 'https://api.qianqi.net/vip/?url=',
                'status': 'active',
                'note': ''
            },
            'i': {
                'name': 'CK解析',
                'url': 'https://www.ckplayer.vip/jiexi/?url=',
                'status': 'active',
                'note': ''
            }
        }

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

    def get_all_apis(self):
        """获取所有解析接口信息"""
        return self.parse_apis

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

    def parse_url(self, video_url, api_key='a'):
        """
        根据选择的解析线路生成解析链接
        """
        if not self.is_valid_url(video_url):
            return {
                'success': False,
                'message': '无效的视频链接',
                'data': None
            }

        if api_key not in self.parse_apis:
            return {
                'success': False,
                'message': '无效的解析线路选择',
                'data': None
            }

        api_info = self.parse_apis[api_key]

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
                'api_key': api_key
            }
        }

    def open_in_browser(self, url):
        """
        在浏览器中打开解析链接
        """
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"打开浏览器失败: {str(e)}")
            return False

    def _extract_m3u8_from_api(self, parsed_url):
        """
        从解析接口返回的页面中提取真实的 m3u8 或直链地址
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': parsed_url
        }
        
        try:
            response = requests.get(parsed_url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            html = response.text
            
            # 1. 从 iframe src 中提取
            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if iframe_match:
                iframe_url = iframe_match.group(1)
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                elif iframe_url.startswith('/'):
                    parsed = urlparse(parsed_url)
                    iframe_url = f"{parsed.scheme}://{parsed.netloc}{iframe_url}"
                
                result = self._extract_m3u8_from_api(iframe_url)
                if result:
                    return result
            
            # 2. 从 script 标签中提取 m3u8 链接
            m3u8_patterns = [
                r'["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'url["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'src["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'video["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
                r'playurl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'"video"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'"src"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            ]
            
            for pattern in m3u8_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    url = match.group(1)
                    url = url.replace('\\/', '/')
                    if url.startswith('//'):
                        url = 'https:' + url
                    return url
            
            # 3. 从 JSON 数据中提取
            json_match = re.search(r'var\s+config\s*=\s*({.*?});', html, re.DOTALL)
            if json_match:
                try:
                    config = json.loads(json_match.group(1))
                    if 'url' in config:
                        return config['url']
                    if 'video' in config:
                        return config['video']
                    if 'src' in config:
                        return config['src']
                except:
                    pass
            
            # 4. 从 player 配置中提取
            player_match = re.search(r'player\s*\(\s*{(.*?)}\s*\)', html, re.DOTALL)
            if player_match:
                url_match = re.search(r'url\s*:\s*["\']([^"\']+)["\']', player_match.group(1))
                if url_match:
                    return url_match.group(1)
            
            # 5. 从 CKPlayer 配置中提取
            ck_match = re.search(r'video\s*:\s*["\']([^"\']+)["\']', html)
            if ck_match:
                return ck_match.group(1)
            
            return None
            
        except Exception as e:
            print(f"提取m3u8地址失败: {str(e)}")
            return None

    def download_video(self, video_url, output_path=None, quality='best', original_url=None):
        """
        使用yt-dlp下载视频（优化速度版本）
        
        Args:
            video_url (str): 视频链接（可以是原始视频链接或解析后的链接）
            output_path (str): 输出目录，默认为当前目录
            quality (str): 视频质量
            original_url (str): 原始视频链接
            
        Returns:
            dict: 下载结果
        """
        if not self.is_valid_url(video_url):
            return {
                'success': False,
                'message': '无效的视频链接',
                'data': None
            }

        if output_path is None:
            output_path = os.getcwd()

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # 判断是否是解析接口链接
        is_api_url = any(api['url'].split('?')[0] in video_url for api in self.parse_apis.values())
        
        actual_url = video_url
        
        # 如果是解析接口链接，尝试提取真实视频地址
        if is_api_url:
            print(f"检测到解析接口链接，正在提取真实视频地址...")
            extracted_url = self._extract_m3u8_from_api(video_url)
            if extracted_url:
                actual_url = extracted_url
                print(f"提取到真实地址: {actual_url}")
            else:
                if original_url:
                    actual_url = original_url
                else:
                    return {
                        'success': False,
                        'message': '无法从解析接口提取真实视频地址，请尝试直接复制解析链接到浏览器播放',
                        'data': None
                    }

        quality_map = {
            'best': 'bestvideo+bestaudio/best',
            'worst': 'worstvideo+worstaudio/worst',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]'
        }

        format_spec = quality_map.get(quality, quality_map['best'])

        # 构建优化的 yt-dlp 命令（提升下载速度）
        cmd = [
            'yt-dlp',
            '-f', format_spec,
            '-o', os.path.join(output_path, '%(title)s.%(ext)s'),
            '--merge-output-format', 'mp4',
            '--no-warnings',
            # 速度优化参数
            '--concurrent-fragments', '5',      # 并发下载5个片段
            '--buffer-size', '16K',             # 增大缓冲区
            '--http-chunk-size', '10M',         # HTTP分块大小
            '--retries', '10',                  # 重试次数
            '--fragment-retries', '10',         # 片段重试次数
            '--no-check-certificate',           # 跳过证书验证
            '--prefer-free-formats',            # 优先免费格式
            '--no-playlist',                    # 不下载播放列表
        ]

        # 如果是 m3u8 链接，添加相关参数
        if '.m3u8' in actual_url.lower():
            cmd.extend([
                '--downloader', 'ffmpeg',
                '--hls-prefer-native',
                '--hls-use-mpegts',
            ])

        cmd.append(actual_url)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=output_path
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'message': '视频下载成功',
                    'data': {
                        'output_path': output_path,
                        'stdout': result.stdout
                    }
                }
            else:
                # 如果 yt-dlp 失败，尝试用 ffmpeg 直接下载 m3u8
                if '.m3u8' in actual_url.lower():
                    return self._download_with_ffmpeg(actual_url, output_path)
                return {
                    'success': False,
                    'message': f'下载失败: {result.stderr}',
                    'data': None
                }
        except FileNotFoundError:
            return {
                'success': False,
                'message': '未找到yt-dlp，请确保已安装',
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'下载过程发生错误: {str(e)}',
                'data': None
            }

    def _download_with_ffmpeg(self, m3u8_url, output_path):
        """
        使用 ffmpeg 下载 m3u8 视频
        """
        try:
            output_file = os.path.join(output_path, 'video_download.mp4')
            
            cmd = [
                'ffmpeg',
                '-i', m3u8_url,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-y',
                output_file
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=output_path
            )
            
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
                return {
                    'success': False,
                    'message': f'ffmpeg下载失败: {result.stderr}',
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
                ep_links = re.findall(r'href=["\'](https?://www\.iqiyi\.com/v_\w+\.html)["\'][^>]*>\s*(?:<[^>]+>)*\s*(\d+)\s*(?:<[^>]+>)*\s*</a>', html)
                for url, num in ep_links:
                    episodes.append({
                        'url': url,
                        'episode_num': int(num),
                        'tv_id': ''
                    })
                
                if not episodes:
                    ep_data = re.findall(r'data-episode=["\'](\d+)["\'][^>]*href=["\'](https?://www\.iqiyi\.com/v_\w+\.html)["\']', html)
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
