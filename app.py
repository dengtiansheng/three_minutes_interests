#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三分钟热情项目管理系统 - Web界面
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from decimal import Decimal
import os
import sys

# 尝试加载.env文件（如果安装了python-dotenv）
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载.env文件中的环境变量
except ImportError:
    # 如果没有安装python-dotenv，忽略错误
    pass

# 检测是否为Serverless环境
is_serverless = bool(
    os.environ.get('TENCENTCLOUD_RUNENV') or 
    os.environ.get('SCF_RUNTIME') or 
    os.environ.get('SERVERLESS')
)

# 创建Flask应用
app = Flask(__name__)

# 配置日志（简化，避免阻塞）
if is_serverless:
    import logging
    logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
    app.logger.setLevel(logging.ERROR)
else:
    import logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

# 延迟初始化ProjectManager
pm = None

def get_project_manager():
    """获取ProjectManager实例（懒加载）- 仅使用MySQL版本"""
    global pm
    if pm is None:
        # MySQL配置（从环境变量读取，确保安全性）
        mysql_host = os.environ.get('MYSQL_HOST')
        mysql_port = int(os.environ.get('MYSQL_PORT', '3306'))
        mysql_user = os.environ.get('MYSQL_USER', 'root')
        mysql_password = os.environ.get('MYSQL_PASSWORD')
        mysql_database = os.environ.get('MYSQL_DATABASE', 'threemins')
        
        # 检查必需的配置
        if not mysql_host:
            raise RuntimeError("请设置环境变量 MYSQL_HOST")
        if not mysql_password:
            raise RuntimeError("请设置环境变量 MYSQL_PASSWORD")
        
        # 使用MySQL
        from project_manager_mysql import ProjectManagerMySQL
        pm = ProjectManagerMySQL(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database
        )
        if not is_serverless:
            app.logger.info("使用MySQL数据库存储")
    return pm


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/incubator', methods=['GET'])
def get_incubator():
    """获取兴趣孵化池列表"""
    try:
        pm = get_project_manager()
        # 获取分页参数
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=10)
        
        result = pm._load_json(pm.incubator_file, page=page, per_page=per_page)
        
        # 如果是分页结果，转换items中的Decimal
        if isinstance(result, dict):
            result['items'] = convert_decimals(result['items'])
            return jsonify(result)
        else:
            # 兼容旧接口（无分页）
            ideas = convert_decimals(result)
            return jsonify(ideas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/incubator', methods=['POST'])
def add_incubator():
    """添加想法到兴趣孵化池"""
    try:
        data = request.json
        idea = data.get('idea', '')
        notes = data.get('notes', '')
        if idea:
            pm = get_project_manager()
            idea_id = pm.add_to_incubator(idea, notes)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '想法不能为空'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/incubator/<int:idea_id>', methods=['DELETE'])
def remove_incubator(idea_id):
    """从兴趣孵化池移除想法"""
    try:
        pm = get_project_manager()
        pm.remove_from_incubator(idea_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def convert_decimals(obj):
    """递归转换Decimal类型为float"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    else:
        return obj

@app.route('/api/experiments', methods=['GET'])
def get_experiments():
    """获取进行中的实验列表"""
    try:
        pm = get_project_manager()
        # 获取分页参数
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=10)
        
        result = pm._load_json(pm.active_file, page=page, per_page=per_page)
        
        # 判断是分页结果还是列表结果
        if isinstance(result, dict):
            experiments = result['items']
            is_paginated = True
        else:
            experiments = result
            is_paginated = False
        
        # MySQL版本已经通过SQL查询过滤了active状态
        # 计算剩余天数
        now = datetime.now()
        for exp in experiments:
            end_date_str = exp.get('end_date', '')
            if isinstance(end_date_str, str):
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    days_left = (end_date - now).days
                    exp['days_left'] = days_left
                except Exception as e:
                    app.logger.warning(f"解析日期失败: {end_date_str}, 错误: {e}")
                    exp['days_left'] = 0
            else:
                exp['days_left'] = 0
        
        # 确保所有Decimal类型都被转换
        experiments = convert_decimals(experiments)
        
        app.logger.info(f"返回 {len(experiments)} 个进行中的实验")
        
        # 如果是分页结果，返回分页格式
        if is_paginated:
            result['items'] = experiments
            return jsonify(result)
        else:
            return jsonify(experiments)
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        app.logger.error(f"获取实验列表失败: {error_msg}")
        return jsonify({'error': str(e), 'traceback': error_msg}), 500


@app.route('/api/experiments', methods=['POST'])
def start_experiment():
    """启动新实验"""
    try:
        data = request.json
        idea_id = data.get('idea_id')
        idea_text = data.get('idea', '')
        goal = data.get('goal', '')
        budget = float(data.get('budget', 0))
        days = int(data.get('days', 21))
        
        if not goal:
            return jsonify({'success': False, 'error': '目标不能为空'})
        
        # 将idea_id转换为整数（如果提供）
        if idea_id:
            try:
                idea_id = int(idea_id)
            except (ValueError, TypeError):
                idea_id = None
        
        pm = get_project_manager()
        exp_id = pm.start_experiment(
            idea_id=idea_id,
            idea_text=idea_text,
            goal=goal,
            budget=budget,
            duration_days=days
        )
        return jsonify({'success': True, 'id': exp_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/experiments/<int:exp_id>/progress', methods=['POST'])
def add_progress(exp_id):
    """添加进度记录"""
    try:
        data = request.json
        note = data.get('note', '')
        if note:
            pm = get_project_manager()
            pm.add_progress_note(exp_id, note)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '进度记录不能为空'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/experiments/<int:exp_id>/complete', methods=['POST'])
def complete_experiment(exp_id):
    """完成实验"""
    try:
        data = request.json
        skill = data.get('skill', '')
        experience = data.get('experience', '')
        connection = data.get('connection', '')
        
        pm = get_project_manager()
        archive_id = pm.complete_experiment(
            exp_id,
            skill_learned=skill,
            experience=experience,
            connection=connection
        )
        return jsonify({'success': True, 'id': archive_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/archive', methods=['GET'])
def get_archive():
    """获取项目档案馆列表"""
    try:
        pm = get_project_manager()
        # 获取分页参数
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=10)
        
        result = pm._load_json(pm.archive_file, page=page, per_page=per_page)
        
        # 如果是分页结果，转换items中的Decimal
        if isinstance(result, dict):
            result['items'] = convert_decimals(result['items'])
            return jsonify(result)
        else:
            # 兼容旧接口（无分页）
            archive = convert_decimals(result)
            return jsonify(archive)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/archive/<int:archive_id>', methods=['GET'])
def get_archive_item(archive_id):
    """获取单个归档项目详情"""
    try:
        pm = get_project_manager()
        archive = pm._load_json(pm.archive_file)
        item = next((a for a in archive if a['id'] == archive_id), None)
        if item:
            item = convert_decimals(item)
            return jsonify(item)
        return jsonify({'error': '未找到归档项目'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/archive/<int:archive_id>', methods=['DELETE'])
def delete_archive_item(archive_id):
    """删除归档项目"""
    try:
        pm = get_project_manager()
        # MySQL版本：直接删除数据库记录（使用统一的projects表）
        sql = "DELETE FROM projects WHERE id = %s AND status = 'archived'"
        pm._execute_query(sql, (archive_id,), fetch=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/experiments/<int:exp_id>', methods=['GET'])
def get_experiment(exp_id):
    """获取单个实验详情"""
    try:
        pm = get_project_manager()
        experiments = pm._load_json(pm.active_file)
        exp = next((e for e in experiments if e['id'] == exp_id), None)
        if exp:
            # 计算剩余天数
            end_date_str = exp.get('end_date', '')
            if isinstance(end_date_str, str):
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    days_left = (end_date - datetime.now()).days
                    exp['days_left'] = days_left
                except:
                    exp['days_left'] = 0
            else:
                exp['days_left'] = 0
            exp = convert_decimals(exp)
            return jsonify(exp)
        return jsonify({'error': '未找到实验'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        pm = get_project_manager()
        stats = pm.get_statistics()
        stats = convert_decimals(stats)
        return jsonify(stats)
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


# 如果直接运行此文件，启动开发服务器
# 根据腾讯云文档：Web Function必须监听0.0.0.0:9000
if __name__ == '__main__':
    # Serverless环境：监听0.0.0.0:9000
    # 本地开发：监听127.0.0.1:9000
    if os.environ.get('TENCENTCLOUD_RUNENV') or os.environ.get('SCF_RUNTIME'):
        # Serverless环境
        app.run(host='0.0.0.0', port=9000)
    else:
        # 本地开发环境
        app.run(debug=True, host='127.0.0.1', port=9000)
