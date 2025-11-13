#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三分钟热情项目管理系统 - Web界面
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from project_manager import ProjectManager
from datetime import datetime, timedelta

app = Flask(__name__)
pm = ProjectManager()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/incubator', methods=['GET'])
def get_incubator():
    """获取兴趣孵化池列表"""
    ideas = pm._load_json(pm.incubator_file)
    return jsonify(ideas)


@app.route('/api/incubator', methods=['POST'])
def add_incubator():
    """添加想法到兴趣孵化池"""
    data = request.json
    idea = data.get('idea', '')
    notes = data.get('notes', '')
    if idea:
        pm.add_to_incubator(idea, notes)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '想法不能为空'})


@app.route('/api/incubator/<int:idea_id>', methods=['DELETE'])
def remove_incubator(idea_id):
    """从兴趣孵化池移除想法"""
    pm.remove_from_incubator(idea_id)
    return jsonify({'success': True})


@app.route('/api/experiments', methods=['GET'])
def get_experiments():
    """获取进行中的实验列表"""
    experiments = pm._load_json(pm.active_file)
    active = [e for e in experiments if e.get('status') == 'active']
    
    # 计算剩余天数
    now = datetime.now()
    for exp in active:
        end_date = datetime.strptime(exp['end_date'], '%Y-%m-%d')
        days_left = (end_date - now).days
        exp['days_left'] = days_left
    
    return jsonify(active)


@app.route('/api/experiments', methods=['POST'])
def start_experiment():
    """启动新实验"""
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
    
    try:
        exp_id = pm.start_experiment(
            idea_id=idea_id,
            idea_text=idea_text,
            goal=goal,
            budget=budget,
            duration_days=days
        )
        return jsonify({'success': True, 'id': exp_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/experiments/<int:exp_id>/progress', methods=['POST'])
def add_progress(exp_id):
    """添加进度记录"""
    data = request.json
    note = data.get('note', '')
    if note:
        pm.add_progress_note(exp_id, note)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '进度记录不能为空'})


@app.route('/api/experiments/<int:exp_id>/complete', methods=['POST'])
def complete_experiment(exp_id):
    """完成实验"""
    data = request.json
    skill = data.get('skill', '')
    experience = data.get('experience', '')
    connection = data.get('connection', '')
    
    try:
        archive_id = pm.complete_experiment(
            exp_id,
            skill_learned=skill,
            experience=experience,
            connection=connection
        )
        return jsonify({'success': True, 'id': archive_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/archive', methods=['GET'])
def get_archive():
    """获取项目档案馆列表"""
    archive = pm._load_json(pm.archive_file)
    return jsonify(archive)


@app.route('/api/archive/<int:archive_id>', methods=['GET'])
def get_archive_item(archive_id):
    """获取单个归档项目详情"""
    archive = pm._load_json(pm.archive_file)
    item = next((a for a in archive if a['id'] == archive_id), None)
    if item:
        return jsonify(item)
    return jsonify({'error': '未找到归档项目'}), 404


@app.route('/api/archive/<int:archive_id>', methods=['DELETE'])
def delete_archive_item(archive_id):
    """删除归档项目"""
    try:
        archive = pm._load_json(pm.archive_file)
        original_count = len(archive)
        archive = [a for a in archive if a['id'] != archive_id]
        
        if len(archive) == original_count:
            return jsonify({'success': False, 'error': '未找到要删除的项目'}), 404
        
        pm._save_json(pm.archive_file, archive)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/experiments/<int:exp_id>', methods=['GET'])
def get_experiment(exp_id):
    """获取单个实验详情"""
    experiments = pm._load_json(pm.active_file)
    exp = next((e for e in experiments if e['id'] == exp_id), None)
    if exp:
        # 计算剩余天数
        end_date = datetime.strptime(exp['end_date'], '%Y-%m-%d')
        days_left = (end_date - datetime.now()).days
        exp['days_left'] = days_left
        return jsonify(exp)
    return jsonify({'error': '未找到实验'}), 404


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    incubator = pm._load_json(pm.incubator_file)
    active = pm._load_json(pm.active_file)
    archive = pm._load_json(pm.archive_file)
    
    active_count = len([e for e in active if e.get('status') == 'active'])
    pending_ideas = len([i for i in incubator if i.get('status') == 'pending'])
    
    return jsonify({
        'incubator_count': pending_ideas,
        'active_count': active_count,
        'archive_count': len(archive),
        'total_explored': len(archive)
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("三分钟热情项目管理系统 - Web界面")
    print("="*60)
    print("访问地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务器")
    print("="*60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)

