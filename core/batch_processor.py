# core/batch_processor.py
"""
批量处理器 - 支持批量输入处理和结果导出
"""
import json
import csv
import os
from typing import List, Dict, Any, Optional, Callable, Iterator
from dataclasses import dataclass, field, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


@dataclass
class BatchItem:
    """批量处理项"""
    item_id: str
    input_data: Dict[str, Any]
    ground_truth: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """批量处理结果"""
    item_id: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    execution_log: List[Dict] = field(default_factory=list)
    error: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchJob:
    """批量任务"""
    job_id: str
    config_id: int
    total_items: int
    completed_items: int = 0
    failed_items: int = 0
    results: List[BatchResult] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'job_id': self.job_id,
            'config_id': self.config_id,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'failed_items': self.failed_items,
            'status': self.status,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'progress_percent': self.get_progress()
        }
    
    def get_progress(self) -> float:
        """获取进度百分比"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items + self.failed_items) / self.total_items * 100


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, executor: Callable, max_workers: int = 4):
        """
        初始化批量处理器
        
        Args:
            executor: 执行函数 (input_data) -> result
            max_workers: 最大并行工作线程数
        """
        self.executor = executor
        self.max_workers = max_workers
        self.jobs: Dict[str, BatchJob] = {}
        self._lock = threading.Lock()
    
    def create_job(self, items: List[BatchItem], config_id: int) -> str:
        """
        创建批量任务
        
        Args:
            items: 待处理项列表
            config_id: 配置ID
            
        Returns:
            任务ID
        """
        job_id = f"batch_{config_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        job = BatchJob(
            job_id=job_id,
            config_id=config_id,
            total_items=len(items)
        )
        
        with self._lock:
            self.jobs[job_id] = job
        
        return job_id
    
    def process_batch(self, job_id: str, 
                     progress_callback: Optional[Callable] = None) -> BatchJob:
        """
        执行批量处理
        
        Args:
            job_id: 任务ID
            progress_callback: 进度回调函数 (current, total, result)
            
        Returns:
            完成的任务
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"任务不存在: {job_id}")
        
        job.status = "running"
        
        # 这里简化处理，实际应该从存储中加载 items
        # 为演示，假设 items 已经存储在某个地方
        
        return job
    
    def process_items(self, items: List[BatchItem], 
                     config_id: int,
                     parallel: bool = True,
                     progress_callback: Optional[Callable] = None) -> BatchJob:
        """
        直接处理批量项
        
        Args:
            items: 待处理项列表
            config_id: 配置ID
            parallel: 是否并行处理
            progress_callback: 进度回调
            
        Returns:
            批量任务结果
        """
        job_id = self.create_job(items, config_id)
        job = self.jobs[job_id]
        job.status = "running"
        
        if parallel and self.max_workers > 1:
            results = self._process_parallel(items, progress_callback)
        else:
            results = self._process_sequential(items, progress_callback)
        
        job.results = results
        job.completed_items = sum(1 for r in results if r.success)
        job.failed_items = sum(1 for r in results if not r.success)
        job.status = "completed"
        job.completed_at = datetime.now().isoformat()
        
        return job
    
    def _process_sequential(self, items: List[BatchItem],
                           progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """顺序处理"""
        results = []
        
        for i, item in enumerate(items):
            result = self._process_single(item)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, len(items), result)
        
        return results
    
    def _process_parallel(self, items: List[BatchItem],
                         progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """并行处理"""
        results = [None] * len(items)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._process_single, item): i 
                for i, item in enumerate(items)
            }
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                except Exception as e:
                    item = items[idx]
                    result = BatchResult(
                        item_id=item.item_id,
                        success=False,
                        error=str(e)
                    )
                
                results[idx] = result
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, len(items), result)
        
        return results
    
    def _process_single(self, item: BatchItem) -> BatchResult:
        """处理单个项"""
        import time
        start_time = time.time()
        
        try:
            # 调用执行器
            output = self.executor(item.input_data)
            
            processing_time = time.time() - start_time
            
            return BatchResult(
                item_id=item.item_id,
                success=True,
                output=output.get('final_state', {}),
                execution_log=output.get('execution_log', []),
                processing_time=processing_time,
                metadata={
                    'total_steps': output.get('total_steps', 0),
                    'has_ground_truth': item.ground_truth is not None
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            return BatchResult(
                item_id=item.item_id,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """获取任务状态"""
        return self.jobs.get(job_id)
    
    def export_results(self, job_id: str, 
                      format: str = "json",
                      output_path: Optional[str] = None) -> str:
        """
        导出结果
        
        Args:
            job_id: 任务ID
            format: 导出格式 (json, csv)
            output_path: 输出路径，默认自动生成
            
        Returns:
            导出文件路径
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"任务不存在: {job_id}")
        
        if not output_path:
            output_path = f"batch_result_{job_id}.{format}"
        
        if format == "json":
            self._export_json(job, output_path)
        elif format == "csv":
            self._export_csv(job, output_path)
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        return output_path
    
    def _export_json(self, job: BatchJob, output_path: str):
        """导出为 JSON"""
        data = {
            'job_info': job.to_dict(),
            'results': [
                {
                    'item_id': r.item_id,
                    'success': r.success,
                    'output': r.output,
                    'error': r.error,
                    'processing_time': r.processing_time,
                    'metadata': r.metadata
                }
                for r in job.results
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _export_csv(self, job: BatchJob, output_path: str):
        """导出为 CSV"""
        if not job.results:
            return
        
        # 收集所有可能的字段
        fieldnames = ['item_id', 'success', 'error', 'processing_time']
        
        # 从输出中提取字段
        for result in job.results:
            if result.output:
                for key in result.output.keys():
                    if key not in fieldnames:
                        fieldnames.append(f"output.{key}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in job.results:
                row = {
                    'item_id': result.item_id,
                    'success': result.success,
                    'error': result.error or '',
                    'processing_time': result.processing_time
                }
                
                # 添加输出字段
                for key, value in result.output.items():
                    row[f"output.{key}"] = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                
                writer.writerow(row)


class BatchInputLoader:
    """批量输入加载器"""
    
    @staticmethod
    def from_jsonl(file_path: str) -> List[BatchItem]:
        """从 JSONL 文件加载"""
        items = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                data = json.loads(line.strip())
                items.append(BatchItem(
                    item_id=data.get('id', f'item_{i}'),
                    input_data=data.get('input', data),
                    ground_truth=data.get('ground_truth'),
                    metadata={'source_file': file_path, 'line': i}
                ))
        return items
    
    @staticmethod
    def from_csv(file_path: str, input_columns: List[str],
                 id_column: Optional[str] = None) -> List[BatchItem]:
        """从 CSV 文件加载"""
        items = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                input_data = {col: row[col] for col in input_columns if col in row}
                
                item_id = row.get(id_column, f'item_{i}') if id_column else f'item_{i}'
                
                items.append(BatchItem(
                    item_id=item_id,
                    input_data=input_data,
                    metadata={'source_file': file_path, 'row': i}
                ))
        return items
    
    @staticmethod
    def from_list(data_list: List[Dict]) -> List[BatchItem]:
        """从列表加载"""
        items = []
        for i, data in enumerate(data_list):
            items.append(BatchItem(
                item_id=data.get('id', f'item_{i}'),
                input_data=data.get('input', data),
                ground_truth=data.get('ground_truth'),
                metadata={'index': i}
            ))
        return items


# 便捷函数
def process_batch(config: List[Dict], 
                 inputs: List[Dict[str, Any]],
                 llm_callback: Optional[Callable] = None,
                 parallel: bool = True,
                 max_workers: int = 4) -> Dict[str, Any]:
    """
    便捷批量处理函数
    
    Args:
        config: 系统配置
        inputs: 输入列表
        llm_callback: LLM 回调函数
        parallel: 是否并行
        max_workers: 最大工作线程数
        
    Returns:
        处理结果统计
    """
    from runtime.advanced_executor import AdvancedExecutor
    
    # 创建执行器
    executor = AdvancedExecutor(config, llm_callback)
    
    # 创建批量处理器
    def exec_fn(input_data):
        return executor.execute(input_data)
    
    processor = BatchProcessor(exec_fn, max_workers)
    
    # 创建批量项
    items = BatchInputLoader.from_list([
        {'input': inp, 'id': f'item_{i}'} 
        for i, inp in enumerate(inputs)
    ])
    
    # 执行处理
    job = processor.process_items(items, config_id=0, parallel=parallel)
    
    return {
        'job_id': job.job_id,
        'total': job.total_items,
        'completed': job.completed_items,
        'failed': job.failed_items,
        'results': [
            {
                'item_id': r.item_id,
                'success': r.success,
                'output': r.output,
                'error': r.error
            }
            for r in job.results
        ]
    }
