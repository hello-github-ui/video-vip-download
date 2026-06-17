import re
import requests
import webbrowser
import subprocess
import os
from urllib.parse import quote, urlparse
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
        验证URL是否有效
        
        Args:
            url (str): 待验证的URL
            
        Returns:
            bool: URL是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def detect_platform(self, url):
        """
        检测视频URL所属平台
        
        Args:
            url (str): 视频链接
            
        Returns:
            str: 平台名称，未知平台返回'其他'
        """
        for platform, domains in self.supported_platforms.items():
            for domain in domains:
                if domain in url:
                    return platform
        return '其他'

    def parse_url(self, video_url, api_key='b'):
        """
        根据选择的解析线路生成解析链接
        
        Args:
            video_url (str): 原始视频链接
            api_key (str): 解析线路标识，默认为夜幕解析(b)
            
        Returns:
            dict: 解析结果，包含状态和解析后的链接
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
        
        Args:
            url (str): 要打开的URL
            
        Returns:
            bool: 是否成功打开
        """
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"打开浏览器失败: {str(e)}")
            return False

    def download_video(self, video_url, output_path=None, quality='best'):
        """
        使用yt-dlp下载视频
        
        Args:
            video_url (str): 视频链接
            output_path (str): 输出目录，默认为当前目录
            quality (str): 视频质量，可选值: best, worst, 1080p, 720p等
            
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
        
        quality_map = {
            'best': 'bestvideo+bestaudio/best',
            'worst': 'worstvideo+worstaudio/worst',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]'
        }
        
        format_spec = quality_map.get(quality, quality_map['best'])
        
        cmd = [
            'yt-dlp',
            '-f', format_spec,
            '-o', os.path.join(output_path, '%(title)s.%(ext)s'),
            '--merge-output-format', 'mp4',
            video_url
        ]
        
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

    def check_api_status(self, api_key):
        """
        检查解析接口状态
        
        Args:
            api_key (str): 解析接口标识
            
        Returns:
            bool: 接口是否可用
        """
        if api_key not in self.parse_apis:
            return False
        return self.parse_apis[api_key]['status'] == 'active'

    def extract_video_info(self, url):
        """
        尝试从视频页面提取基本信息
        
        Args:
            url (str): 视频页面URL
            
        Returns:
            dict: 视频信息
        """
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
