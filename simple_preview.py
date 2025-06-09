#!/usr/bin/env python3
"""
简单的实时预览服务器 - 无需额外依赖
支持局域网访问，方便团队协作
"""

import http.server
import socketserver
import os
import webbrowser
from datetime import datetime
import socket
import subprocess
import platform

PORT = 8080

def get_local_ip():
    """获取本机的局域网IP地址"""
    try:
        # 方法1：通过连接外部服务器获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        try:
            # 方法2：获取所有网络接口的IP地址
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except:
            return "127.0.0.1"

def get_all_ips():
    """获取所有可用的IP地址"""
    ips = []
    
    # 添加 localhost
    ips.append(("localhost", "127.0.0.1"))
    
    # 获取局域网IP
    local_ip = get_local_ip()
    if local_ip != "127.0.0.1":
        ips.append(("局域网", local_ip))
    
    # macOS 特定：尝试获取所有活动的网络接口
    if platform.system() == "Darwin":
        try:
            # 使用 ifconfig 获取所有网络接口
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            current_interface = None
            for line in lines:
                if line and not line.startswith('\t') and not line.startswith(' '):
                    current_interface = line.split(':')[0]
                elif 'inet ' in line and '127.0.0.1' not in line:
                    # 提取IP地址
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1]
                        if ip not in [ip_tuple[1] for ip_tuple in ips]:
                            interface_name = f"{current_interface}" if current_interface else "其他"
                            ips.append((interface_name, ip))
        except:
            pass
    
    return ips

class LiveReloadHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path.endswith('.html'):
            # 读取 HTML 文件
            file_path = 'index.html' if self.path == '/' else self.path[1:]
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 注入轮询刷新脚本
                reload_script = """
<script>
// 自动刷新脚本
(function() {
    let lastModified = null;
    const checkInterval = 1000; // 每秒检查一次
    
    async function checkForUpdates() {
        try {
            const response = await fetch(window.location.href, { 
                method: 'HEAD',
                cache: 'no-cache'
            });
            
            const currentModified = response.headers.get('last-modified');
            
            if (lastModified && currentModified && lastModified !== currentModified) {
                console.log('🔄 检测到页面更新，正在刷新...');
                location.reload();
            }
            
            lastModified = currentModified;
        } catch (error) {
            console.error('检查更新时出错:', error);
        }
    }
    
    // 首次加载时记录修改时间
    checkForUpdates();
    
    // 定期检查更新
    setInterval(checkForUpdates, checkInterval);
    
    console.log('✅ 自动刷新已启用 - 每秒检查文件变化');
})();
</script>
"""
                # 在 </body> 标签前插入脚本
                if '</body>' in content:
                    content = content.replace('</body>', reload_script + '\n</body>')
                else:
                    content += reload_script
                
                # 发送响应
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content.encode('utf-8')))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Last-Modified', datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                return
        
        # 对于其他文件，使用默认处理
        super().do_GET()
    
    def log_message(self, format, *args):
        # 自定义日志格式
        timestamp = datetime.now().strftime('%H:%M:%S')
        client_address = self.address_string()
        message = format % args
        
        # 根据状态码设置颜色
        if "200" in message:
            print(f"[{timestamp}] ✅ {message}")
        elif "304" in message:
            print(f"[{timestamp}] 📄 {message} (未修改)")
        elif "404" in message:
            print(f"[{timestamp}] ❌ {message}")
        else:
            print(f"[{timestamp}] 📍 {message}")

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or '.')
    
    # 获取所有可用的IP地址
    ips = get_all_ips()
    
    # 修改服务器绑定地址为 0.0.0.0，允许外部访问
    with socketserver.TCPServer(("0.0.0.0", PORT), LiveReloadHTTPHandler) as httpd:
        print("\n" + "="*60)
        print("🌟 SerialGen 实时预览服务器（支持局域网访问）")
        print("="*60)
        print(f"📁 服务目录: {os.getcwd()}")
        print(f"\n🌐 访问地址:")
        
        # 显示所有可用的访问地址
        for name, ip in ips:
            print(f"   • {name}: http://{ip}:{PORT}")
        
        print("\n💡 分享提示:")
        print("   • 将局域网地址分享给同事，即可在同一网络下访问")
        print("   • 确保防火墙允许端口", PORT, "的访问")
        
        print("\n✨ 功能特性:")
        print("   • 浏览器自动刷新（检测文件变化）")
        print("   • 支持局域网访问，方便团队协作")
        print("   • 无需安装额外依赖")
        print("   • 支持所有静态资源")
        
        print("\n🛑 按 Ctrl+C 停止服务器")
        print("="*60 + "\n")
        
        # 自动打开浏览器（使用局域网IP，方便分享）
        local_ip = get_local_ip()
        if local_ip != "127.0.0.1":
            browser_url = f'http://{local_ip}:{PORT}'
            webbrowser.open(browser_url)
            print(f"🌐 已在浏览器中打开: {browser_url}")
            print(f"📋 可直接复制上述地址分享给同事")
        else:
            webbrowser.open(f'http://localhost:{PORT}')
            print(f"🌐 已在浏览器中打开: http://localhost:{PORT}")
        
        try:
            print(f"🚀 服务器已在端口 {PORT} 启动，等待连接...\n")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 服务器已停止运行")
        except OSError as e:
            if e.errno == 48:  # Address already in use
                print(f"\n❌ 错误：端口 {PORT} 已被占用")
                print(f"💡 解决方案：")
                print(f"   1. 停止占用该端口的程序")
                print(f"   2. 或修改 PORT 变量使用其他端口")
            else:
                raise

if __name__ == "__main__":
    main() 