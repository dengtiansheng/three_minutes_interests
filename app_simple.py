#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最简单的测试版本 - 用于验证Serverless是否能正常运行
"""

from flask import Flask

# 创建Flask应用
app = Flask(__name__)

@app.route('/')
def index():
    """最简单的首页"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>测试页面</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            h1 { text-align: center; }
            .info {
                background: rgba(255,255,255,0.2);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <h1>✅ Flask应用运行成功！</h1>
        <div class="info">
            <p><strong>状态：</strong>应用正常运行</p>
            <p><strong>环境：</strong>Serverless</p>
            <p><strong>时间：</strong>2025-11-13</p>
        </div>
        <p style="text-align: center;">如果你看到这个页面，说明Flask应用已经成功部署并运行！</p>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    """健康检查"""
    return {'status': 'ok', 'message': '应用运行正常'}

@app.route('/test')
def test():
    """测试路由"""
    return {'test': 'success', 'message': '路由测试成功'}

# 如果直接运行此文件，启动开发服务器
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

