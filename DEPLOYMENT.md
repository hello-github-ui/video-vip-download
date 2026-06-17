# 🎥 henVIP 视频解析工具 - 部署指南

## 目录

1. [项目概述](#项目概述)
2. [环境要求](#环境要求)
3. [依赖安装](#依赖安装)
4. [运行方式](#运行方式)
   - [图形界面版本](#图形界面版本)
   - [命令行版本](#命令行版本)
5. [功能说明](#功能说明)
6. [常见问题](#常见问题)

---

## 项目概述

henVIP 是一款支持多平台视频解析的工具，提供图形界面和命令行两种操作方式，支持腾讯视频、优酷、哔哩哔哩、爱奇艺等主流视频网站的解析和下载。

**项目结构：**

```
video-vip-download/
├── main.py              # 主入口文件
├── video_parser.py      # 视频解析核心模块
├── cli.py               # 命令行版本
├── gui.py               # 图形界面版本
├── requirements.txt     # 依赖文件
├── README.md            # 项目说明
├── DEPLOYMENT.md        # 部署指南（本文件）
└── Image/               # 演示图片目录
```

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows / macOS / Linux |
| Python 版本 | 3.6+ |
| 网络连接 | 需要联网解析视频 |

---

## 依赖安装

### 方式一：使用 pip 安装

```bash
# 进入项目目录
cd video-vip-download

# 安装依赖（推荐使用虚拟环境）
pip3 install -r requirements.txt
```

### 方式二：手动安装

```bash
# 安装 GUI 框架
pip3 install PyQt5>=5.15.9

# 安装网络请求库
pip3 install requests>=2.31.0

# 安装视频下载工具
pip3 install yt-dlp>=2024.7.16

# 安装 HTML 解析库
pip3 install beautifulsoup4>=4.12.2
```

> **注意**：如果使用 yt-dlp 下载视频，需要确保系统已安装 `ffmpeg`（用于视频合并）。

---

## 运行方式

### 图形界面版本

```bash
# 方式一：直接运行
python3 main.py

# 方式二：使用 -g 参数
python3 main.py -g
```

**界面功能：**
- 输入视频链接并选择解析线路
- 一键粘贴剪贴板内容
- 解析结果展示
- 快速访问主流视频平台
- 支持视频下载（可选画质）

### 命令行版本

```bash
# 查看帮助信息
python3 main.py -c --help

# 列出所有可用解析线路
python3 main.py -c -l

# 使用夜幕解析（推荐）
python3 main.py -c -b https://v.qq.com/x/cover/mzc00200q0y2d9q.html

# 使用虾米解析
python3 main.py -c -c https://www.bilibili.com/video/BV1xx411c7mZ

# 下载视频（最佳画质）
python3 main.py -c -D https://www.bilibili.com/video/BV1xx411c7mZ

# 指定画质下载
python3 main.py -c -D https://www.bilibili.com/video/BV1xx411c7mZ -q 720p

# 指定输出目录
python3 main.py -c -D https://www.bilibili.com/video/BV1xx411c7mZ -o ~/Downloads

# 解析后不自动打开浏览器
python3 main.py -c -b https://v.qq.com/x/cover/mzc00200q0y2d9q.html -n
```

**命令行参数说明：**

| 参数 | 说明 |
|------|------|
| `-a` / `-b` / `-c` / `-d` / `-e` / `-f` / `-g` / `-H` / `-i` | 选择不同的解析线路 |
| `-l` | 列出所有解析线路 |
| `-D <URL>` | 下载视频 |
| `-q QUALITY` | 指定画质（best/1080p/720p/480p/360p/worst） |
| `-o PATH` | 指定下载目录 |
| `-n` | 解析后不自动打开浏览器 |

---

## 功能说明

### 解析线路

| 标识 | 名称 | 状态 | 备注 |
|------|------|------|------|
| `a` | 万能稳定解析 | ❌ 不可用 | 实测已不可用 |
| `b` | 夜幕解析 | ✅ 可用 | **推荐使用** |
| `c` | 虾米解析 | ✅ 可用 | - |
| `d` | 冰豆解析 | ✅ 可用 | - |
| `e` | JSON解析 | ✅ 可用 | - |
| `f` | m3u8解析 | ❌ 不可用 | 实测已不可用 |
| `g` | 阳途解析 | ✅ 可用 | - |
| `h` | 千奇解析 | ✅ 可用 | - |
| `i` | CK解析 | ✅ 可用 | - |

### 支持平台

- 腾讯视频 (v.qq.com)
- 优酷 (youku.com)
- 哔哩哔哩 (bilibili.com)
- 爱奇艺 (iqiyi.com)
- 芒果TV (mgtv.com)
- 搜狐视频 (sohu.com)
- PP视频 (ppvideo.com)
- 乐视视频 (le.com)
- 土豆视频 (tudou.com)
- AcFun (acfun.cn)

---

## 常见问题

### Q1: 安装依赖时报错 "Permission denied"

**解决方案：** 使用 `--user` 参数安装到用户目录

```bash
pip3 install --user -r requirements.txt
```

### Q2: 图形界面无法启动

**可能原因：** PyQt5 安装不完整

**解决方案：**

```bash
pip3 uninstall PyQt5 PyQt5-Qt5 PyQt5-sip
pip3 install PyQt5>=5.15.9
```

### Q3: 下载视频时提示 "未找到yt-dlp"

**解决方案：** 确保 yt-dlp 已正确安装并添加到 PATH

```bash
# 检查安装
pip3 show yt-dlp

# 如果命令行无法找到 yt-dlp
export PATH="$HOME/Library/Python/3.11/bin:$PATH"  # macOS
```

### Q4: 解析失败

**可能原因：**
1. 视频链接无效或已过期
2. 解析接口暂时不可用
3. 网络连接问题

**解决方案：**
- 尝试更换解析线路
- 检查网络连接
- 确认视频链接有效

### Q5: 下载的视频没有声音

**解决方案：** 确保系统已安装 `ffmpeg`

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# 下载 ffmpeg 并添加到 PATH
```

---

## 许可证

本项目使用 [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.zh-cn.html) 许可证。

---

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系我们。