# web/pages/training.py
import json
import gradio as gr
from training.sft_trainer import SFTTrainer
from training.dpo_trainer import DPOTrainer
from training.grpo_trainer import GRPOTrainer


def create_training_page(app_state):
    """创建训练管理页面"""
    
    db = app_state.db_manager
    
    gr.Markdown("## 🎯 训练管理")
    
    with gr.Tabs():
        # SFT 训练 Tab
        with gr.TabItem("📚 SFT 训练"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 训练配置")
                    
                    sft_name = gr.Textbox(
                        label="训练任务名称",
                        placeholder="输入训练任务名称"
                    )
                    
                    sft_config = gr.Dropdown(
                        label="选择系统配置",
                        choices=[(f"{c.name} (ID: {c.id})", c.id) 
                                for c in db.get_all_system_configs(only_valid=True)],
                        value=None
                    )
                    
                    sft_dataset = gr.Dropdown(
                        label="选择训练数据集",
                        choices=[(f"{d.name} (ID: {d.id})", d.id) 
                                for d in db.get_all_datasets()],
                        value=None
                    )
                    
                    sft_model = gr.Textbox(
                        label="模型路径",
                        placeholder="例如: Qwen/Qwen2.5-0.5B-Instruct",
                        value="Qwen/Qwen2.5-0.5B-Instruct"
                    )
                    
                    with gr.Accordion("高级参数", open=False):
                        sft_lr = gr.Number(label="学习率", value=2e-5)
                        sft_batch = gr.Number(label="Batch Size", value=4, precision=0)
                        sft_epochs = gr.Number(label="Epochs", value=3, precision=0)
                        sft_max_len = gr.Number(label="Max Length", value=2048, precision=0)
                    
                    sft_start_btn = gr.Button("🚀 开始训练", variant="primary")
                
                with gr.Column(scale=2):
                    gr.Markdown("### 训练状态")
                    
                    sft_status = gr.Markdown("等待开始训练...")
                    
                    sft_progress = gr.Slider(
                        label="训练进度",
                        minimum=0,
                        maximum=100,
                        value=0,
                        interactive=False
                    )
                    
                    sft_logs = gr.Textbox(
                        label="训练日志",
                        lines=10,
                        interactive=False
                    )
                    
                    sft_output = gr.Textbox(
                        label="输出信息",
                        interactive=False
                    )
        
        # DPO 训练 Tab
        with gr.TabItem("⚖️ DPO 训练"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 训练配置")
                    
                    dpo_name = gr.Textbox(
                        label="训练任务名称",
                        placeholder="输入训练任务名称"
                    )
                    
                    dpo_config = gr.Dropdown(
                        label="选择系统配置",
                        choices=[(f"{c.name} (ID: {c.id})", c.id) 
                                for c in db.get_all_system_configs(only_valid=True)],
                        value=None
                    )
                    
                    dpo_dataset = gr.Dropdown(
                        label="选择偏好数据集",
                        choices=[(f"{d.name} (ID: {d.id})", d.id) 
                                for d in db.get_all_datasets()],
                        value=None
                    )
                    
                    dpo_model = gr.Textbox(
                        label="模型路径",
                        placeholder="例如: Qwen/Qwen2.5-0.5B-Instruct",
                        value="Qwen/Qwen2.5-0.5B-Instruct"
                    )
                    
                    dpo_ref_model = gr.Textbox(
                        label="参考模型路径 (可选)",
                        placeholder="默认为模型路径",
                        value=""
                    )
                    
                    with gr.Accordion("高级参数", open=False):
                        dpo_lr = gr.Number(label="学习率", value=5e-7)
                        dpo_batch = gr.Number(label="Batch Size", value=2, precision=0)
                        dpo_epochs = gr.Number(label="Epochs", value=3, precision=0)
                        dpo_beta = gr.Number(label="Beta", value=0.1)
                    
                    dpo_start_btn = gr.Button("🚀 开始训练", variant="primary")
                
                with gr.Column(scale=2):
                    gr.Markdown("### 训练状态")
                    
                    dpo_status = gr.Markdown("等待开始训练...")
                    
                    dpo_progress = gr.Slider(
                        label="训练进度",
                        minimum=0,
                        maximum=100,
                        value=0,
                        interactive=False
                    )
                    
                    dpo_logs = gr.Textbox(
                        label="训练日志",
                        lines=10,
                        interactive=False
                    )
                    
                    dpo_output = gr.Textbox(
                        label="输出信息",
                        interactive=False
                    )
        
        # GRPO 训练 Tab
        with gr.TabItem("🎮 GRPO 训练"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 训练配置")
                    
                    grpo_name = gr.Textbox(
                        label="训练任务名称",
                        placeholder="输入训练任务名称"
                    )
                    
                    grpo_config = gr.Dropdown(
                        label="选择系统配置",
                        choices=[(f"{c.name} (ID: {c.id})", c.id) 
                                for c in db.get_all_system_configs(only_valid=True)],
                        value=None
                    )
                    
                    grpo_dataset = gr.Dropdown(
                        label="选择训练数据集",
                        choices=[(f"{d.name} (ID: {d.id})", d.id) 
                                for d in db.get_all_datasets()],
                        value=None
                    )
                    
                    grpo_model = gr.Textbox(
                        label="模型路径",
                        placeholder="例如: Qwen/Qwen2.5-0.5B-Instruct",
                        value="Qwen/Qwen2.5-0.5B-Instruct"
                    )
                    
                    grpo_reward_type = gr.Dropdown(
                        label="奖励类型",
                        choices=["gt_match", "rule", "llm_judge", "custom"],
                        value="gt_match"
                    )
                    
                    with gr.Accordion("高级参数", open=False):
                        grpo_lr = gr.Number(label="学习率", value=1e-6)
                        grpo_batch = gr.Number(label="Batch Size", value=4, precision=0)
                        grpo_rollout = gr.Number(label="Rollout Batch Size", value=64, precision=0)
                        grpo_kl = gr.Number(label="KL Coef", value=0.01)
                    
                    grpo_start_btn = gr.Button("🚀 开始训练", variant="primary")
                
                with gr.Column(scale=2):
                    gr.Markdown("### 训练状态")
                    
                    grpo_status = gr.Markdown("等待开始训练...")
                    
                    grpo_progress = gr.Slider(
                        label="训练进度",
                        minimum=0,
                        maximum=100,
                        value=0,
                        interactive=False
                    )
                    
                    grpo_logs = gr.Textbox(
                        label="训练日志",
                        lines=10,
                        interactive=False
                    )
                    
                    grpo_output = gr.Textbox(
                        label="输出信息",
                        interactive=False
                    )
        
        # 训练任务列表 Tab
        with gr.TabItem("📋 训练任务"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 所有训练任务")
                    
                    jobs = db.get_all_training_jobs()
                    job_data = []
                    for j in jobs:
                        job_data.append([
                            j.id,
                            j.name,
                            j.type.upper(),
                            j.status,
                            j.created_at.strftime('%Y-%m-%d %H:%M')
                        ])
                    
                    job_table = gr.Dataframe(
                        headers=["ID", "名称", "类型", "状态", "创建时间"],
                        value=job_data if job_data else [["", "", "", "", ""]],
                        interactive=False
                    )
                    
                    with gr.Row():
                        refresh_job_btn = gr.Button("🔄 刷新")
                        view_job_btn = gr.Button("👁️ 查看详情")
                        stop_job_btn = gr.Button("⏹️ 停止", variant="stop")
                    
                    job_id_input = gr.Number(label="任务 ID", precision=0)
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 任务详情")
                    job_detail = gr.JSON(label="任务信息")
    
    # 事件处理函数
    def start_sft_training(name, config_id, dataset_id, model_path, lr, batch, epochs, max_len):
        if not name or not config_id:
            return "❌ 请提供任务名称和配置", 0, "", ""
        
        try:
            import os
            import threading
            import time
            import json
            
            # 创建训练任务记录
            job = db.create_training_job(
                name=name,
                type='sft',
                config={'config_id': config_id, 'dataset_id': dataset_id, 'model': model_path},
                dataset_id=int(dataset_id) if dataset_id else None,
                config_id=int(config_id),
                hyperparameters={
                    'lr': lr,
                    'batch_size': batch,
                    'epochs': epochs,
                    'max_length': max_len
                }
            )
            
            # 更新状态为运行中
            db.update_training_status(job.id, 'running')
            
            # 准备训练数据
            trainer = SFTTrainer()
            
            logs_list = [
                f"SFT 训练任务已创建 (ID: {job.id})",
                f"任务名称: {name}",
                f"模型: {model_path}",
                f"学习率: {lr}",
                f"Batch Size: {batch}",
                f"Epochs: {epochs}",
                "",
                "准备训练数据..."
            ]
            
            # 获取数据集文件路径
            data_file = None
            if dataset_id:
                try:
                    dataset = db.get_dataset(int(dataset_id))
                    if dataset and dataset.file_path:
                        data_file = dataset.file_path
                        logs_list.append(f"使用选择的数据集: {dataset.name} ({data_file})")
                except Exception as e:
                    logs_list.append(f"获取数据集失败: {e}")
            
            # 如果没有选择数据集或获取失败，使用默认数据集
            if not data_file:
                data_file = "test_sft_dataset.jsonl"
                logs_list.append(f"使用默认数据集: {data_file}")
            
            # 验证数据文件存在
            if not os.path.exists(data_file):
                return f"❌ 数据文件不存在: {data_file}", 0, "\n".join(logs_list), ""
            
            # 验证数据格式
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    sample = json.loads(first_line)
                    if 'messages' not in sample:
                        return f"❌ 数据格式错误: 缺少 'messages' 字段", 0, "\n".join(logs_list), ""
                logs_list.append(f"数据格式验证通过")
            except Exception as e:
                return f"❌ 数据格式验证失败: {e}", 0, "\n".join(logs_list), ""
            
            logs_list.append(f"训练数据文件: {data_file}")
            logs_list.append("启动训练...")
            
            # 用于收集日志的变量
            training_logs = []
            current_progress = {"step": 0, "total_steps": 0, "loss": 0.0}
            
            def log_callback(msg):
                training_logs.append(msg)
                # 解析进度信息
                if 'loss' in msg.lower():
                    try:
                        # 尝试解析 loss 和 step 信息
                        if 'step' in msg.lower():
                            parts = msg.split()
                            for i, part in enumerate(parts):
                                if 'step' in part.lower() and i + 1 < len(parts):
                                    try:
                                        step_info = parts[i + 1].split('/')
                                        if len(step_info) == 2:
                                            current_progress["step"] = int(step_info[0])
                                            current_progress["total_steps"] = int(step_info[1])
                                    except:
                                        pass
                    except:
                        pass
                # 实时更新数据库日志
                db.update_training_status(
                    job_id=job.id,
                    status='running',
                    logs="\n".join(training_logs[-100:])  # 只保留最后100行
                )
            
            def run_training():
                try:
                    result = trainer.train_with_api(
                        data_file=data_file,
                        model_path=model_path,
                        hyperparameters={
                            'lr': lr,
                            'batch_size': int(batch),
                            'num_epochs': int(epochs),
                            'max_length': int(max_len),
                            'use_lora': True,
                            'lora_rank': 8,
                            'lora_alpha': 32,
                            'gradient_checkpointing': True
                        },
                        log_callback=log_callback
                    )
                    
                    # 更新任务状态
                    final_status = 'completed' if result['status'] == 'completed' else 'failed'
                    db.update_training_status(
                        job_id=job.id,
                        status=final_status,
                        output_dir=result.get('output_dir'),
                        logs="\n".join(training_logs)
                    )
                except Exception as e:
                    import traceback
                    error_msg = f"训练异常: {str(e)}\n{traceback.format_exc()}"
                    training_logs.append(error_msg)
                    db.update_training_status(
                        job_id=job.id,
                        status='failed',
                        logs="\n".join(training_logs)
                    )
            
            # 在后台线程中运行训练
            training_thread = threading.Thread(target=run_training)
            training_thread.daemon = True
            training_thread.start()
            
            # 等待几秒让训练启动
            time.sleep(2)
            
            output = f"""
训练任务已启动！
任务 ID: {job.id}
训练数据: {data_file}

训练正在后台运行。
提示：点击"刷新状态"按钮查看实时进度和日志。
            """
            
            return "✅ 训练任务已启动", 10, "\n".join(logs_list), output
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return f"❌ 启动失败: {str(e)}\n{error_detail}", 0, str(e), ""
    
    def start_dpo_training(name, config_id, dataset_id, model_path, ref_model,
                          lr, batch, epochs, beta):
        if not name or not config_id:
            return "❌ 请提供任务名称和配置", 0, "", ""
        
        try:
            job = db.create_training_job(
                name=name,
                type='dpo',
                config={'config_id': config_id, 'dataset_id': dataset_id, 'model': model_path},
                dataset_id=int(dataset_id) if dataset_id else None,
                config_id=int(config_id),
                hyperparameters={
                    'lr': lr,
                    'batch_size': batch,
                    'epochs': epochs,
                    'beta': beta
                }
            )
            
            db.update_training_status(job.id, 'running')
            
            trainer = DPOTrainer()
            
            logs = [
                f"DPO 训练任务已创建 (ID: {job.id})",
                f"任务名称: {name}",
                f"模型: {model_path}",
                f"学习率: {lr}",
                f"Beta: {beta}",
                "",
                "准备偏好数据...",
                "启动训练..."
            ]
            
            training_info = trainer.train(
                data_file="data/train.jsonl",
                model_path=model_path,
                ref_model_path=ref_model if ref_model else None,
                hyperparameters={
                    'lr': lr,
                    'batch_size': batch,
                    'num_epochs': epochs,
                    'beta': beta
                }
            )
            
            script = trainer.get_training_script(training_info)
            script_path = f"training_outputs/dpo_job_{job.id}.sh"
            
            import os
            os.makedirs(os.path.dirname(script_path) or '.', exist_ok=True)
            with open(script_path, 'w') as f:
                f.write(script)
            
            output = f"""
DPO 训练任务已准备完成！
任务 ID: {job.id}
输出目录: {training_info.get('output_dir')}
训练脚本: {script_path}

请在命令行中运行：
bash {script_path}
            """
            
            return "✅ DPO 训练任务已准备", 10, "\n".join(logs), output
            
        except Exception as e:
            return f"❌ 启动失败: {str(e)}", 0, str(e), ""
    
    def start_grpo_training(name, config_id, dataset_id, model_path, reward_type,
                           lr, batch, rollout, kl):
        if not name or not config_id:
            return "❌ 请提供任务名称和配置", 0, "", ""
        
        try:
            job = db.create_training_job(
                name=name,
                type='grpo',
                config={'config_id': config_id, 'dataset_id': dataset_id, 'model': model_path},
                dataset_id=int(dataset_id) if dataset_id else None,
                config_id=int(config_id),
                hyperparameters={
                    'lr': lr,
                    'batch_size': batch,
                    'rollout_batch_size': rollout,
                    'kl_coef': kl
                }
            )
            
            db.update_training_status(job.id, 'running')
            
            trainer = GRPOTrainer()
            
            # 奖励规格
            reward_spec = [{
                'reward_id': f'reward.{reward_type}',
                'type': reward_type,
                'weight': 1.0
            }]
            
            logs = [
                f"GRPO 训练任务已创建 (ID: {job.id})",
                f"任务名称: {name}",
                f"模型: {model_path}",
                f"奖励类型: {reward_type}",
                f"KL Coef: {kl}",
                "",
                "准备 Rollout 数据...",
                "启动训练..."
            ]
            
            training_info = trainer.train(
                data_file="data/train.jsonl",
                model_path=model_path,
                reward_spec=reward_spec,
                hyperparameters={
                    'lr': lr,
                    'batch_size': batch,
                    'rollout_batch_size': rollout,
                    'kl_coef': kl
                }
            )
            
            script = trainer.get_training_script(training_info)
            script_path = f"training_outputs/grpo_job_{job.id}.sh"
            
            import os
            os.makedirs(os.path.dirname(script_path) or '.', exist_ok=True)
            with open(script_path, 'w') as f:
                f.write(script)
            
            output = f"""
GRPO 训练任务已准备完成！
任务 ID: {job.id}
输出目录: {training_info.get('output_dir')}
训练脚本: {script_path}

请在命令行中运行：
bash {script_path}
            """
            
            return "✅ GRPO 训练任务已准备", 10, "\n".join(logs), output
            
        except Exception as e:
            return f"❌ 启动失败: {str(e)}", 0, str(e), ""
    
    def refresh_jobs():
        jobs = db.get_all_training_jobs()
        job_data = []
        for j in jobs:
            job_data.append([
                j.id,
                j.name,
                j.type.upper(),
                j.status,
                j.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        return job_data if job_data else [["", "", "", "", ""]]
    
    def view_job(job_id):
        if not job_id:
            return {"error": "请提供任务 ID"}, "", 0
        
        job = db.get_training_job(int(job_id))
        if not job:
            return {"error": "任务不存在"}, "", 0
        
        # 计算进度
        progress = 0
        if job.status == 'completed':
            progress = 100
        elif job.status == 'running':
            # 尝试从日志解析进度
            if job.logs:
                # 简单估计：根据日志行数估算进度
                log_lines = job.logs.split('\n')
                # 通常训练开始后有模型加载日志，然后才是训练日志
                # 这里做一个简单估算
                if len(log_lines) > 50:
                    progress = min(95, int(len(log_lines) / 200 * 100))
                else:
                    progress = 5
        
        job_info = {
            "id": job.id,
            "name": job.name,
            "type": job.type,
            "status": job.status,
            "progress": f"{progress}%",
            "config": job.config,
            "hyperparameters": job.hyperparameters,
            "output_dir": job.output_dir,
            "metrics": job.metrics,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
        
        # 返回日志（最后 50 行）
        logs = job.logs if job.logs else "暂无日志"
        log_lines = logs.split('\n')
        recent_logs = '\n'.join(log_lines[-50:]) if len(log_lines) > 50 else logs
        
        return job_info, recent_logs, progress
    
    # 绑定事件
    sft_start_btn.click(
        fn=start_sft_training,
        inputs=[sft_name, sft_config, sft_dataset, sft_model, sft_lr, sft_batch, sft_epochs, sft_max_len],
        outputs=[sft_status, sft_progress, sft_logs, sft_output]
    )
    
    dpo_start_btn.click(
        fn=start_dpo_training,
        inputs=[dpo_name, dpo_config, dpo_dataset, dpo_model, dpo_ref_model,
                dpo_lr, dpo_batch, dpo_epochs, dpo_beta],
        outputs=[dpo_status, dpo_progress, dpo_logs, dpo_output]
    )
    
    grpo_start_btn.click(
        fn=start_grpo_training,
        inputs=[grpo_name, grpo_config, grpo_dataset, grpo_model, grpo_reward_type,
                grpo_lr, grpo_batch, grpo_rollout, grpo_kl],
        outputs=[grpo_status, grpo_progress, grpo_logs, grpo_output]
    )
    
    refresh_job_btn.click(
        fn=refresh_jobs,
        outputs=job_table
    )
    
    view_job_btn.click(
        fn=view_job,
        inputs=job_id_input,
        outputs=[job_detail, gr.Textbox(label="训练日志", lines=15), gr.Slider(label="进度", minimum=0, maximum=100)]
    )
