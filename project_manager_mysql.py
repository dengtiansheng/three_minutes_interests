#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三分钟热情项目管理系统 - MySQL数据库版本（重构版）
使用统一的projects表替代原来的三个表（incubator、active_experiments、archive）
通过status字段区分：'concept'（概念）、'active'（实验）、'archived'（存档）
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
    """项目管理核心类 - MySQL数据库版本（使用统一projects表）"""
    
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
        now = datetime.now()
        sql = """
            INSERT INTO projects (idea, notes, status, created_at, updated_at)
            VALUES (%s, %s, 'concept', %s, %s)
        """
        idea_id = self._execute_query(
            sql,
            (idea, notes, now, now),
            fetch=False
        )
        logger.info(f"成功添加想法到孵化池，ID: {idea_id}")
        return idea_id
    
    def remove_from_incubator(self, idea_id: int):
        """从兴趣孵化池移除想法"""
        sql = "DELETE FROM projects WHERE id = %s AND status = 'concept'"
        self._execute_query(sql, (idea_id,), fetch=False)
        logger.info(f"成功移除想法 ID: {idea_id}")
    
    def _load_json(self, table_name_or_path, page: int = None, per_page: int = None) -> List:
        """从数据库表加载数据（兼容原有接口）
        
        Args:
            table_name_or_path: 表名或路径
            page: 页码（从1开始），如果为None则返回所有数据
            per_page: 每页数量，如果为None则返回所有数据
        
        Returns:
            如果指定了分页参数，返回字典 {'items': [...], 'total': 总数, 'page': 页码, 'per_page': 每页数量, 'pages': 总页数}
            否则返回列表（兼容旧接口）
        """
        # 兼容原有接口：可能传入文件路径，需要转换为状态
        if isinstance(table_name_or_path, str):
            if 'incubator' in table_name_or_path:
                status = 'concept'
            elif 'active_experiments' in table_name_or_path:
                status = 'active'
            elif 'archive' in table_name_or_path:
                status = 'archived'
            else:
                # 如果直接传入状态值
                status = table_name_or_path if table_name_or_path in ['concept', 'active', 'archived'] else None
        else:
            status = table_name_or_path if table_name_or_path in ['concept', 'active', 'archived'] else None
        
        if status is None:
            return [] if page is None else {'items': [], 'total': 0, 'page': 1, 'per_page': per_page or 10, 'pages': 0}
        
        # 先查询总数
        count_sql = "SELECT COUNT(*) as total FROM projects WHERE status = %s"
        total_result = self._execute_query(count_sql, (status,))
        total = total_result[0]['total'] if total_result else 0
        
        # 根据状态查询projects表
        if status == 'concept':
            base_sql = """
                SELECT * FROM projects 
                WHERE status = 'concept' 
                ORDER BY created_at DESC
            """
        elif status == 'active':
            base_sql = """
                SELECT * FROM projects 
                WHERE status = 'active' 
                ORDER BY created_at DESC
            """
        elif status == 'archived':
            base_sql = """
                SELECT * FROM projects 
                WHERE status = 'archived' 
                ORDER BY completed_at DESC, created_at DESC
            """
        else:
            return [] if page is None else {'items': [], 'total': 0, 'page': 1, 'per_page': per_page or 10, 'pages': 0}
        
        # 如果指定了分页参数，添加LIMIT和OFFSET
        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            sql = f"{base_sql} LIMIT {per_page} OFFSET {offset}"
        else:
            sql = base_sql
        
        rows = self._execute_query(sql)
        logger.info(f"从projects表查询到 {len(rows)} 条状态为 '{status}' 的记录（总数: {total}）")
        
        # 转换为JSON格式（兼容原有格式）
        result = []
        for row in rows:
            item = dict(row)
            project_id = item['id']
            
            # 查询进度记录（统一使用progress_notes表）
            progress_sql = """
                SELECT created_at, note
                FROM progress_notes
                WHERE project_id = %s
                ORDER BY created_at ASC
            """
            progress_rows = self._execute_query(progress_sql, (project_id,))
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
            
            # 转换Decimal类型为float（用于JSON序列化）
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = float(value)
            
            # 转换日期格式为字符串
            for key in ['created_at', 'updated_at', 'completed_at', 'start_date', 'end_date']:
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
                        if key in ['start_date', 'end_date'] and len(item[key]) > 10:
                            try:
                                dt = datetime.strptime(item[key], '%Y-%m-%d %H:%M:%S')
                                item[key] = dt.strftime('%Y-%m-%d')
                            except:
                                pass
            
            result.append(item)
        
        # 如果指定了分页参数，返回分页结果
        if page is not None and per_page is not None:
            pages = (total + per_page - 1) // per_page if per_page > 0 else 0
            return {
                'items': result,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages
            }
        
        return result
    
    def _save_json(self, table_name_or_path, data: List):
        """保存数据到数据库（兼容原有接口）"""
        # MySQL版本中，数据通过具体方法直接写入数据库
        # 此方法主要用于兼容原有接口，实际不会被调用
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
        now = datetime.now()
        start_date = now
        end_date = start_date + timedelta(days=duration_days)
        
        # 如果提供了idea_id，从孵化池获取信息并更新状态
        if idea_id:
            sql = "SELECT idea, notes FROM projects WHERE id = %s AND status = 'concept'"
            result = self._execute_query(sql, (idea_id,))
            if not result:
                raise ValueError(f"未找到ID为 {idea_id} 的概念想法")
            
            idea_text = result[0]['idea']
            notes = result[0].get('notes', '')  # 保留notes字段
            # 更新状态从 'concept' 到 'active'，保留notes字段
            sql = """
                UPDATE projects 
                SET idea = %s, notes = %s, goal = %s, budget = %s, start_date = %s, end_date = %s, 
                    duration_days = %s, status = 'active', updated_at = %s
                WHERE id = %s
            """
            self._execute_query(
                sql,
                (idea_text, notes, goal, budget, start_date.date(), end_date.date(), 
                 duration_days, now, idea_id),
                fetch=False
            )
            exp_id = idea_id
            logger.info(f"成功将概念 {idea_id} 转换为实验")
        else:
            # 直接创建新实验
            sql = """
                INSERT INTO projects 
                (idea, goal, budget, start_date, end_date, duration_days, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s)
            """
            exp_id = self._execute_query(
                sql,
                (idea_text, goal, budget, start_date.date(), end_date.date(), 
                 duration_days, now, now),
                fetch=False
            )
            logger.info(f"成功创建新实验，ID: {exp_id}")
        
        return exp_id
    
    def add_progress_note(self, experiment_id: int, note: str):
        """为实验添加进度记录"""
        # 检查实验是否存在且状态为active
        sql = "SELECT id FROM projects WHERE id = %s AND status = 'active'"
        result = self._execute_query(sql, (experiment_id,))
        if not result:
            raise ValueError(f"未找到ID为 {experiment_id} 的进行中实验")
        
        sql = """
            INSERT INTO progress_notes (project_id, note, created_at)
            VALUES (%s, %s, %s)
        """
        self._execute_query(sql, (experiment_id, note, datetime.now()), fetch=False)
        logger.info(f"成功为实验 {experiment_id} 添加进度记录")
    
    def complete_experiment(self, experiment_id: int, 
                           skill_learned: str = "",
                           experience: str = "",
                           connection: str = ""):
        """完成实验并归档（更新状态而不是移动数据）"""
        # 获取实验信息
        sql = """
            SELECT * FROM projects WHERE id = %s AND status = 'active'
        """
        result = self._execute_query(sql, (experiment_id,))
        if not result:
            raise ValueError(f"未找到ID为 {experiment_id} 的进行中实验")
        
        exp = result[0]
        
        # 更新状态从 'active' 到 'archived'，并添加归档信息
        completed_at = datetime.now()
        sql = """
            UPDATE projects 
            SET status = 'archived', completed_at = %s, 
                skill_learned = %s, experience = %s, connection = %s,
                updated_at = %s
            WHERE id = %s
        """
        self._execute_query(
            sql,
            (completed_at, skill_learned, experience, connection, completed_at, experiment_id),
            fetch=False
        )
        
        # 进度记录不需要移动，因为它们已经通过project_id关联到projects表
        # 无论项目处于什么状态，进度记录都保留在progress_notes表中
        
        logger.info(f"实验 {experiment_id} 已归档（状态更新为archived）")
        return experiment_id  # 返回相同的ID，因为数据没有移动
    
    # ========== 项目档案馆操作 ==========
    
    def list_archive(self):
        """列出所有已归档的项目"""
        return self._load_json('archived')
    
    def get_statistics(self):
        """获取统计信息"""
        try:
            # 直接查询projects表，按状态分组统计
            sql = """
                SELECT status, COUNT(*) as count
                FROM projects
                GROUP BY status
            """
            rows = self._execute_query(sql)
            
            # 初始化计数
            incubator_count = 0
            active_count = 0
            archive_count = 0
            
            for row in rows:
                if row['status'] == 'concept':
                    incubator_count = row['count']
                elif row['status'] == 'active':
                    active_count = row['count']
                elif row['status'] == 'archived':
                    archive_count = row['count']
            
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
