# database/models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Dataset(Base):
    """测试数据集表"""
    __tablename__ = 'datasets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)  # 'test', 'train', 'validation'
    file_path = Column(String(500), nullable=False)
    file_format = Column(String(20), nullable=False)  # 'json', 'jsonl'
    record_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    generated_data = relationship("GeneratedData", back_populates="dataset")
    
    def __repr__(self):
        return f"<Dataset(id={self.id}, name='{self.name}', type='{self.type}')>"


class GeneratedData(Base):
    """生成的轨迹数据表"""
    __tablename__ = 'generated_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey('datasets.id'), nullable=True)
    config_id = Column(Integer, ForeignKey('system_configs.id'), nullable=True)
    agent_id = Column(String(100), nullable=False)
    input_data = Column(JSON, nullable=True)  # 输入数据
    output_data = Column(JSON, nullable=True)  # 输出数据
    trajectory = Column(JSON, nullable=False)  # 完整轨迹
    ground_truth = Column(JSON, nullable=True)  # 真实标签
    meta_info = Column(JSON, nullable=True)  # 额外元数据
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联关系
    dataset = relationship("Dataset", back_populates="generated_data")
    config = relationship("SystemConfig", back_populates="generated_data")
    
    def __repr__(self):
        return f"<GeneratedData(id={self.id}, agent_id='{self.agent_id}')>"


class SystemConfig(Base):
    """系统配置表 (存储JSON配置)"""
    __tablename__ = 'system_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    config_json = Column(JSON, nullable=False)  # 完整的JSON配置
    is_valid = Column(Boolean, default=False)  # 是否通过校验
    validation_errors = Column(Text, nullable=True)  # 校验错误信息
    agent_count = Column(Integer, default=0)  # Agent数量
    execution_order = Column(JSON, nullable=True)  # 执行顺序
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    executions = relationship("Execution", back_populates="config")
    generated_data = relationship("GeneratedData", back_populates="config")
    
    def __repr__(self):
        return f"<SystemConfig(id={self.id}, name='{self.name}', is_valid={self.is_valid})>"


class Execution(Base):
    """执行记录表"""
    __tablename__ = 'executions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(Integer, ForeignKey('system_configs.id'), nullable=False)
    dataset_id = Column(Integer, ForeignKey('datasets.id'), nullable=True)
    status = Column(String(50), default='pending')  # 'pending', 'running', 'completed', 'failed'
    result = Column(JSON, nullable=True)  # 执行结果
    logs = Column(Text, nullable=True)  # 执行日志
    error_message = Column(Text, nullable=True)  # 错误信息
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联关系
    config = relationship("SystemConfig", back_populates="executions")
    
    def __repr__(self):
        return f"<Execution(id={self.id}, status='{self.status}')>"


class TrainingJob(Base):
    """训练任务表"""
    __tablename__ = 'training_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'sft', 'dpo', 'grpo'
    config = Column(JSON, nullable=False)  # 训练配置
    status = Column(String(50), default='pending')  # 'pending', 'running', 'completed', 'failed', 'stopped'
    dataset_id = Column(Integer, ForeignKey('datasets.id'), nullable=True)
    config_id = Column(Integer, ForeignKey('system_configs.id'), nullable=True)
    output_dir = Column(String(500), nullable=True)  # 输出目录
    model_path = Column(String(500), nullable=True)  # 模型路径
    hyperparameters = Column(JSON, nullable=True)  # 超参数
    logs = Column(Text, nullable=True)  # 训练日志
    metrics = Column(JSON, nullable=True)  # 训练指标
    error_message = Column(Text, nullable=True)  # 错误信息
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<TrainingJob(id={self.id}, type='{self.type}', status='{self.status}')>"
