#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VIP 视频解析工具 - Web 界面
基于 Flask 提供简洁的 Web 操作界面
"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory

from video_parser import VideoParser


class WebApp:
    """
    Web 应用类
    提供视频解析和下载的 Web 界面
    """

    def __init__(self):
        """初始化 Web 应用"""
        self.app = Flask(__name__,
                        template_folder='templates',
                        static_folder='static')
        self.parser = VideoParser()
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        self.app.route('/', methods=['GET'])(self.index)
        self.app.route('/parse', methods=['POST'])(self.parse)
        self.app.route('/download', methods=['POST'])(self.download)
        self.app.route('/apis', methods=['GET'])(self.get_apis)
        self.app.route('/favicon.ico')(self.favicon)

    def index(self):
        """主页"""
        return render_template('index.html')

    def parse(self):
        """解析视频"""
        data = request.get_json()
        video_url = data.get('url')
        api_key = data.get('api', 'a')

        if not video_url:
            return jsonify({'success': False, 'message': '请输入视频链接'})

        result = self.parser.parse_url(video_url, api_key)

        if result['success']:
            parsed_data = result['data']
            return jsonify({
                'success': True,
                'message': result['message'],
                'data': {
                    'parsed_url': parsed_data['parsed_url'],
                    'original_url': parsed_data['original_url'],
                    'platform': self.parser.detect_platform(video_url),
                    'api_name': parsed_data['api_name']
                }
            })
        else:
            return jsonify({'success': False, 'message': result['message']})

    def download(self):
        """下载视频"""
        data = request.get_json()
        video_url = data.get('url')
        output_path = data.get('output', os.path.expanduser('~/Downloads'))
        quality = data.get('quality', 'best')

        if not video_url:
            return jsonify({'success': False, 'message': '请输入视频链接'})

        # 使用原始 URL 进行下载（yt-dlp 直接支持）
        result = self.parser.download_video(video_url, output_path, quality, video_url)

        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'data': result['data']
            })
        else:
            return jsonify({'success': False, 'message': result['message']})

    def get_apis(self):
        """获取解析线路列表"""
        apis = self.parser.parse_apis
        api_list = []
        for key, api in apis.items():
            api_list.append({
                'key': key,
                'name': api['name'],
                'status': api['status'],
                'note': api.get('note', '')
            })
        return jsonify({'success': True, 'data': api_list})

    def favicon(self):
        """返回 favicon"""
        favicon_path = os.path.join(self.app.static_folder, 'favicon.ico')
        if os.path.exists(favicon_path):
            return send_from_directory(self.app.static_folder, 'favicon.ico')
        return '', 404

    def run(self, host='127.0.0.1', port=5000, debug=False):
        """启动 Web 服务器"""
        print(f"\n🌐 Web 服务启动: http://{host}:{port}")
        print("💡 按 Ctrl+C 停止服务\n")
        self.app.run(host=host, port=port, debug=debug)


def create_templates():
    """
    创建 HTML 模板文件（如果不存在）
    WebApp 启动时会自动检查 templates 目录
    """
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)

    index_html = os.path.join(templates_dir, 'index.html')
    if not os.path.exists(index_html):
        with open(index_html, 'w', encoding='utf-8') as f:
            f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIP 视频解析工具</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 500px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-weight: 500;
        }
        input, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input:focus, select:focus {
            border-color: #667eea;
            outline: none;
        }
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        button {
            flex: 1;
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, background 0.3s;
        }
        button:hover { transform: translateY(-2px); }
        .btn-parse { background: #667eea; color: white; }
        .btn-download { background: #28a745; color: white; }
        .btn-open { background: #17a2b8; color: white; }
        .result {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .result.error { border-left-color: #dc3545; }
        .result.success { border-left-color: #28a745; }
        .loading {
            text-align: center;
            color: #999;
            padding: 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
    </style>
    <link rel="icon" href="/favicon.ico">
</head>
<body>
    <div class="container">
        <h1>VIP 视频解析工具</h1>
        <div class="form-group">
            <label>视频链接</label>
            <input type="text" id="url" placeholder="请输入腾讯/爱奇艺/B站等视频链接">
        </div>
        <div class="form-group">
            <label>解析线路</label>
            <select id="api"></select>
        </div>
        <div class="form-group">
            <label>画质选择（下载时生效）</label>
            <select id="quality">
                <option value="best">最佳画质</option>
                <option value="1080p">1080p</option>
                <option value="720p">720p</option>
                <option value="480p">480p</option>
                <option value="360p">360p</option>
            </select>
        </div>
        <div class="btn-group">
            <button class="btn-parse" onclick="parse()">开始解析</button>
            <button class="btn-download" onclick="download()">下载视频</button>
        </div>
        <div id="result"></div>
    </div>

    <script>
        let parsedUrl = null;
        let originalUrl = null;

        // 加载解析线路
        fetch('/apis')
            .then(r => r.json())
            .then(data => {
                const select = document.getElementById('api');
                data.data.forEach(api => {
                    const opt = document.createElement('option');
                    opt.value = api.key;
                    const status = api.status === 'active' ? '✅' : '❌';
                    opt.text = api.name + ' ' + status + (api.note ? ' (' + api.note + ')' : '');
                    if (api.status === 'active') opt.selected = true;
                    select.appendChild(opt);
                });
            });

        function showLoading() {
            document.getElementById('result').innerHTML =
                '<div class="loading"><span class="spinner"></span> 处理中...</div>';
        }

        function showResult(success, message, data) {
            const div = document.getElementById('result');
            div.className = 'result ' + (success ? 'success' : 'error');
            if (success && data) {
                parsedUrl = data.parsed_url;
                originalUrl = data.original_url;
                div.innerHTML = `
                    <strong>${message}</strong><br>
                    <br>平台: ${data.platform}<br>
                    <br>解析链接: <a href="${parsedUrl}" target="_blank">${parsedUrl}</a>
                    <button class="btn-open" style="margin-top:10px;width:100%" onclick="openBrowser()">在浏览器播放</button>
                `;
            } else {
                div.innerHTML = `<strong>${message}</strong>`;
            }
        }

        function parse() {
            const url = document.getElementById('url').value;
            const api = document.getElementById('api').value;
            if (!url) { alert('请输入视频链接'); return; }
            showLoading();
            fetch('/parse', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url, api: api})
            })
            .then(r => r.json())
            .then(data => showResult(data.success, data.message, data.data))
            .catch(e => showResult(false, '请求失败: ' + e));
        }

        function download() {
            const url = document.getElementById('url').value;
            const quality = document.getElementById('quality').value;
            if (!url) { alert('请输入视频链接'); return; }
            showLoading();
            fetch('/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url, quality: quality})
            })
            .then(r => r.json())
            .then(data => showResult(data.success, data.message, data.data))
            .catch(e => showResult(false, '请求失败: ' + e));
        }

        function openBrowser() {
            if (parsedUrl) window.open(parsedUrl, '_blank');
        }
    </script>
</body>
</html>''')


def main():
    """Web 入口函数"""
    create_templates()
    app = WebApp()
    app.run(debug=False)


if __name__ == '__main__':
    main()