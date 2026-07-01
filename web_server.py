#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VIP 视频解析工具 - Web 服务端
提供 REST API 和网页界面，支持在线解析和下载
"""

import os
import tempfile
import uuid

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

from video_parser import VideoParser

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 存储下载任务的临时目录
TEMP_DIR = tempfile.gettempdir()

# 初始化解析器
parser = VideoParser()


@app.route('/')
def index():
    """首页 - 渲染网页界面"""
    return render_template('index.html')


@app.route('/download')
def download_page():
    """下载页面 - 集成视频播放和下载功能"""
    video_url = request.args.get('url', '')
    original_url = request.args.get('original', '')
    return render_template('download.html', video_url=video_url, original_url=original_url)


@app.route('/api/parse', methods=['POST'])
def api_parse():
    """
    解析视频链接 API
    
    请求体:
    {
        "url": "https://v.qq.com/x/cover/...",
        "api_key": "a"  // 可选，默认 "a"
    }
    
    响应:
    {
        "success": true,
        "message": "...",
        "data": {
            "original_url": "...",
            "parsed_url": "...",
            "api_name": "...",
            "platform": "..."
        }
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求体不能为空'}), 400

    video_url = data.get('url', '').strip()
    api_key = data.get('api_key', 'a')

    if not video_url:
        return jsonify({'success': False, 'message': '视频链接不能为空'}), 400

    result = parser.parse_url(video_url, api_key)

    if result['success']:
        platform = parser.detect_platform(video_url)
        result['data']['platform'] = platform

    return jsonify(result)


@app.route('/api/platforms', methods=['GET'])
def api_platforms():
    """获取支持的平台列表"""
    return jsonify({
        'success': True,
        'data': list(parser.supported_platforms.keys())
    })


@app.route('/api/apis', methods=['GET'])
def api_apis():
    """获取所有解析线路"""
    apis = parser.get_all_apis()
    return jsonify({
        'success': True,
        'data': apis
    })


@app.route('/api/next-episode', methods=['POST'])
def api_next_episode():
    """
    获取下一集 API
    
    请求体:
    {
        "url": "当前视频链接"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求体不能为空'}), 400

    current_url = data.get('url', '').strip()
    if not current_url:
        return jsonify({'success': False, 'message': '视频链接不能为空'}), 400

    result = parser.get_next_episode(current_url)
    return jsonify(result)


@app.route('/api/episodes', methods=['POST'])
def api_episodes():
    """
    获取剧集列表 API
    
    请求体:
    {
        "url": "视频链接"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求体不能为空'}), 400

    video_url = data.get('url', '').strip()
    if not video_url:
        return jsonify({'success': False, 'message': '视频链接不能为空'}), 400

    result = parser.get_episode_list(video_url)
    return jsonify(result)


@app.route('/api/download', methods=['POST'])
def api_download():
    """
    下载视频 API
    
    请求体:
    {
        "url": "解析后的链接或原始链接",
        "quality": "best",  // 可选
        "original_url": "原始链接"  // 可选
    }
    
    响应: 视频文件流
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求体不能为空'}), 400

    video_url = data.get('url', '').strip()
    quality = data.get('quality', 'best')
    original_url = data.get('original_url')

    if not video_url:
        return jsonify({'success': False, 'message': '视频链接不能为空'}), 400

    # 创建临时输出目录
    output_dir = os.path.join(TEMP_DIR, f'vip_download_{uuid.uuid4().hex[:8]}')
    os.makedirs(output_dir, exist_ok=True)

    result = parser.download_video(video_url, output_dir, quality, original_url)

    if result['success']:
        # 查找下载的文件
        files = os.listdir(output_dir)
        if files:
            file_path = os.path.join(output_dir, files[0])
            return send_file(
                file_path,
                as_attachment=True,
                download_name=files[0]
            )
        else:
            return jsonify({'success': False, 'message': '下载成功但找不到文件'}), 500
    else:
        return jsonify(result), 400


@app.route('/api/batch-download', methods=['POST'])
def api_batch_download():
    """
    批量下载 API
    
    请求体:
    {
        "url": "起始视频链接",
        "quality": "best",  // 可选
        "api_key": "a",  // 可选
        "max_episodes": 5  // 可选，默认全部
    }
    
    响应: 返回下载结果信息（不直接返回文件，因为批量下载文件较大）
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求体不能为空'}), 400

    start_url = data.get('url', '').strip()
    quality = data.get('quality', 'best')
    api_key = data.get('api_key', 'a')
    max_episodes = data.get('max_episodes')

    if not start_url:
        return jsonify({'success': False, 'message': '视频链接不能为空'}), 400

    # 创建临时输出目录
    output_dir = os.path.join(TEMP_DIR, f'vip_batch_{uuid.uuid4().hex[:8]}')
    os.makedirs(output_dir, exist_ok=True)

    def progress_callback(episode_num, total, status, message):
        # Web 端批量下载不实时推送进度，只记录日志
        app.logger.info(f"[Batch] Ep{episode_num}/{total} [{status}]: {message}")

    result = parser.batch_download(
        start_url,
        output_dir,
        quality,
        api_key,
        max_episodes,
        progress_callback
    )

    return jsonify(result)


@app.route('/api/extract-m3u8', methods=['POST'])
def api_extract_m3u8():
    """
    从解析接口提取真实 m3u8 地址 API
    
    请求体:
    {
        "parsed_url": "解析接口返回的链接"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求体不能为空'}), 400

    parsed_url = data.get('parsed_url', '').strip()
    if not parsed_url:
        return jsonify({'success': False, 'message': '解析链接不能为空'}), 400

    m3u8_url = parser._extract_m3u8_from_api(parsed_url)

    if m3u8_url:
        return jsonify({
            'success': True,
            'message': '提取成功',
            'data': {'m3u8_url': m3u8_url}
        })
    else:
        return jsonify({
            'success': False,
            'message': '无法提取真实视频地址'
        })


@app.route('/health', methods=['GET'])
def health():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'service': 'vip-video-parser',
        'version': '1.0.0'
    })


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


def create_app():
    """创建应用实例（用于 Gunicorn/uWSGI）"""
    return app


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"\n\tVIP 视频解析工具 Web 服务端")
    print(f"\t访问地址: http://localhost:{port}")
    print(f"\t视频地址示例: https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html")
    print(f"\t按 Ctrl+C 停止服务\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
