# VIP 视频解析工具 - 部署与构建指南

## 目录

1. [项目概述](#项目概述)
2. [环境要求](#环境要求)
3. [本地开发](#本地开发)
4. [桌面端构建](#桌面端构建)
5. [Web 端部署](#web-端部署)
6. [GitHub Actions 自动构建](#github-actions-自动构建)
7. [Docker 部署](#docker-部署)
8. [常见问题](#常见问题)

---

## 项目概述

本项目是一款支持多平台 VIP 视频解析的工具，提供以下使用方式：

- **桌面端**：Windows / Linux / macOS（Intel + Apple Silicon）
- **Web 端**：浏览器在线访问
- **命令行**：脚本化和批量操作

**技术栈：**

- Python 3.11
- PyQt5（桌面 GUI）
- Flask（Web 服务端）
- PyInstaller（桌面端打包）
- Docker（Web 端容器化）
- GitHub Actions（CI/CD 自动构建）

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.11+ |
| 操作系统 | Windows / macOS / Linux |
| 网络 | 需要联网解析视频 |
| 可选 | ffmpeg（用于视频合并） |

---

## 本地开发

### 1. 克隆仓库

```bash
git clone https://github.com/hello-github-ui/video-vip-download.git
cd video-vip-download
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt

# Web 端额外依赖
pip install flask flask-cors gunicorn
```

### 4. 运行

```bash
# 图形界面
python main.py

# 命令行
python main.py -c --help

# Web 服务
python web_server.py
```

---

## 桌面端构建

### 手动构建（本地）

#### Windows

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm --onefile --windowed \
  --name "VIP-Video-Parser-Windows" \
  --icon=icon.ico \
  --add-data "icon.ico;." \
  main.py
```

#### Linux

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm --onefile --windowed \
  --name "VIP-Video-Parser-Linux" \
  --icon=icon.ico \
  --add-data "icon.ico:." \
  main.py
```

#### macOS Intel

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm --windowed \
  --name "VIP-Video-Parser-macOS-Intel" \
  --icon=icon.ico \
  --add-data "icon.ico:." \
  main.py
cd dist
zip -r "VIP-Video-Parser-macOS-Intel.zip" "VIP-Video-Parser-macOS-Intel.app"
```

#### macOS Apple Silicon

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm --windowed \
  --name "VIP-Video-Parser-macOS-AppleSilicon" \
  --icon=icon.ico \
  --add-data "icon.ico:." \
  main.py
cd dist
zip -r "VIP-Video-Parser-macOS-AppleSilicon.zip" "VIP-Video-Parser-macOS-AppleSilicon.app"
```

---

## Web 端部署

### 方式一：直接运行

```bash
pip install flask flask-cors gunicorn
python web_server.py
```

访问 http://localhost:5000

### 方式二：Gunicorn 生产部署

```bash
gunicorn -w 4 -b 0.0.0.0:5000 web_server:create_app()
```

### 方式三：Docker 部署

```bash
# 构建镜像
docker build -t vip-video-parser .

# 运行容器
docker run -d -p 5000:5000 --name vip-parser vip-video-parser

# 查看日志
docker logs -f vip-parser
```

---

## GitHub Actions 自动构建

### 触发方式

1. **自动触发**：推送 `v*` 标签（如 `git tag v1.0.0 && git push origin v1.0.0`）
2. **手动触发**：在 Actions 页面点击 "Run workflow" 并输入版本号

### 构建产物

| 产物 | 说明 |
|------|------|
| Windows EXE | `VIP-Video-Parser-Windows.exe` |
| Linux 可执行文件 | `VIP-Video-Parser-Linux` |
| macOS Intel App | `VIP-Video-Parser-macOS-Intel.zip` |
| macOS Apple Silicon App | `VIP-Video-Parser-macOS-AppleSilicon.zip` |
| Docker 镜像 | `docker.io/<your-dockerhub-username>/vip-video-parser:<version>` |

### 配置 Docker Hub 推送

在 GitHub 仓库 Settings > Secrets and variables > Actions 中添加：

| Secret | 说明 |
|--------|------|
| `DOCKER_USERNAME` | 你的 Docker Hub 用户名 |
| `DOCKER_PASSWORD` | 你的 Docker Hub 密码或 Access Token |

### 工作流文件

详见 `.github/workflows/build.yml`

---

## Docker 部署

### 拉取镜像

```bash
# 替换为你的 Docker Hub 用户名
docker pull <your-dockerhub-username>/vip-video-parser:latest
```

### 运行容器

```bash
# 基本运行
docker run -d -p 5000:5000 --name vip-parser <your-dockerhub-username>/vip-video-parser:latest

# 指定端口
docker run -d -p 8080:5000 --name vip-parser <your-dockerhub-username>/vip-video-parser:latest

# 持久化下载目录
docker run -d -p 5000:5000 -v ~/Downloads:/app/downloads --name vip-parser <your-dockerhub-username>/vip-video-parser:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  vip-parser:
    image: <your-dockerhub-username>/vip-video-parser:latest
    container_name: vip-parser
    ports:
      - "5000:5000"
    volumes:
      - ./downloads:/app/downloads
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
docker-compose up -d
```

---

## 常见问题

### Q1: GitHub Actions 构建失败

**检查清单：**

- [ ] `requirements.txt` 包含所有依赖
- [ ] `icon.ico` 存在于仓库根目录
- [ ] Docker Hub 凭据已配置
- [ ] 标签格式正确（`v1.0.0`）

### Q2: PyInstaller 打包后无法运行

**解决方案：**

```bash
# 检查依赖是否完整
pip install --upgrade pyinstaller

# 重新打包时添加 --clean
pyinstaller --clean --noconfirm ...

# 查看打包日志
pyinstaller --log-level DEBUG ...
```

### Q3: Web 端无法访问

**检查：**

```bash
# 检查服务是否运行
curl http://localhost:5000/health

# 检查端口占用
lsof -i :5000

# 查看日志
python web_server.py
```

### Q4: Docker 镜像构建失败

**解决方案：**

```bash
# 清理缓存
docker build --no-cache -t vip-video-parser .

# 检查 Dockerfile
# 确保 requirements.txt 包含 flask flask-cors gunicorn
```

### Q5: macOS 打开应用提示「无法验证开发者」

**解决方案：**

```bash
# 右键点击应用 -> 打开
# 或执行
xattr -cr "VIP-Video-Parser-macOS-Intel.app"
```

---

## 许可证

GNU General Public License v3.0
