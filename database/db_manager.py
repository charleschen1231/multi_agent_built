# database/db_manager.py
import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, Dataset, GeneratedData, SystemConfig, Execution, TrainingJob


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认存储在项目目录下的 data 文件夹中
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'data', 'app.db')
        
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # 创建表
        self._create_tables()
    
    def _create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    # ==================== Dataset 操作 ====================
    
    def create_dataset(self, name: str, file_path: str, type: str = 'test',
                       description: str = None, file_format: str = 'jsonl',
                       record_count: int = 0) -> Dataset:
        """创建数据集记录"""
        session = self.get_session()
        try:
            dataset = Dataset(
                name=name,
                description=description,
                type=type,
                file_path=file_path,
                file_format=file_format,
                record_count=record_count
            )
            session.add(dataset)
            session.commit()
            session.refresh(dataset)
            return dataset
        finally:
            session.close()
    
    def get_dataset(self, dataset_id: int) -> Optional[Dataset]:
        """获取数据集"""
        session = self.get_session()
        try:
            return session.query(Dataset).filter(Dataset.id == dataset_id).first()
        finally:
            session.close()
    
    def get_all_datasets(self, type: str = None) -> List[Dataset]:
        """获取所有数据集"""
        session = self.get_session()
        try:
            query = session.query(Dataset)
            if type:
                query = query.filter(Dataset.type == type)
            return query.order_by(desc(Dataset.created_at)).all()
        finally:
            session.close()
    
    def delete_dataset(self, dataset_id: int) -> bool:
        """删除数据集"""
        session = self.get_session()
        try:
            dataset = session.query(Dataset).filter(Dataset.id == dataset_id).first()
            if dataset:
                session.delete(dataset)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    # ==================== SystemConfig 操作 ====================
    
    def create_system_config(self, name: str, config_json: dict,
                           description: str = None) -> SystemConfig:
        """创建系统配置"""
        session = self.get_session()
        try:
            config = SystemConfig(
                name=name,
                description=description,
                config_json=config_json,
                agent_count=len(config_json) if isinstance(config_json, list) else 0
            )
            session.add(config)
            session.commit()
            session.refresh(config)
            return config
        finally:
            session.close()
    
    def update_config_validation(self, config_id: int, is_valid: bool,
                                  errors: str = None, execution_order: list = None):
        """更新配置校验状态"""
        session = self.get_session()
        try:
            config = session.query(SystemConfig).filter(SystemConfig.id == config_id).first()
            if config:
                config.is_valid = is_valid
                config.validation_errors = errors
                if execution_order:
                    config.execution_order = execution_order
                session.commit()
        finally:
            session.close()
    
    def get_system_config(self, config_id: int) -> Optional[SystemConfig]:
        """获取系统配置"""
        session = self.get_session()
        try:
            return session.query(SystemConfig).filter(SystemConfig.id == config_id).first()
        finally:
            session.close()
    
    def get_all_system_configs(self, only_valid: bool = False) -> List[SystemConfig]:
        """获取所有系统配置"""
        session = self.get_session()
        try:
            query = session.query(SystemConfig)
            if only_valid:
                query = query.filter(SystemConfig.is_valid == True)
            return query.order_by(desc(SystemConfig.created_at)).all()
        finally:
            session.close()
    
    def delete_system_config(self, config_id: int) -> bool:
        """删除系统配置"""
        session = self.get_session()
        try:
            config = session.query(SystemConfig).filter(SystemConfig.id == config_id).first()
            if config:
                session.delete(config)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    # ==================== GeneratedData 操作 ====================
    
    def create_generated_data(self, agent_id: str, trajectory: dict,
                             dataset_id: int = None, config_id: int = None,
                             input_data: dict = None, output_data: dict = None,
                             ground_truth: dict = None, metadata: dict = None) -> GeneratedData:
        """创建生成的轨迹数据"""
        session = self.get_session()
        try:
            data = GeneratedData(
                dataset_id=dataset_id,
                config_id=config_id,
                agent_id=agent_id,
                input_data=input_data,
                output_data=output_data,
                trajectory=trajectory,
                ground_truth=ground_truth,
                metadata=metadata
            )
            session.add(data)
            session.commit()
            session.refresh(data)
            return data
        finally:
            session.close()
    
    def get_generated_data_by_config(self, config_id: int) -> List[GeneratedData]:
        """获取指定配置生成的数据"""
        session = self.get_session()
        try:
            return session.query(GeneratedData).filter(
                GeneratedData.config_id == config_id
            ).order_by(desc(GeneratedData.created_at)).all()
        finally:
            session.close()
    
    def get_generated_data_by_dataset(self, dataset_id: int) -> List[GeneratedData]:
        """获取指定数据集生成的数据"""
        session = self.get_session()
        try:
            return session.query(GeneratedData).filter(
                GeneratedData.dataset_id == dataset_id
            ).order_by(desc(GeneratedData.created_at)).all()
        finally:
            session.close()
    
    # ==================== Execution 操作 ====================
    
    def create_execution(self, config_id: int, dataset_id: int = None) -> Execution:
        """创建执行记录"""
        session = self.get_session()
        try:
            execution = Execution(
                config_id=config_id,
                dataset_id=dataset_id,
                status='pending'
            )
            session.add(execution)
            session.commit()
            session.refresh(execution)
            return execution
        finally:
            session.close()
    
    def update_execution_status(self, execution_id: int, status: str,
                                result: dict = None, logs: str = None,
                                error_message: str = None):
        """更新执行状态"""
        session = self.get_session()
        try:
            execution = session.query(Execution).filter(Execution.id == execution_id).first()
            if execution:
                execution.status = status
                if result:
                    execution.result = result
                if logs:
                    execution.logs = logs
                if error_message:
                    execution.error_message = error_message
                
                if status == 'running':
                    execution.started_at = datetime.now()
                elif status in ['completed', 'failed']:
                    execution.completed_at = datetime.now()
                
                session.commit()
        finally:
            session.close()
    
    def get_execution(self, execution_id: int) -> Optional[Execution]:
        """获取执行记录"""
        session = self.get_session()
        try:
            return session.query(Execution).filter(Execution.id == execution_id).first()
        finally:
            session.close()
    
    def get_all_executions(self, config_id: int = None) -> List[Execution]:
        """获取所有执行记录"""
        session = self.get_session()
        try:
            query = session.query(Execution)
            if config_id:
                query = query.filter(Execution.config_id == config_id)
            return query.order_by(desc(Execution.created_at)).all()
        finally:
            session.close()
    
    # ==================== TrainingJob 操作 ====================
    
    def create_training_job(self, name: str, type: str, config: dict,
                           dataset_id: int = None, config_id: int = None,
                           hyperparameters: dict = None) -> TrainingJob:
        """创建训练任务"""
        session = self.get_session()
        try:
            job = TrainingJob(
                name=name,
                type=type,
                config=config,
                dataset_id=dataset_id,
                config_id=config_id,
                hyperparameters=hyperparameters
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
        finally:
            session.close()
    
    def update_training_status(self, job_id: int, status: str,
                               logs: str = None, metrics: dict = None,
                               error_message: str = None,
                               output_dir: str = None):
        """更新训练状态"""
        session = self.get_session()
        try:
            job = session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if job:
                job.status = status
                if logs:
                    job.logs = logs
                if metrics:
                    job.metrics = metrics
                if error_message:
                    job.error_message = error_message
                if output_dir:
                    job.output_dir = output_dir
                
                if status == 'running':
                    job.started_at = datetime.now()
                elif status in ['completed', 'failed', 'stopped']:
                    job.completed_at = datetime.now()
                
                session.commit()
        finally:
            session.close()
    
    def get_training_job(self, job_id: int) -> Optional[TrainingJob]:
        """获取训练任务"""
        session = self.get_session()
        try:
            return session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        finally:
            session.close()
    
    def get_all_training_jobs(self, type: str = None) -> List[TrainingJob]:
        """获取所有训练任务"""
        session = self.get_session()
        try:
            query = session.query(TrainingJob)
            if type:
                query = query.filter(TrainingJob.type == type)
            return query.order_by(desc(TrainingJob.created_at)).all()
        finally:
            session.close()
    
    def delete_training_job(self, job_id: int) -> bool:
        """删除训练任务"""
        session = self.get_session()
        try:
            job = session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if job:
                session.delete(job)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def update_training_job_status(self, job_id: int, status: str):
        """更新训练任务状态"""
        session = self.get_session()
        try:
            job = session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if job:
                job.status = status
                if status == 'running':
                    job.started_at = datetime.now()
                elif status in ['completed', 'failed', 'stopped']:
                    job.completed_at = datetime.now()
                session.commit()
        finally:
            session.close()
    
    def update_training_job(self, job_id: int, status: str = None, 
                           output_dir: str = None, model_path: str = None,
                           logs: str = None, error_message: str = None,
                           metrics: dict = None):
        """更新训练任务信息"""
        session = self.get_session()
        try:
            job = session.query(TrainingJob).filter(TrainingJob.id == job_id).first()
            if job:
                if status:
                    job.status = status
                if output_dir:
                    job.output_dir = output_dir
                if model_path:
                    job.model_path = model_path
                if logs:
                    job.logs = logs
                if error_message:
                    job.error_message = error_message
                if metrics:
                    job.metrics = metrics
                
                if status == 'running':
                    job.started_at = datetime.now()
                elif status in ['completed', 'failed', 'stopped']:
                    job.completed_at = datetime.now()
                
                session.commit()
        finally:
            session.close()
    
    def update_system_config(self, config_id: int, config_json: dict = None, 
                            name: str = None, description: str = None,
                            is_valid: bool = None):
        """更新系统配置"""
        session = self.get_session()
        try:
            config = session.query(SystemConfig).filter(SystemConfig.id == config_id).first()
            if config:
                if config_json is not None:
                    config.config_json = config_json
                if name is not None:
                    config.name = name
                if description is not None:
                    config.description = description
                if is_valid is not None:
                    config.is_valid = is_valid
                config.updated_at = datetime.now()
                session.commit()
                return True
            return False
        finally:
            session.close()
