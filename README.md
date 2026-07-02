# 🎥VIP 视频解析工具

一款支持多平台 VIP 视频解析的桌面端和 Web 端工具，支持腾讯视频、优酷、哔哩哔哩、爱奇艺等主流视频网站。

## 功能特性

-   **多平台支持**：腾讯视频、优酷、哔哩哔哩、爱奇艺、芒果 TV、搜狐视频等
-   **多种解析线路**：9 条解析线路可选，自动检测可用性
-   **图形界面**：PyQt5 跨平台桌面应用
-   **命令行工具**：支持脚本化和批量操作
-   **批量下载**：自动下载电视剧全部剧集
-   **自动获取下一集**：支持腾讯和爱奇艺的剧集自动翻页
-   **Web 在线访问**：通过浏览器即可使用
-   **下载速度优化**：并发片段下载、缓冲区优化

## 快速开始

### 桌面端下载

| 平台      | 架构          | 下载                                                         |
| --------- | ------------- | ------------------------------------------------------------ |
| Windows   | x64           | [VIP-Video-Parser-Windows.exe](https://github.com/hello-github-ui/video-vip-download/releases/latest) |
| Linux     | x64           | [VIP-Video-Parser-Linux](https://github.com/hello-github-ui/video-vip-download/releases/latest) |
| ~~macOS~~ | ~~Intel~~     | ~~[VIP-Video-Parser-macOS-Intel.zip](https://github.com/hello-github-ui/video-vip-download/releases/latest)~~ |
| macOS     | Apple Silicon | [VIP-Video-Parser-macOS-AppleSilicon.zip](https://github.com/hello-github-ui/video-vip-download/releases/latest) |

### Web 端部署

````bash
docker pull <your-dockerhub-username>/vip-video-parser:latest
docker run -p 8080:8080 <your-dockerhub-username>/vip-video-parser:latest

访问 http://localhost:8080 即可使用。

### 源码运行

​```bash
# 克隆仓库
git clone https://github.com/hello-github-ui/video-vip-download.git
cd video-vip-download

# 安装依赖
pip install -r requirements.txt

# 启动图形界面
python main.py

# 或启动命令行
python main.py -c --help

# 或启动 Web 服务
python web_server.py
````

## 使用说明

### 图形界面

1. 输入视频链接
2. 选择解析线路
3. 点击「开始解析」
4. 解析成功后可在浏览器打开或下载

### 命令行

```bash
# 解析视频
python main.py -c -a https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html

# 下载视频
python main.py -c -D https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html -q 720p -o ~/Downloads

# 批量下载电视剧
python main.py -c -B https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html -o ~/Downloads -m 10

# 获取下一集
python main.py -c -N https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html

# 获取剧集列表
python main.py -c -E https://v.qq.com/x/cover/wu1e7mrffzvibjy/t00306i1e62.html
```

### Web API

| 接口                  | 方法 | 说明         |
| --------------------- | ---- | ------------ |
| `/api/parse`          | POST | 解析视频链接 |
| `/api/next-episode`   | POST | 获取下一集   |
| `/api/episodes`       | POST | 获取剧集列表 |
| `/api/download`       | POST | 下载视频     |
| `/api/batch-download` | POST | 批量下载     |
| `/health`             | GET  | 健康检查     |

## 项目结构

```
video-vip-download/
├── .github/workflows/     # GitHub Actions 自动构建
│   └── build.yml
├── templates/             # Web 前端模板
│   └── index.html
├── main.py               # 主入口
├── gui.py                # 图形界面
├── cli.py                # 命令行工具
├── web_server.py         # Web 服务端
├── video_parser.py       # 核心解析模块
├── requirements.txt      # Python 依赖
├── Dockerfile            # Docker 镜像构建
├── README.md             # 项目说明
├── DEPLOYMENT.md         # 部署指南
└── icon.ico              # 应用图标
```

## 自动构建

本项目使用 GitHub Actions 自动构建多平台产物：

-   **触发方式**：推送 `v*` 标签或手动触发
-   **构建产物**：
    -   Windows EXE
    -   Linux 可执行文件
    -   macOS Intel / Apple Silicon App
    -   Docker 镜像（多架构）
-   **发布**：自动创建 GitHub Release 并上传产物

### 配置 Docker Hub 推送

在仓库 Settings > Secrets and variables > Actions 中添加：

-   `DOCKER_USERNAME`：你的 Docker Hub 用户名
-   `DOCKER_PASSWORD`：你的 Docker Hub 密码或 Token

### 本地打包

#### 前置准备

```bash
# 克隆仓库
git clone https://github.com/hello-github-ui/video-vip-download.git
cd video-vip-download

# 安装依赖
pip install -r requirements.txt
pip install pyinstaller pillow
```

#### Windows

```bash
pyinstaller --clean --noconfirm --onefile --windowed ^
  --name "VIP-Video-Parser-Windows" ^
  --icon=icon.ico ^
  --add-data "icon.ico;." ^
  main.py
```

| 参数                      | 说明                                         |
| :------------------------ | :------------------------------------------- |
| `--clean`                 | 打包前清理临时文件                           |
| `--noconfirm`             | 不确认，直接覆盖旧文件                       |
| `--onefile`               | 打包成单个 exe 文件                          |
| `--windowed`              | 启动时不显示命令行黑框（GUI 程序用）         |
| `--name "xxx"`            | 生成的 exe 文件名                            |
| `--icon=icon.ico`         | exe 文件的图标                               |
| `--add-data "icon.ico;."` | 把 icon.ico 打包进程序（Windows 用分号分隔） |
| `main.py`                 | 入口脚本                                     |

#### macOS

Apple Silicon (M1/M2/M3)：

```bash
# 先生成 icns 图标
python -c "
from PIL import Image
img = Image.open('icon.ico')
img.save('icon.icns', format='ICNS')
print('Icon converted to icns format')
"

# 打包
pyinstaller --clean --noconfirm --windowed \
  --name "VIP-Video-Parser-macOS-AppleSilicon" \
  --icon=icon.icns \
  --add-data "icon.icns:." \
  main.py

# 打包成 zip（方便分发）
cd dist
zip -r "VIP-Video-Parser-macOS-AppleSilicon.zip" "VIP-Video-Parser-macOS-AppleSilicon.app"
```

~~Intel：~~

```bash
# 先生成 icns 图标
python -c "
from PIL import Image
img = Image.open('icon.ico')
img.save('icon.icns', format='ICNS')
print('Icon converted to icns format')
"

# 打包
pyinstaller --clean --noconfirm --windowed \
  --name "VIP-Video-Parser-macOS-Intel" \
  --icon=icon.icns \
  --add-data "icon.icns:." \
  main.py

# 打包成 zip（方便分发）
cd dist
zip -r "VIP-Video-Parser-macOS-Intel.zip" "VIP-Video-Parser-macOS-Intel.app"
```

#### Linux

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y libgl1 libglx-mesa0 libxkbcommon-x11-0 \
  libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
  libxcb-render-util0 libxcb-xinerama0 libxcb-xfixes0 libegl1 libopengl0

# 打包
pyinstaller --clean --noconfirm --onefile --windowed \
  --name "VIP-Video-Parser-Linux" \
  --icon=icon.ico \
  --add-data "icon.ico:." \
  main.py
```

#### 产物位置

打包完成后，产物位于 `dist/` 目录下：

| 平台    | 产物路径                                    |
| ------- | ------------------------------------------- |
| Windows | `dist/VIP-Video-Parser-Windows.exe`         |
| macOS   | `dist/VIP-Video-Parser-macOS-xxx.app/`      |
| Linux   | `dist/VIP-Video-Parser-Linux`               |

## 演示

![image-20260702144244921](assets/image-20260702144244921.png)

![image-20260702144343349](assets/image-20260702144343349.png)

![image-20260702165702791](assets/image-20260702165702791.png)

## 许可证

GNU General Public License v3.0
