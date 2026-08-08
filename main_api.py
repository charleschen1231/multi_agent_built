"""
FastAPI Backend for Multi-Agent System Builder
Enterprise-grade API with authentication
"""
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os
import jwt
from passlib.context import CryptContext

from database.db_manager import DatabaseManager
from core.json_validator import JSONValidator
from core.trajectory_generator import TrajectoryGenerator
from spec.system_spec import SystemSpec
from training.sft_trainer import SFTTrainer
from training.dpo_trainer import DPOTrainer
from training.grpo_trainer import GRPOTrainer
from evaluation.evaluator import SystemEvaluator

import threading
import time

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(
    title="Multi-Agent System Builder API",
    description="Enterprise-grade API for Multi-Agent System Builder",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database
db = DatabaseManager()
validator = JSONValidator()

# ============== Models ==============

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ConfigCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    config_json: List[Dict[str, Any]]

class ConfigResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_valid: bool
    agent_count: int
    execution_order: Optional[List[str]]
    created_at: str

class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str = "test"
    file_path: str
    file_format: str
    record_count: int = 0

class ExecutionCreate(BaseModel):
    config_id: int
    dataset_id: Optional[int] = None
    use_teacher: bool = False
    record_trajectory: bool = True

# ============== Authentication ==============

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Simple user store (in production, use database)
USERS = {
    "admin": get_password_hash("admin123"),
    "user": get_password_hash("user123")
}

# ============== Routes ==============

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to login page"""
    with open("static/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/app", response_class=HTMLResponse)
async def app_page():
    """Main application page - token validation is done client-side"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# ============== Auth API ==============

@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    """User login"""
    if user_data.username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not verify_password(user_data.password, USERS[user_data.username]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
async def get_current_user(current_user: str = Depends(verify_token)):
    """Get current user info"""
    return {"username": current_user}

# ============== Config API ==============

@app.get("/api/configs", response_model=List[ConfigResponse])
async def get_configs(current_user: str = Depends(verify_token)):
    """Get all system configs"""
    configs = db.get_all_system_configs()
    return [
        ConfigResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            is_valid=c.is_valid,
            agent_count=c.agent_count,
            execution_order=c.execution_order,
            created_at=c.created_at.isoformat() if c.created_at else ""
        )
        for c in configs
    ]

@app.get("/api/configs/{config_id}")
async def get_config(config_id: int, current_user: str = Depends(verify_token)):
    """Get specific config"""
    config = db.get_system_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return {
        "id": config.id,
        "name": config.name,
        "description": config.description,
        "config_json": config.config_json,
        "is_valid": config.is_valid,
        "execution_order": config.execution_order,
        "agent_count": config.agent_count
    }

@app.post("/api/configs")
async def create_config(config: ConfigCreate, current_user: str = Depends(verify_token)):
    """Create new config with deduplication"""
    # Validate config
    result = validator.validate(config.config_json)
    
    # Check for duplicate config (same JSON content)
    existing_configs = db.get_all_system_configs()
    config_str = json.dumps(config.config_json, sort_keys=True)
    
    for existing in existing_configs:
        existing_str = json.dumps(existing.config_json, sort_keys=True)
        if existing_str == config_str:
            # Return existing config
            return {
                "id": existing.id,
                "name": existing.name,
                "is_valid": existing.is_valid,
                "errors": None,
                "execution_order": existing.execution_order,
                "message": "Configuration already exists",
                "existing": True
            }
    
    # Save to database
    db_config = db.create_system_config(
        name=config.name,
        description=config.description,
        config_json=config.config_json
    )
    
    # Update validation status
    db.update_config_validation(
        config_id=db_config.id,
        is_valid=result.is_valid,
        errors="\n".join(result.errors) if result.errors else None,
        execution_order=result.execution_order
    )
    
    return {
        "id": db_config.id,
        "name": db_config.name,
        "is_valid": result.is_valid,
        "errors": result.errors,
        "execution_order": result.execution_order,
        "existing": False
    }

@app.post("/api/configs/validate")
async def validate_config(config_data: Dict[str, Any], current_user: str = Depends(verify_token)):
    """Validate config without saving"""
    result = validator.validate(config_data.get("config_json", []))
    graph = validator.get_dataflow_graph(config_data.get("config_json", []))
    
    return {
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "execution_order": result.execution_order,
        "graph": graph
    }

@app.delete("/api/configs/{config_id}")
async def delete_config(config_id: int, current_user: str = Depends(verify_token)):
    """Delete config"""
    success = db.delete_system_config(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"message": "Config deleted successfully"}

@app.post("/api/configs/{config_id}/optimize-prompts")
async def optimize_prompts(config_id: int, current_user: str = Depends(verify_token)):
    """Optimize prompts using GPT-4o"""
    try:
        from core.prompt_optimizer import PromptOptimizer, compare_prompts
        
        config = db.get_system_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        optimizer = PromptOptimizer()
        results = optimizer.optimize_system_prompts(config.config_json)
        optimized_config = optimizer.apply_optimization(config.config_json, results)
        
        # 生成对比报告
        comparisons = []
        for orig, opt in zip(config.config_json, optimized_config):
            comparisons.append(compare_prompts(orig, opt))
        
        return {
            "success": True,
            "optimized_config": optimized_config,
            "comparisons": comparisons,
            "summary": {
                "total_agents": len(results),
                "optimized_count": sum(1 for r in results if r.improvements)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.post("/api/configs/{config_id}/execute")
async def execute_config(config_id: int, request: Dict[str, Any], current_user: str = Depends(verify_token)):
    """Execute config with advanced executor (supports branch/loop)"""
    try:
        from runtime.advanced_executor import AdvancedExecutor
        from llm.model_factory import ModelFactory
        import os
        
        config = db.get_system_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        user_input = request.get("input", {})
        max_steps = request.get("max_steps", 100)
        
        # 创建 LLM 回调函数，根据 Agent 配置使用不同的模型
        def llm_callback(prompt: str, system_prompt: str = "", agent_config: dict = None) -> str:
            try:
                # 从 Agent 配置中获取模型名称
                model_name = None
                if agent_config and 'model' in agent_config:
                    model_name = agent_config['model'].get('name_or_path', 'gpt-4o')
                
                # 如果没有指定模型，使用默认模型
                if not model_name:
                    model_name = 'gpt-4o'
                
                # 检查模型路径是否存在（如果是本地路径）
                if ('/' in model_name or '\\' in model_name or model_name.startswith('.')):
                    # 这是一个本地路径，检查是否存在
                    if not os.path.exists(model_name):
                        print(f"警告: 模型路径不存在: {model_name}，回退到使用基础模型 Qwen/Qwen2.5-0.5B-Instruct")
                        model_name = 'Qwen/Qwen2.5-0.5B-Instruct'
                    else:
                        # 检查目录下是否有模型文件
                        has_model_file = any(
                            f.endswith('.bin') or f.endswith('.safetensors') or f == 'config.json'
                            for f in os.listdir(model_name)
                        )
                        if not has_model_file:
                            print(f"警告: 模型目录 {model_name} 中没有模型文件，回退到使用基础模型 Qwen/Qwen2.5-0.5B-Instruct")
                            model_name = 'Qwen/Qwen2.5-0.5B-Instruct'
                
                # 创建 LLM 实例
                llm = ModelFactory.create_llm(model_name)
                
                # 合并 system_prompt 和 prompt
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                
                # 调用模型生成响应
                response = llm.generate(full_prompt, temperature=0.7)
                return response
            except Exception as e:
                print(f"LLM 调用错误: {e}")
                return f"[错误] 模型调用失败: {str(e)}"
        
        executor = AdvancedExecutor(config.config_json, llm_callback)
        result = executor.execute(user_input, max_steps)
        
        return {
            "success": True,
            "final_state": result["final_state"],
            "execution_log": result["execution_log"],
            "total_steps": result["total_steps"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")

@app.post("/api/configs/{config_id}/execute-batch")
async def execute_batch(config_id: int, request: Dict[str, Any], current_user: str = Depends(verify_token)):
    """Execute batch processing"""
    try:
        from core.batch_processor import process_batch
        
        config = db.get_system_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        inputs = request.get("inputs", [])
        parallel = request.get("parallel", True)
        max_workers = request.get("max_workers", 4)
        
        if not inputs:
            raise HTTPException(status_code=400, detail="No inputs provided")
        
        result = process_batch(
            config.config_json,
            inputs,
            parallel=parallel,
            max_workers=max_workers
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch execution failed: {str(e)}")

# ============== Dataset API ==============

@app.get("/api/datasets")
async def get_datasets(current_user: str = Depends(verify_token)):
    """Get all datasets"""
    datasets = db.get_all_datasets()
    return [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "type": d.type,
            "file_format": d.file_format,
            "record_count": d.record_count,
            "created_at": d.created_at.isoformat() if d.created_at else ""
        }
        for d in datasets
    ]

@app.get("/api/datasets/{dataset_id}")
async def get_dataset(dataset_id: int, current_user: str = Depends(verify_token)):
    """Get specific dataset"""
    dataset = db.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Load preview data
    preview = []
    try:
        with open(dataset.file_path, 'r', encoding='utf-8') as f:
            if dataset.file_format == 'jsonl':
                for i, line in enumerate(f):
                    if i >= 5:  # Preview first 5 records
                        break
                    preview.append(json.loads(line))
            else:
                data = json.load(f)
                preview = data[:5] if isinstance(data, list) else [data]
    except Exception as e:
        preview = [{"error": str(e)}]
    
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "type": dataset.type,
        "file_format": dataset.file_format,
        "record_count": dataset.record_count,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else "",
        "preview": preview
    }

@app.post("/api/datasets")
async def create_dataset(dataset: DatasetCreate, current_user: str = Depends(verify_token)):
    """Create new dataset record"""
    db_dataset = db.create_dataset(
        name=dataset.name,
        description=dataset.description,
        type=dataset.type,
        file_path=dataset.file_path,
        file_format=dataset.file_format,
        record_count=dataset.record_count
    )
    return {
        "id": db_dataset.id,
        "name": db_dataset.name,
        "message": "Dataset created successfully"
    }

# ============== Execution API ==============

@app.post("/api/executions")
async def create_execution(exec_data: ExecutionCreate, current_user: str = Depends(verify_token)):
    """Create and run execution"""
    config = db.get_system_config(exec_data.config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    # Create execution record
    execution = db.create_execution(
        config_id=exec_data.config_id,
        dataset_id=exec_data.dataset_id
    )
    
    # Update status
    db.update_execution_status(execution.id, 'running')
    
    try:
        # Load dataset if provided
        inputs = []
        if exec_data.dataset_id:
            dataset = db.get_dataset(exec_data.dataset_id)
            if dataset and os.path.exists(dataset.file_path):
                with open(dataset.file_path, 'r', encoding='utf-8') as f:
                    if dataset.file_format == 'jsonl':
                        inputs = [json.loads(line) for line in f.readlines()]
                    else:
                        inputs = json.load(f)
        
        if not inputs:
            inputs = [{"user_request": "帮我制定一个学习计划，准备下周的数学考试"}]
        
        # Generate trajectories
        spec = SystemSpec(agents=config.config_json)
        generator = TrajectoryGenerator(spec, config_id=config.id)
        trajectories = generator.generate_batch(inputs, use_teacher=exec_data.use_teacher)
        
        # Save trajectories
        for traj in trajectories:
            for step in traj.steps:
                db.create_generated_data(
                    agent_id=step.agent_id,
                    trajectory=step.to_dict(),
                    config_id=config.id,
                    dataset_id=exec_data.dataset_id,
                    input_data=step.input_data,
                    output_data=step.output_data,
                    ground_truth={'response': step.ground_truth} if step.ground_truth else None
                )
        
        # Update execution status
        db.update_execution_status(
            execution_id=execution.id,
            status='completed',
            result={
                'sample_count': len(trajectories),
                'trajectory_ids': [t.trajectory_id for t in trajectories]
            }
        )
        
        return {
            "execution_id": execution.id,
            "status": "completed",
            "trajectory_count": len(trajectories),
            "trajectories": [t.to_dict() for t in trajectories]
        }
        
    except Exception as e:
        db.update_execution_status(
            execution_id=execution.id,
            status='failed',
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/executions")
async def get_executions(current_user: str = Depends(verify_token)):
    """Get all executions"""
    executions = db.get_all_executions()
    return [
        {
            "id": e.id,
            "config_id": e.config_id,
            "dataset_id": e.dataset_id,
            "status": e.status,
            "created_at": e.created_at.isoformat() if e.created_at else "",
            "result": e.result
        }
        for e in executions
    ]

# ============== Trajectory API ==============

@app.get("/api/trajectories")
async def get_trajectories(
    config_id: Optional[int] = None,
    dataset_id: Optional[int] = None,
    current_user: str = Depends(verify_token)
):
    """Get trajectories with optional filtering"""
    if config_id:
        data = db.get_generated_data_by_config(config_id)
    elif dataset_id:
        data = db.get_generated_data_by_dataset(dataset_id)
    else:
        data = []
        for config in db.get_all_system_configs():
            data.extend(db.get_generated_data_by_config(config.id))
    
    return [
        {
            "id": d.id,
            "trajectory_id": d.trajectory.get("trajectory_id", "") if isinstance(d.trajectory, dict) else "",
            "agent_id": d.agent_id,
            "config_id": d.config_id,
            "dataset_id": d.dataset_id,
            "input_data": d.input_data,
            "output_data": d.output_data,
            "created_at": d.created_at.isoformat() if d.created_at else ""
        }
        for d in data
    ]

# ============== Training API ==============

# Training job manager
class TrainingJobManager:
    def __init__(self):
        self.active_jobs = {}
        self.sft_trainer = SFTTrainer(output_dir="./training_outputs/sft")
        self.dpo_trainer = DPOTrainer(output_dir="./training_outputs/dpo")
        self.grpo_trainer = GRPOTrainer(output_dir="./training_outputs/grpo")
        # Keep legacy reference for backward compatibility
        self.trainer = self.sft_trainer
    
    def prepare_training_data(self, job_id: int, config_id: int, dataset_id: int, data_source: str = "trajectory"):
        """Prepare training data from trajectories or dataset"""
        try:
            # Get config
            config = db.get_system_config(config_id)
            if not config:
                raise ValueError(f"Config {config_id} not found")
            
            # Get dataset
            dataset = db.get_dataset(dataset_id)
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")
            
            if data_source == "trajectory":
                # Get trajectories for this config
                trajectories_data = db.get_generated_data_by_config(config_id)
                
                # Convert to SFT format
                trajectories = []
                for data in trajectories_data:
                    traj = {
                        'trajectory_id': f"traj_{data.id}",
                        'sample_id': data.dataset_id,
                        'steps': [{
                            'agent_id': data.agent_id,
                            'prompt': json.dumps(data.input_data) if data.input_data else '',
                            'output': json.dumps(data.output_data) if data.output_data else '',
                            'ground_truth': json.dumps(data.ground_truth) if data.ground_truth else None,
                            'metadata': {
                                'system_prompt': config.config_json[0].get('instruction_prompt', {}).get('instruction', '') if config.config_json else ''
                            }
                        }]
                    }
                    trajectories.append(traj)
                
                # Prepare SFT data
                data_file = self.trainer.prepare_training_data(trajectories)
            else:
                # Use dataset file directly
                data_file = dataset.file_path
            
            return data_file
            
        except Exception as e:
            raise Exception(f"Failed to prepare training data: {str(e)}")
    
    def _detect_training_mode(self, config_json: List[Dict], training_type: str = 'auto') -> str:
        """
        检测训练模式。
        
        Args:
            config_json: 系统配置
            training_type: 用户指定的训练类型 ('auto', 'sft', 'dpo', 'grpo')
        
        Returns:
            str: 检测到的训练模式 ('sft', 'dpo', 'grpo', 'mixed')
        """
        if training_type in ('sft', 'dpo', 'grpo'):
            return training_type
        
        # Auto-detect from config
        mode_counts = {'sft': 0, 'dpo': 0, 'grpo': 0}
        for agent in config_json:
            training = agent.get('training', {})
            if training.get('trainable'):
                mode = training.get('mode', 'sft')
                if mode in mode_counts:
                    mode_counts[mode] += 1
        
        # Return the dominant mode
        if mode_counts['grpo'] > 0 and mode_counts['sft'] == 0 and mode_counts['dpo'] == 0:
            return 'grpo'
        elif mode_counts['dpo'] > 0 and mode_counts['sft'] == 0 and mode_counts['grpo'] == 0:
            return 'dpo'
        elif mode_counts['sft'] > 0 and mode_counts['dpo'] == 0 and mode_counts['grpo'] == 0:
            return 'sft'
        elif sum(1 for v in mode_counts.values() if v > 0) > 1:
            return 'mixed'
        
        return 'sft'  # default
    
    def run_training(self, job_id: int, config_id: int, dataset_id: int, 
                     hyperparameters: Dict, data_source: str = "trajectory",
                     training_mode: str = "auto",
                     training_type: str = "auto"):
        """
        Run training in background thread.
        
        Args:
            training_mode: 'auto' (自动检测), 'system' (多 Agent 训练), 'single' (单模型训练)
            training_type: 'auto', 'sft', 'dpo', 'grpo'
        """
        import time
        
        try:
            # Update job status
            db.update_training_job_status(job_id, 'running')
            
            # Get config
            config = db.get_system_config(config_id)
            config_json = config.config_json if config else []
            
            # Get dataset
            dataset = db.get_dataset(dataset_id)
            
            # 日志缓冲
            logs_buffer = []
            
            def log_callback(message: str):
                logs_buffer.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
                if len(logs_buffer) % 10 == 0:
                    db.update_training_job(
                        job_id=job_id,
                        logs="\n".join(logs_buffer[-200:])
                    )
            
            def flush_logs():
                """强制刷新日志到数据库"""
                if logs_buffer:
                    db.update_training_job(
                        job_id=job_id,
                        logs="\n".join(logs_buffer[-200:])
                    )
            
            # Detect training type
            detected_type = self._detect_training_mode(config_json, training_type)
            
            if log_callback:
                log_callback(f"检测到的训练类型: {detected_type}")
                log_callback(f"训练模式: {training_mode}")
            
            # Count trainable agents per mode
            trainable_agents = {
                'sft': [a for a in config_json if a.get('training', {}).get('trainable') and a.get('training', {}).get('mode') == 'sft'],
                'dpo': [a for a in config_json if a.get('training', {}).get('trainable') and a.get('training', {}).get('mode') == 'dpo'],
                'grpo': [a for a in config_json if a.get('training', {}).get('trainable') and a.get('training', {}).get('mode') == 'grpo'],
            }
            
            use_system_mode = False
            if training_mode == 'system':
                use_system_mode = True
            elif training_mode == 'auto':
                total_trainable = sum(len(v) for v in trainable_agents.values())
                use_system_mode = total_trainable >= 1
            
            dataset_file = dataset.file_path if dataset else None
            
            # ============ DPO System-Level Training ============
            if detected_type == 'dpo' and use_system_mode and dataset_file:
                log_callback("=" * 50)
                log_callback("System-Level Multi-Agent DPO 模式")
                log_callback(f"可训练 DPO Agent 数: {len(trainable_agents['dpo'])}")
                
                metrics_history = []
                def metrics_callback(step, loss, lr):
                    metrics_history.append({
                        'step': step, 'loss': loss, 'lr': lr,
                        'timestamp': time.time()
                    })
                
                # Find trajectory file if available
                trajectory_file = self._find_trajectory_file(config_id, dataset_id)
                
                result = self.dpo_trainer.train_system_level(
                    config_json=config_json,
                    dataset_file=dataset_file,
                    trajectory_file=trajectory_file,
                    default_hyperparameters=hyperparameters,
                    log_callback=log_callback,
                    metrics_callback=metrics_callback
                )
                
                flush_logs()
                
                db.update_training_job(
                    job_id=job_id,
                    status='completed' if result['status'] == 'completed' else 'failed',
                    output_dir=result.get('agents', [{}])[0].get('output_dir') if result.get('agents') else None,
                    model_path='system_level_dpo',
                    metrics=result,
                    logs="\n".join(logs_buffer[-200:])
                )
            
            # ============ GRPO System-Level Training ============
            elif detected_type == 'grpo' and use_system_mode and dataset_file:
                log_callback("=" * 50)
                log_callback("System-Level Multi-Agent GRPO 模式")
                log_callback(f"可训练 GRPO Agent 数: {len(trainable_agents['grpo'])}")
                
                metrics_history = []
                def metrics_callback(step, loss, lr):
                    metrics_history.append({
                        'step': step, 'loss': loss, 'lr': lr,
                        'timestamp': time.time()
                    })
                
                trajectory_file = self._find_trajectory_file(config_id, dataset_id)
                
                result = self.grpo_trainer.train_system_level(
                    config_json=config_json,
                    dataset_file=dataset_file,
                    trajectory_file=trajectory_file,
                    default_hyperparameters=hyperparameters,
                    log_callback=log_callback,
                    metrics_callback=metrics_callback
                )
                
                flush_logs()
                
                db.update_training_job(
                    job_id=job_id,
                    status='completed' if result['status'] == 'completed' else 'failed',
                    output_dir=result.get('agents', [{}])[0].get('output_dir') if result.get('agents') else None,
                    model_path='system_level_grpo',
                    metrics=result,
                    logs="\n".join(logs_buffer[-200:])
                )
            
            # ============ Mixed Mode Training ============
            elif detected_type == 'mixed' and use_system_mode and dataset_file:
                log_callback("=" * 50)
                log_callback("Mixed Mode: 多种训练类型")
                
                mixed_result = {'agents': [], 'status': 'completed'}
                
                # Run SFT agents
                if trainable_agents['sft']:
                    log_callback(f"\n--- SFT Phase: {len(trainable_agents['sft'])} agents ---")
                    sft_result = self.sft_trainer.train_system_level(
                        config_json=config_json,
                        dataset_file=dataset_file,
                        default_hyperparameters=hyperparameters,
                        log_callback=log_callback
                    )
                    mixed_result['agents'].extend(sft_result.get('agents', []))
                    if sft_result['status'] != 'completed':
                        mixed_result['status'] = 'partial'
                
                # Run DPO agents
                if trainable_agents['dpo']:
                    log_callback(f"\n--- DPO Phase: {len(trainable_agents['dpo'])} agents ---")
                    trajectory_file = self._find_trajectory_file(config_id, dataset_id)
                    dpo_result = self.dpo_trainer.train_system_level(
                        config_json=config_json,
                        dataset_file=dataset_file,
                        trajectory_file=trajectory_file,
                        default_hyperparameters=hyperparameters,
                        log_callback=log_callback
                    )
                    mixed_result['agents'].extend(dpo_result.get('agents', []))
                    if dpo_result['status'] != 'completed':
                        mixed_result['status'] = 'partial'
                
                # Run GRPO agents
                if trainable_agents['grpo']:
                    log_callback(f"\n--- GRPO Phase: {len(trainable_agents['grpo'])} agents ---")
                    trajectory_file = self._find_trajectory_file(config_id, dataset_id)
                    grpo_result = self.grpo_trainer.train_system_level(
                        config_json=config_json,
                        dataset_file=dataset_file,
                        trajectory_file=trajectory_file,
                        default_hyperparameters=hyperparameters,
                        log_callback=log_callback
                    )
                    mixed_result['agents'].extend(grpo_result.get('agents', []))
                    if grpo_result['status'] != 'completed':
                        mixed_result['status'] = 'partial'
                
                mixed_result['mode'] = 'mixed'
                mixed_result['overall_message'] = f"Mixed training: {len(mixed_result['agents'])} agents processed"
                
                flush_logs()
                
                db.update_training_job(
                    job_id=job_id,
                    status='completed' if mixed_result['status'] == 'completed' else 'failed',
                    model_path='system_level_mixed',
                    metrics=mixed_result,
                    logs="\n".join(logs_buffer[-200:])
                )
            
            # ============ SFT System-Level (original) ============
            elif use_system_mode and data_source == 'dataset' and dataset_file:
                log_callback("检测到 System-Level 多 Agent SFT 模式")
                log_callback(f"可训练 Agent 数: {len(trainable_agents['sft'])}")
                
                metrics_history = []
                
                def metrics_callback(step: int, loss: float, learning_rate: float):
                    metrics_history.append({
                        'step': step, 'loss': loss, 'lr': learning_rate,
                        'timestamp': time.time()
                    })
                
                result = self.sft_trainer.train_system_level(
                    config_json=config_json,
                    dataset_file=dataset_file,
                    default_hyperparameters=hyperparameters,
                    log_callback=log_callback,
                    metrics_callback=metrics_callback
                )
                
                flush_logs()
                
                db.update_training_job(
                    job_id=job_id,
                    status='completed' if result['status'] == 'completed' else 'failed',
                    output_dir=result.get('agents', [{}])[0].get('output_dir') if result.get('agents') else None,
                    model_path='system_level',
                    metrics=result,
                    logs="\n".join(logs_buffer[-200:])
                )
            
            else:
                # ============ 单模型训练（向后兼容） ============
                data_file = self.prepare_training_data(job_id, config_id, dataset_id, data_source)
                
                # Find first trainable agent's model
                model_path = None
                for agent in config_json:
                    training = agent.get('training', {})
                    if training.get('trainable'):
                        model_path = agent.get('model', {}).get('name_or_path')
                        break
                if not model_path:
                    model_path = "Qwen/Qwen2.5-0.5B-Instruct"
                
                metrics_history = []
                
                def metrics_callback(step: int, loss: float, learning_rate: float):
                    metrics_history.append({
                        'step': step, 'loss': loss,
                        'learning_rate': learning_rate, 'timestamp': time.time()
                    })
                    progress = min(100, int(step / hyperparameters.get('max_steps', 500) * 100))
                    db.update_training_job(
                        job_id=job_id,
                        metrics={'progress': progress, 'current_loss': loss, 'learning_rate': learning_rate}
                    )
                
                log_callback(f"Starting SFT training with model: {model_path}")
                log_callback(f"Training data: {data_file}")
                log_callback(f"Hyperparameters: {hyperparameters}")
                
                result = self.sft_trainer.train_with_api(
                    data_file=data_file,
                    model_path=model_path,
                    hyperparameters=hyperparameters,
                    log_callback=log_callback,
                    metrics_callback=metrics_callback
                )
                
                flush_logs()
                
                if result.get('status') == 'completed':
                    db.update_training_job(
                        job_id=job_id,
                        status='completed',
                        output_dir=result.get('output_dir'),
                        model_path=result.get('output_dir'),
                        logs="\n".join(logs_buffer[-200:])
                    )
                else:
                    error_msg = result.get('message', 'Unknown error')
                    db.update_training_job(
                        job_id=job_id,
                        status='failed',
                        error_message=error_msg,
                        logs="\n".join(logs_buffer[-200:])
                    )
            
        except Exception as e:
            error_msg = str(e)
            print(f"Training error: {error_msg}")
            db.update_training_job(
                job_id=job_id,
                status='failed',
                error_message=error_msg,
                logs=f"Training failed with error: {error_msg}"
            )
        finally:
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    def _find_trajectory_file(self, config_id: int, dataset_id: int) -> Optional[str]:
        """查找与 config_id 和 dataset_id 关联的轨迹文件"""
        try:
            rollout_dir = 'data/rollouts'
            if os.path.exists(rollout_dir):
                # Find most recent trajectory file
                files = sorted(
                    [f for f in os.listdir(rollout_dir) if f.endswith('.jsonl')],
                    reverse=True
                )
                if files:
                    return os.path.join(rollout_dir, files[0])
        except Exception:
            pass
        return None

training_manager = TrainingJobManager()

@app.get("/api/training/jobs")
async def get_training_jobs(current_user: str = Depends(verify_token)):
    """Get all training jobs"""
    jobs = db.get_all_training_jobs()
    return [
        {
            "id": j.id,
            "name": j.name,
            "type": j.type,
            "status": j.status,
            "config_id": j.config_id,
            "dataset_id": j.dataset_id,
            "output_dir": j.output_dir,
            "model_path": j.model_path,
            "progress": j.metrics.get('progress', 0) if j.metrics else 0,
            "created_at": j.created_at.isoformat() if j.created_at else "",
            "completed_at": j.completed_at.isoformat() if j.completed_at else "",
            "updated_at": j.updated_at.isoformat() if j.updated_at else "",
            "metrics": j.metrics,
            "config": {"name": db.get_system_config(j.config_id).name} if j.config_id and db.get_system_config(j.config_id) else None
        }
        for j in jobs
    ]

@app.get("/api/training/jobs/{job_id}")
async def get_training_job(job_id: int, current_user: str = Depends(verify_token)):
    """Get training job details"""
    job = db.get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    return {
        "id": job.id,
        "name": job.name,
        "type": job.type,
        "status": job.status,
        "description": job.config.get('description', '') if job.config else '',
        "config_id": job.config_id,
        "dataset_id": job.dataset_id,
        "hyperparameters": job.hyperparameters,
        "output_dir": job.output_dir,
        "model_path": job.model_path,
        "logs": job.logs,
        "metrics": job.metrics,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "started_at": job.started_at.isoformat() if job.started_at else "",
        "completed_at": job.completed_at.isoformat() if job.completed_at else ""
    }

@app.post("/api/training/jobs")
async def create_training_job(
    job_data: Dict[str, Any],
    current_user: str = Depends(verify_token)
):
    """Create new training job and start training"""
    # Create job in database
    job = db.create_training_job(
        name=job_data.get("name", "Untitled"),
        type=job_data.get("type", job_data.get("training_type", "sft")),
        config={
            "description": job_data.get("description", ""),
            "data_source": job_data.get("data_source", "trajectory"),
            "training_mode": job_data.get("training_mode", "auto"),
            "training_type": job_data.get("training_type", "auto")
        },
        dataset_id=job_data.get("dataset_id"),
        config_id=job_data.get("config_id"),
        hyperparameters=job_data.get("hyperparameters", {})
    )
    
    # Start training in background thread
    def run_training_thread():
        training_manager.run_training(
            job_id=job.id,
            config_id=job_data.get("config_id"),
            dataset_id=job_data.get("dataset_id"),
            hyperparameters=job_data.get("hyperparameters", {}),
            data_source=job_data.get("data_source", "trajectory"),
            training_mode=job_data.get("training_mode", "auto"),
            training_type=job_data.get("training_type", "auto")
        )
    
    thread = threading.Thread(target=run_training_thread)
    thread.daemon = True
    thread.start()
    
    training_manager.active_jobs[job.id] = thread
    
    return {
        "id": job.id,
        "name": job.name,
        "type": job.type,
        "status": "running",
        "message": "Training job started"
    }

@app.post("/api/training/jobs/{job_id}/stop")
async def stop_training_job(job_id: int, current_user: str = Depends(verify_token)):
    """Stop a running training job"""
    job = db.get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    if job.status != 'running':
        raise HTTPException(status_code=400, detail="Job is not running")
    
    # Update status
    db.update_training_job_status(job_id, 'stopped')
    
    # Remove from active jobs
    if job_id in training_manager.active_jobs:
        del training_manager.active_jobs[job_id]
    
    return {"message": "Training job stopped"}

@app.delete("/api/training/jobs/{job_id}")
async def delete_training_job(job_id: int, current_user: str = Depends(verify_token)):
    """Delete a training job"""
    job = db.get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    # If job is running, stop it first
    if job.status == 'running':
        db.update_training_job_status(job_id, 'stopped')
        if job_id in training_manager.active_jobs:
            del training_manager.active_jobs[job_id]
    
    # Delete from database
    db.delete_training_job(job_id)
    
    return {"message": "Training job deleted successfully"}

@app.post("/api/training/jobs/{job_id}/validate")
async def validate_training_job(
    job_id: int,
    request: Dict[str, Any] = None,
    current_user: str = Depends(verify_token)
):
    """
    Validate a completed training job by comparing student outputs vs teacher ground truth.
    
    Phase 3 of the distillation pipeline:
    - Run student pipeline on same dataset
    - Compare per-agent outputs against teacher trajectories
    - Compute metrics: exact match, F1, ROUGE-L, trajectory consistency
    """
    job = db.get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    if job.status != 'completed':
        raise HTTPException(status_code=400, detail="Training job must be completed before validation")
    
    try:
        config = db.get_system_config(job.config_id)
        if not config:
            raise HTTPException(status_code=404, detail="System config not found")
        
        dataset = db.get_dataset(job.dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        evaluator = SystemEvaluator()
        
        # Find trajectory files
        trajectory_file = training_manager._find_trajectory_file(job.config_id, job.dataset_id)
        
        request_data = request or {}
        student_file = request_data.get('student_trajectory_file', trajectory_file)
        teacher_file = request_data.get('teacher_trajectory_file')
        
        # If no trajectory file, try to find SFT training output files
        if not student_file:
            search_dirs = []
            # 1. Check job.output_dir (ms-swift training output)
            if job.output_dir and os.path.exists(job.output_dir):
                search_dirs.append(job.output_dir)
            # 2. Check system_sft directory where prepare_all_agents_sft_data saves files
            system_sft_base = os.path.join('training_outputs', 'sft', 'system_sft')
            if os.path.exists(system_sft_base):
                # Find the most recent run directory
                run_dirs = sorted(
                    [d for d in os.listdir(system_sft_base) if d.startswith('run_')],
                    reverse=True
                )
                if run_dirs:
                    search_dirs.append(os.path.join(system_sft_base, run_dirs[0]))
                # Also search all run subdirectories
                for run_dir in run_dirs:
                    search_dirs.append(os.path.join(system_sft_base, run_dir))
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    sft_files = sorted(
                        [f for f in os.listdir(search_dir) if f.endswith('_sft.jsonl')],
                        reverse=True
                    )
                    if sft_files:
                        student_file = os.path.join(search_dir, sft_files[0])
                        break
        
        if not student_file:
            raise HTTPException(
                status_code=400, 
                detail="No student trajectory file found. Please provide student_trajectory_file."
            )
        
        if teacher_file:
            # Evaluate from files
            report = evaluator.evaluate_from_trajectory_files(
                student_trajectory_file=student_file,
                teacher_trajectory_file=teacher_file,
                config_json=config.config_json
            )
        else:
            # Try to build evaluation from dataset + student outputs
            # Load dataset as teacher GT
            teacher_data = []
            with open(dataset.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        sample = json.loads(line)
                        # Convert dataset sample to trajectory format
                        for agent in config.config_json:
                            training = agent.get('training', {})
                            gt_config = training.get('ground_truth', {})
                            gt_key = gt_config.get('gt_key')
                            if gt_key and gt_key in sample:
                                teacher_data.append({
                                    'agent_id': agent.get('agent_id'),
                                    'messages': [{'role': 'assistant', 'content': str(sample[gt_key])}],
                                    'ground_truth': str(sample[gt_key]),
                                    'meta': {'sample_id': len(teacher_data)}
                                })
            
            # Load student trajectories
            student_data = []
            if student_file and os.path.exists(student_file):
                with open(student_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            student_data.append(json.loads(line))
            
            if not student_data:
                raise HTTPException(status_code=400, detail="No student trajectory data found")
            
            report = evaluator.evaluate_system(
                student_trajectories=student_data,
                teacher_trajectories=teacher_data,
                config_json=config.config_json
            )
        
        # Save report
        report_file = evaluator.save_report(report, f"validation_job_{job_id}.json")
        report['report_file'] = report_file
        
        # Store validation result in job metrics
        existing_metrics = job.metrics or {}
        existing_metrics['validation'] = report
        db.update_training_job(
            job_id=job_id,
            metrics=existing_metrics
        )
        
        return {
            "job_id": job_id,
            "validation_report": report,
            "report_file": report_file
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.post("/api/training/jobs/{job_id}/prepare-data")
async def prepare_training_data_endpoint(
    job_id: int,
    current_user: str = Depends(verify_token)
):
    """Prepare training data for a job"""
    job = db.get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    try:
        data_file = training_manager.prepare_training_data(
            job_id=job_id,
            config_id=job.config_id,
            dataset_id=job.dataset_id,
            data_source=job.config.get('data_source', 'trajectory') if job.config else 'trajectory'
        )
        return {"data_file": data_file, "message": "Training data prepared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/training/jobs/{job_id}/deploy")
async def deploy_trained_model(
    job_id: int,
    deploy_data: Dict[str, Any],
    current_user: str = Depends(verify_token)
):
    """Deploy trained model to system config.
    
    For System-Level training, each agent has its own output_dir stored in
    job.metrics['agents'][i]['output_dir']. This endpoint maps each agent
    to its correct trained model path.
    """
    job = db.get_training_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    if job.status != 'completed':
        raise HTTPException(status_code=400, detail="Training job is not completed")
    
    # Build agent_id -> output_dir mapping from System-Level metrics
    agent_output_map = {}
    metrics = job.metrics or {}
    agents_metrics = metrics.get('agents', [])
    if agents_metrics:
        for am in agents_metrics:
            aid = am.get('agent_id')
            out_dir = am.get('output_dir')
            if aid and out_dir:
                agent_output_map[aid] = out_dir
    
    # Fallback: if no per-agent mapping, use job.output_dir
    if not agent_output_map and not job.output_dir:
        raise HTTPException(status_code=400, detail="No output directory found")
    
    # Get config
    config = db.get_system_config(job.config_id)
    if not config:
        raise HTTPException(status_code=404, detail="System config not found")
    
    # Update config with new model path
    config_json = config.config_json
    target_agent = deploy_data.get('agent_id')
    
    updated_agents = []
    for agent in config_json:
        if target_agent and agent['agent_id'] != target_agent:
            continue
        
        training = agent.get('training', {})
        if training.get('trainable') and training.get('mode') in ('sft', 'dpo', 'grpo'):
            agent_id = agent['agent_id']
            
            # Use per-agent output_dir if available, otherwise fallback to job.output_dir
            model_path = agent_output_map.get(agent_id, job.output_dir)
            
            if not model_path:
                continue
            
            # Verify the output directory exists
            if not os.path.exists(model_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"Agent '{agent_id}' output directory not found: {model_path}"
                )
            
            if 'model' not in agent:
                agent['model'] = {}
            agent['model']['name_or_path'] = model_path
            updated_agents.append(agent_id)
            
            if target_agent:
                break
    
    if not updated_agents:
        raise HTTPException(status_code=400, detail="No trainable agent found in config or no valid output directories")
    
    # Save updated config (create new version or overwrite)
    new_name = config.name + "_deployed" if deploy_data.get('create_new_version') else config.name
    db.update_system_config(
        config_id=job.config_id,
        config_json=config_json,
        name=new_name
    )
    
    # Update training job to mark as deployed
    db.update_training_job(
        job_id=job_id,
        model_path=job.output_dir
    )
    
    return {
        "message": f"Model deployed successfully for {len(updated_agents)} agent(s)",
        "config_id": job.config_id,
        "updated_agents": updated_agents,
        "agent_model_paths": {aid: agent_output_map.get(aid, job.output_dir) for aid in updated_agents}
    }

# ============== Stats API ==============

@app.get("/api/stats")
async def get_stats(current_user: str = Depends(verify_token)):
    """Get dashboard statistics"""
    datasets = db.get_all_datasets()
    configs = db.get_all_system_configs()
    executions = db.get_all_executions()
    jobs = db.get_all_training_jobs()
    
    trajectory_count = sum(
        len(db.get_generated_data_by_config(c.id))
        for c in configs
    )
    
    return {
        "dataset_count": len(datasets),
        "config_count": len(configs),
        "valid_config_count": len([c for c in configs if c.is_valid]),
        "execution_count": len(executions),
        "training_count": len(jobs),
        "trajectory_count": trajectory_count,
        "running_trainings": len([j for j in jobs if j.status == 'running'])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
