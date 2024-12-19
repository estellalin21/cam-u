import os
import subprocess
import qrcode
from pathlib import Path
import shutil
import sys
from datetime import datetime

class GitLFSVideoShare:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.videos_dir = self.repo_path / 'videos'
        self.pages_dir = self.repo_path / 'pages'
        self.github_pages_url = None
        self.setup_repository()

    def setup_repository(self):
        """初始化或检查仓库设置"""
        try:
            # 创建必要的目录
            self.videos_dir.mkdir(exist_ok=True)
            self.pages_dir.mkdir(exist_ok=True)

            # 切换到仓库目录
            os.chdir(self.repo_path)

            # 检查是否已初始化git
            if not (self.repo_path / '.git').exists():
                print("初始化Git仓库...")
                self._run_command(['git', 'init'])
                
                # 创建.gitattributes文件
                with open('.gitattributes', 'w') as f:
                    f.write('*.mp4 filter=lfs diff=lfs merge=lfs -text\n')
                    f.write('*.mkv filter=lfs diff=lfs merge=lfs -text\n')
                    f.write('*.mov filter=lfs diff=lfs merge=lfs -text\n')

                # 初始化Git LFS
                self._run_command(['git', 'lfs', 'install'])

            # 获取GitHub Pages URL
            self.github_pages_url = self._get_github_url()

        except Exception as e:
            print(f"仓库设置失败: {str(e)}")
            sys.exit(1)

    def _get_github_url(self):
        """获取GitHub仓库URL"""
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # 转换为GitHub Pages URL
                if url.endswith('.git'):
                    url = url[:-4]
                if url.startswith('git@github.com:'):
                    url = 'https://' + url[15:]
                return url.replace('github.com', 'github.io')
        except:
            pass
        
        # 如果获取失败，要求手动输入
        return input("请输入GitHub Pages URL (格式: https://username.github.io/repo): ").strip()

    def create_player_page(self, video_path, title):
        """创建视频播放页面"""
        video_relative_path = os.path.relpath(video_path, self.repo_path)
        html_content = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #000;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: #fff;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        .video-container {{
            width: 100%;
            max-width: 1920px;
            margin: 20px auto;
            padding: 0 20px;
            box-sizing: border-box;
        }}
        video {{
            width: 100%;
            max-height: 85vh;
            background: #000;
        }}
        h1 {{
            margin: 20px;
            font-size: 24px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="video-container">
        <video controls preload="metadata">
            <source src="/{video_relative_path}" type="video/mp4">
            您的浏览器不支持视频播放。
        </video>
    </div>
</body>
</html>
'''
        # 生成唯一的页面文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        page_name = f'{timestamp}_{Path(title).stem}.html'
        page_path = self.pages_dir / page_name
        
        # 保存HTML文件
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return page_path

    def _run_command(self, command):
        """运行Git命令"""
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"命令失败: {result.stderr}")
        return result.stdout.strip()

    def share_video(self, video_path):
        """处理视频分享"""
        try:
            # 复制视频到videos目录
            video_name = Path(video_path).name
            target_path = self.videos_dir / video_name
            shutil.copy2(video_path, target_path)

            # 创建播放页面
            page_path = self.create_player_page(target_path, video_name)

            # 生成访问URL
            page_relative_path = page_path.relative_to(self.repo_path)
            page_url = f"{self.github_pages_url}/{page_relative_path}"

            # 生成二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(page_url)
            qr.make(fit=True)
            
            # 保存二维码
            qr_path = self.repo_path / 'qrcodes' / f'{Path(video_name).stem}_qr.png'
            qr_path.parent.mkdir(exist_ok=True)
            qr_image = qr.make_image(fill_color="black", back_color="white")
            qr_image.save(qr_path)

            # Git操作
            self._run_command(['git', 'add', '.'])
            self._run_command(['git', 'commit', '-m', f'Add video: {video_name}'])

            return {
                'video_path': str(target_path),
                'page_path': str(page_path),
                'page_url': page_url,
                'qr_path': str(qr_path)
            }

        except Exception as e:
            raise Exception(f"分享失败: {str(e)}")

def main():
    print("=== GitHub LFS 视频分享工具 ===\n")
    
    # 获取仓库路径
    repo_path = input("请输入GitHub仓库本地路径: ").strip()
    
    try:
        # 创建分享器
        sharer = GitLFSVideoShare(repo_path)
        
        # 获取视频文件路径
        video_path = input("\n请输入视频文件路径（直接拖入文件即可）: ").strip().strip('"')
        if not os.path.exists(video_path):
            print("错误：文件不存在！")
            return
        
        # 分享视频
        print("\n处理中...")
        info = sharer.share_video(video_path)
        
        print("\n=== 分享成功！===")
        print(f"视频路径: {info['video_path']}")
        print(f"播放页面: {info['page_path']}")
        print(f"访问地址: {info['page_url']}")
        print(f"二维码位置: {info['qr_path']}")
        print("\n注意：需要手动push到GitHub并启用GitHub Pages才能访问")
        print("1. git push origin main")
        print("2. 在GitHub仓库设置中启用GitHub Pages")
        
    except Exception as e:
        print(f"\n错误：{str(e)}")

if __name__ == "__main__":
    main()
