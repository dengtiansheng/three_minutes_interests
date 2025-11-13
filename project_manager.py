#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三分钟热情项目管理系统
用于管理兴趣孵化池、进行中实验和项目档案馆
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional


class ProjectManager:
    """项目管理核心类"""
    
    def __init__(self, data_dir: str = "project_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 创建备份目录
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.incubator_file = self.data_dir / "incubator.json"
        self.active_file = self.data_dir / "active_experiments.json"
        self.archive_file = self.data_dir / "archive.json"
        
        self._init_files()
    
    def _init_files(self):
        """初始化数据文件"""
        if not self.incubator_file.exists():
            self._save_json(self.incubator_file, [])
        if not self.active_file.exists():
            self._save_json(self.active_file, [])
        if not self.archive_file.exists():
            self._save_json(self.archive_file, [])
    
    def _load_json(self, file_path: Path) -> List:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _create_backup(self, file_path: Path):
        """创建文件备份"""
        if not file_path.exists():
            return
        
        try:
            # 生成带时间戳的备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}.json"
            backup_path = self.backup_dir / backup_name
            
            # 复制文件到备份目录
            shutil.copy2(file_path, backup_path)
            
            # 只保留最近5个备份
            self._cleanup_old_backups(file_path.stem)
        except Exception:
            # 备份失败不影响主流程，静默处理
            pass
    
    def _cleanup_old_backups(self, file_prefix: str):
        """清理旧的备份文件，只保留最近5个"""
        try:
            backups = sorted(
                self.backup_dir.glob(f"{file_prefix}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            # 删除第6个及以后的备份
            for backup in backups[5:]:
                backup.unlink()
        except Exception:
            pass  # 清理失败不影响主流程
    
    def _save_json(self, file_path: Path, data: List):
        """安全保存JSON文件（带备份和原子写入）"""
        # 1. 创建备份（如果文件已存在）
        if file_path.exists():
            self._create_backup(file_path)
        
        # 2. 原子写入：先写入临时文件
        temp_file = None
        try:
            # 创建临时文件（在同一目录下，确保在同一文件系统）
            temp_file = file_path.with_suffix('.tmp')
            
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 验证JSON格式
            with open(temp_file, 'r', encoding='utf-8') as f:
                json.load(f)  # 如果格式错误会抛出异常
            
            # 3. 原子替换：重命名临时文件为正式文件
            # Windows需要先删除目标文件（如果存在）
            if file_path.exists():
                file_path.unlink()
            temp_file.replace(file_path)
            
        except json.JSONEncodeError as e:
            # JSON编码错误
            if temp_file and temp_file.exists():
                temp_file.unlink()
            raise ValueError(f"数据格式错误，无法保存: {e}")
        
        except Exception as e:
            # 其他错误，尝试恢复备份
            if temp_file and temp_file.exists():
                temp_file.unlink()
            
            # 如果原文件被损坏，尝试从备份恢复
            if not file_path.exists() or self._is_json_corrupted(file_path):
                self._restore_from_backup(file_path)
            
            raise RuntimeError(f"保存文件失败: {e}")
    
    def _is_json_corrupted(self, file_path: Path) -> bool:
        """检查JSON文件是否损坏"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return False
        except (json.JSONDecodeError, ValueError):
            return True
    
    def _restore_from_backup(self, file_path: Path):
        """从备份恢复文件"""
        try:
            # 找到最新的备份
            backups = sorted(
                self.backup_dir.glob(f"{file_path.stem}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if backups:
                shutil.copy2(backups[0], file_path)
                return True
        except Exception:
            pass
        
        return False
    
    # ========== 兴趣孵化池操作 ==========
    
    def add_to_incubator(self, idea: str, notes: str = ""):
        """添加想法到兴趣孵化池"""
        ideas = self._load_json(self.incubator_file)
        new_idea = {
            "id": len(ideas) + 1,
            "idea": idea,
            "notes": notes,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending"
        }
        ideas.append(new_idea)
        self._save_json(self.incubator_file, ideas)
        return new_idea["id"]
    
    def list_incubator(self):
        """列出兴趣孵化池中的所有想法（返回列表）"""
        return self._load_json(self.incubator_file)
    
    def remove_from_incubator(self, idea_id: int):
        """从兴趣孵化池移除想法"""
        ideas = self._load_json(self.incubator_file)
        ideas = [i for i in ideas if i["id"] != idea_id]
        self._save_json(self.incubator_file, ideas)
    
    # ========== 进行中实验操作 ==========
    
    def start_experiment(self, idea_id: Optional[int] = None, 
                        idea_text: str = "", 
                        goal: str = "", 
                        budget: float = 0.0,
                        duration_days: int = 21):
        """从孵化池启动实验，或直接创建新实验"""
        active_experiments = self._load_json(self.active_file)
        
        # 如果提供了idea_id，从孵化池获取信息
        if idea_id:
            ideas = self._load_json(self.incubator_file)
            idea_obj = next((i for i in ideas if i["id"] == idea_id), None)
            if not idea_obj:
                raise ValueError(f"未找到ID为 {idea_id} 的想法")
            idea_text = idea_obj["idea"]
            # 标记为已启动
            ideas = [i for i in ideas if i["id"] != idea_id]
            self._save_json(self.incubator_file, ideas)
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        new_experiment = {
            "id": len(active_experiments) + 1,
            "idea": idea_text,
            "goal": goal,
            "budget": budget,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "duration_days": duration_days,
            "status": "active",
            "progress_notes": [],
            "created_at": start_date.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        active_experiments.append(new_experiment)
        self._save_json(self.active_file, active_experiments)
        return new_experiment["id"]
    
    def list_active_experiments(self):
        """列出所有进行中的实验（返回列表）"""
        experiments = self._load_json(self.active_file)
        return [e for e in experiments if e.get("status") == "active"]
    
    def add_progress_note(self, experiment_id: int, note: str):
        """为实验添加进度记录"""
        experiments = self._load_json(self.active_file)
        exp = next((e for e in experiments if e["id"] == experiment_id), None)
        
        if not exp:
            print(f"[错误] 未找到ID为 {experiment_id} 的实验")
            return
        
        if "progress_notes" not in exp:
            exp["progress_notes"] = []
        
        progress_note = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "note": note
        }
        exp["progress_notes"].append(progress_note)
        self._save_json(self.active_file, experiments)
    
    def complete_experiment(self, experiment_id: int, 
                           skill_learned: str = "",
                           experience: str = "",
                           connection: str = ""):
        """完成实验并归档"""
        experiments = self._load_json(self.active_file)
        exp = next((e for e in experiments if e["id"] == experiment_id), None)
        
        if not exp:
            raise ValueError(f"未找到ID为 {experiment_id} 的实验")
        
        # 标记为已完成
        exp["status"] = "completed"
        exp["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 创建归档记录
        archive = self._load_json(self.archive_file)
        archive_entry = {
            "id": len(archive) + 1,
            "idea": exp["idea"],
            "goal": exp["goal"],
            "start_date": exp["start_date"],
            "end_date": exp["end_date"],
            "completed_at": exp["completed_at"],
            "skill_learned": skill_learned,
            "experience": experience,
            "connection": connection,
            "progress_notes": exp.get("progress_notes", [])
        }
        archive.append(archive_entry)
        self._save_json(self.archive_file, archive)
        
        # 从进行中列表移除
        experiments = [e for e in experiments if e["id"] != experiment_id]
        self._save_json(self.active_file, experiments)
        
        return archive_entry["id"]
    
    # ========== 项目档案馆操作 ==========
    
    def list_archive(self):
        """列出所有已归档的项目（返回列表）"""
        return self._load_json(self.archive_file)
    
    def get_statistics(self):
        """获取统计信息（返回字典）"""
        incubator = self._load_json(self.incubator_file)
        active = self._load_json(self.active_file)
        archive = self._load_json(self.archive_file)
        
        active_count = len([e for e in active if e.get("status") == "active"])
        pending_ideas = len([i for i in incubator if i.get("status") == "pending"])
        
        return {
            "incubator_count": pending_ideas,
            "active_count": active_count,
            "archive_count": len(archive),
            "total_explored": len(archive)
        }

