#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三分钟热情项目管理系统 - MySQL数据库版本
使用MySQL数据库来持久化数据
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logger.warning("PyMySQL未安装，无法使用MySQL存储")


class ProjectManagerMySQL:
    """项目管理核心类 - MySQL数据库版本"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str = 'threemins'):
        if not MYSQL_AVAILABLE:
            raise RuntimeError("PyMySQL未安装，请安装: pip install pymysql")
        
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        
        # 测试连接
        self._test_connection()
    
    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            conn = self._get_connection()
            conn.close()
            logger.info("MySQL数据库连接成功")
        except Exception as e:
            logger.error(f"MySQL数据库连接失败: {e}")
            raise
    
    def _execute_query(self, sql: str, params: tuple = None, fetch: bool = True):
        """执行SQL查询"""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                if fetch:
                    result = cursor.fetchall()
                    conn.commit()
                    return result
                else:
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"SQL执行失败: {sql}, 参数: {params}, 错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            if conn:
                conn.close()
    
    # ========== 兴趣孵化池操作 ==========
    
    def add_to_incubator(self, idea: str, notes: str = ""):
        """添加想法到兴趣孵化池"""
        sql = """
            INSERT INTO incubator (idea, notes, created_at, status)
            VALUES (%s, %s, %s, 'pending')
        """
        idea_id = self._execute_query(
            sql,
            (idea, notes, datetime.now()),
            fetch=False
        )
        logger.info(f"成功添加想法到孵化池，ID: {idea_id}")
        return idea_id
    
    def remove_from_incubator(self, idea_id: int):
        """从兴趣孵化池移除想法"""
        sql = "DELETE FROM incubator WHERE id = %s"
        self._execute_query(sql, (idea_id,), fetch=False)
        logger.info(f"成功移除想法 ID: {idea_id}")
    
    def _load_json(self, table_name_or_path) -> List:
        """从数据库表加载数据（兼容原有接口）"""
        # 兼容原有接口：可能传入文件路径，需要转换为表名
        if isinstance(table_name_or_path, str):
            if 'incubator' in table_name_or_path:
                table_name = 'incubator'
            elif 'active_experiments' in table_name_or_path:
                table_name = 'active_experiments'
            elif 'archive' in table_name_or_path:
                table_name = 'archive'
            else:
                table_name = table_name_or_path
        else:
            table_name = table_name_or_path
        
        if table_name == 'incubator':
            sql = "SELECT * FROM incubator WHERE status = 'pending' ORDER BY created_at DESC"
        elif table_name == 'active_experiments':
            # 先查询实验基本信息，进度记录单独查询
            sql = """
                SELECT e.*
                FROM active_experiments e
                WHERE e.status = 'active'
                ORDER BY e.created_at DESC
            """
        elif table_name == 'archive':
            # 先查询归档项目基本信息，进度记录单独查询
            sql = """
                SELECT a.*
                FROM archive a
                ORDER BY a.completed_at DESC
            """
        else:
            return []
        
        rows = self._execute_query(sql)
        logger.info(f"从表 {table_name} 查询到 {len(rows)} 条记录")
        
        # 转换为JSON格式（兼容原有格式）
        result = []
        for row in rows:
            item = dict(row)
            
            # 处理progress_notes
            if table_name == 'active_experiments':
                # 为每个实验单独查询进度记录
                exp_id = item['id']
                progress_sql = """
                    SELECT created_at, note
                    FROM progress_notes
                    WHERE experiment_id = %s
                    ORDER BY created_at ASC
                """
                progress_rows = self._execute_query(progress_sql, (exp_id,))
                item['progress_notes'] = []
                for p_row in progress_rows:
                    # 在Python中格式化时间
                    created_at = p_row['created_at']
                    if isinstance(created_at, datetime):
                        date_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = str(created_at)
                    item['progress_notes'].append({
                        'date': date_str,
                        'note': p_row['note']
                    })
            elif table_name == 'archive':
                # 归档项目的进度记录
                archive_id = item['id']
                progress_sql = """
                    SELECT created_at, note
                    FROM archive_progress_notes
                    WHERE archive_id = %s
                    ORDER BY created_at ASC
                """
                progress_rows = self._execute_query(progress_sql, (archive_id,))
                item['progress_notes'] = []
                for p_row in progress_rows:
                    created_at = p_row['created_at']
                    if isinstance(created_at, datetime):
                        date_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = str(created_at)
                    item['progress_notes'].append({
                        'date': date_str,
                        'note': p_row['note']
                    })
            elif 'progress_notes_json' in item and item['progress_notes_json']:
                # 兼容旧的GROUP_CONCAT方式（如果存在）
                import json
                try:
                    progress_notes_str = '[' + item['progress_notes_json'] + ']'
                    progress_notes = json.loads(progress_notes_str)
                    # 检查并修复日期格式（如果返回的是格式字符串）
                    for note in progress_notes:
                        if 'date' in note and '%' in str(note['date']):
                            logger.warning(f"检测到格式字符串，尝试重新查询时间: {note['date']}")
                    item['progress_notes'] = progress_notes
                except Exception as e:
                    logger.warning(f"解析进度记录失败: {e}, 原始数据: {item.get('progress_notes_json', '')}")
                    item['progress_notes'] = []
            else:
                item['progress_notes'] = []
            
            # 删除临时字段
            item.pop('progress_notes_json', None)
            
            # 转换Decimal类型为float（用于JSON序列化）
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = float(value)
            
            # 转换日期格式为字符串
            for key in ['created_at', 'completed_at', 'start_date', 'end_date']:
                if key in item and item[key]:
                    if isinstance(item[key], datetime):
                        if key in ['start_date', 'end_date']:
                            item[key] = item[key].strftime('%Y-%m-%d')
                        else:
                            item[key] = item[key].strftime('%Y-%m-%d %H:%M:%S')
                    elif hasattr(item[key], 'strftime'):
                        # date对象
                        if key in ['start_date', 'end_date']:
                            item[key] = item[key].strftime('%Y-%m-%d')
                        else:
                            item[key] = item[key].strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(item[key], str):
                        # 已经是字符串格式，确保格式正确
                        # 如果是datetime字符串，转换为date格式（start_date/end_date）
                        if key in ['start_date', 'end_date'] and len(item[key]) > 10:
                            try:
                                dt = datetime.strptime(item[key], '%Y-%m-%d %H:%M:%S')
                                item[key] = dt.strftime('%Y-%m-%d')
                            except:
                                pass
            
            result.append(item)
        
        return result
    
    def _save_json(self, table_name_or_path, data: List):
        """保存数据到数据库（兼容原有接口）"""
        # MySQL版本中，数据通过具体方法直接写入数据库
        # 此方法主要用于兼容原有接口，实际不会被调用
        # 但为了兼容性，保留此方法
        pass
    
    # 兼容原有接口：提供文件路径属性
    @property
    def incubator_file(self):
        return 'incubator'
    
    @property
    def active_file(self):
        return 'active_experiments'
    
    @property
    def archive_file(self):
        return 'archive'
    
    # ========== 进行中实验操作 ==========
    
    def start_experiment(self, idea_id: Optional[int] = None, 
                        idea_text: str = "", 
                        goal: str = "", 
                        budget: float = 0.0,
                        duration_days: int = 21):
        """从孵化池启动实验，或直接创建新实验"""
        # 如果提供了idea_id，从孵化池获取信息
        if idea_id:
            sql = "SELECT idea FROM incubator WHERE id = %s"
            result = self._execute_query(sql, (idea_id,))
            if not result:
                raise ValueError(f"未找到ID为 {idea_id} 的想法")
            idea_text = result[0]['idea']
            # 从孵化池删除
            self.remove_from_incubator(idea_id)
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        sql = """
            INSERT INTO active_experiments 
            (idea, goal, budget, start_date, end_date, duration_days, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'active', %s)
        """
        exp_id = self._execute_query(
            sql,
            (idea_text, goal, budget, start_date.date(), end_date.date(), duration_days, start_date),
            fetch=False
        )
        logger.info(f"成功启动实验，ID: {exp_id}")
        return exp_id
    
    def add_progress_note(self, experiment_id: int, note: str):
        """为实验添加进度记录"""
        # 检查实验是否存在
        sql = "SELECT id FROM active_experiments WHERE id = %s AND status = 'active'"
        result = self._execute_query(sql, (experiment_id,))
        if not result:
            raise ValueError(f"未找到ID为 {experiment_id} 的实验")
        
        sql = """
            INSERT INTO progress_notes (experiment_id, note, created_at)
            VALUES (%s, %s, %s)
        """
        self._execute_query(sql, (experiment_id, note, datetime.now()), fetch=False)
        logger.info(f"成功为实验 {experiment_id} 添加进度记录")
    
    def complete_experiment(self, experiment_id: int, 
                           skill_learned: str = "",
                           experience: str = "",
                           connection: str = ""):
        """完成实验并归档"""
        # 获取实验信息
        sql = """
            SELECT e.*, 
                   GROUP_CONCAT(
                       CONCAT('{"date":"', DATE_FORMAT(p.created_at, '%%Y-%%m-%%d %%H:%%i:%%s'), '","note":"', REPLACE(REPLACE(REPLACE(REPLACE(p.note, '\\\\', '\\\\\\\\'), '"', '\\\\"'), CHAR(13), '\\\\r'), CHAR(10), '\\\\n'), '"}')
                       ORDER BY p.created_at SEPARATOR ','
                   ) as progress_notes_json
            FROM active_experiments e
            LEFT JOIN progress_notes p ON e.id = p.experiment_id
            WHERE e.id = %s
            GROUP BY e.id
        """
        result = self._execute_query(sql, (experiment_id,))
        if not result:
            raise ValueError(f"未找到ID为 {experiment_id} 的实验")
        
        exp = result[0]
        
        # 创建归档记录
        completed_at = datetime.now()
        sql = """
            INSERT INTO archive 
            (idea, goal, start_date, end_date, completed_at, skill_learned, experience, connection)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        archive_id = self._execute_query(
            sql,
            (exp['idea'], exp['goal'], exp['start_date'], exp['end_date'], 
             completed_at, skill_learned, experience, connection),
            fetch=False
        )
        
        # 复制进度记录到归档表
        if exp.get('progress_notes_json'):
            import json
            try:
                progress_notes_str = '[' + exp['progress_notes_json'] + ']'
                progress_notes = json.loads(progress_notes_str)
                for note in progress_notes:
                    sql = """
                        INSERT INTO archive_progress_notes (archive_id, note, created_at)
                        VALUES (%s, %s, %s)
                    """
                    note_date = datetime.strptime(note['date'], '%Y-%m-%d %H:%M:%S')
                    self._execute_query(sql, (archive_id, note['note'], note_date), fetch=False)
            except Exception as e:
                logger.warning(f"复制进度记录失败: {e}")
        
        # 删除实验记录
        sql = "DELETE FROM active_experiments WHERE id = %s"
        self._execute_query(sql, (experiment_id,), fetch=False)
        
        logger.info(f"实验 {experiment_id} 已归档，归档ID: {archive_id}")
        return archive_id
    
    # ========== 项目档案馆操作 ==========
    
    def list_archive(self):
        """列出所有已归档的项目"""
        return self._load_json('archive')
    
    def get_statistics(self):
        """获取统计信息"""
        try:
            incubator_count = len(self._load_json('incubator'))
            active_count = len(self._load_json('active_experiments'))
            archive_count = len(self._load_json('archive'))
            
            return {
                'incubator_count': incubator_count,
                'active_count': active_count,
                'archive_count': archive_count,
                'total_explored': archive_count
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            # 返回默认值
            return {
                'incubator_count': 0,
                'active_count': 0,
                'archive_count': 0,
                'total_explored': 0
            }

