# web/pages/execution_flow.py
import os
import json
import gradio as gr
from spec.system_spec import SystemSpec
from core.trajectory_generator import TrajectoryGenerator


def create_execution_flow_page(app_state):
    """创建执行流程页面 - V6 风格"""
    
    db = app_state.db_manager
    
    # 页面头部
    gr.Markdown("""
    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
        <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%); 
                    border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                    font-size: 24px; color: white;">▶️</div>
        <div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 600;">执行中心</h1>
            <p style="margin: 0; font-size: 14px; color: #8c8c8c;">批量推理与实时监控</p>
        </div>
    </div>
    """)
    
    # 统计卡片
    with gr.Row():
        with gr.Column(scale=1):
            completed_stat = gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #52c41a; margin-bottom: 4px;">0/0</div>
                <div style="font-size: 14px; color: #8c8c8c;">已完成</div>
            </div>
            """)
        with gr.Column(scale=1):
            running_stat = gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #1890ff; margin-bottom: 4px;">0</div>
                <div style="font-size: 14px; color: #8c8c8c;">运行中</div>
            </div>
            """)
        with gr.Column(scale=1):
            pending_stat = gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #8c8c8c; margin-bottom: 4px;">0</div>
                <div style="font-size: 14px; color: #8c8c8c;">待执行</div>
            </div>
            """)
        with gr.Column(scale=1):
            time_stat = gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; margin-bottom: 4px;">0s</div>
                <div style="font-size: 14px; color: #8c8c8c;">平均耗时</div>
            </div>
            """)
    
    # 主内容区
    with gr.Row():
        # 左侧：运行配置
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                            background: linear-gradient(to right, #fafafa, #ffffff);">
                    <div style="font-size: 16px; font-weight: 600;">运行配置</div>
                </div>
                <div style="padding: 24px;">
            """)
            
            # 选择配置
            exec_config = gr.Dropdown(
                label="选择系统配置",
                choices=[(f"{c.name} (ID: {c.id}, {'✅' if c.is_valid else '❌'})", c.id) 
                        for c in db.get_all_system_configs(only_valid=True)],
                value=None
            )
            
            # 选择数据集
            exec_dataset = gr.Dropdown(
                label="选择测试数据集",
                choices=[(f"{d.name} (ID: {d.id})", d.id) 
                        for d in db.get_all_datasets()],
                value=None
            )
            
            # 刷新按钮
            refresh_data_btn = gr.Button("🔄 刷新数据", size="sm")
            
            # 执行选项
            use_teacher = gr.Checkbox(
                label="使用教师模型生成 Ground Truth",
                value=False
            )
            
            record_trajectory = gr.Checkbox(
                label="记录执行轨迹",
                value=True
            )
            
            with gr.Row():
                run_btn = gr.Button("▶️ 开始执行", variant="primary")
                stop_btn = gr.Button("⏹️ 停止", variant="stop")
            
            gr.Markdown("</div></div>")
        
        # 右侧：执行状态
        with gr.Column(scale=2):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                            background: linear-gradient(to right, #fafafa, #ffffff);">
                    <div style="font-size: 16px; font-weight: 600;">实时执行状态</div>
                </div>
                <div style="padding: 24px;">
            """)
            
            # 实时执行状态可视化
            exec_viz = gr.HTML(
                value="""
                <div style="display: flex; align-items: center; justify-content: center; padding: 40px;">
                    <div style="color: #8c8c8c; text-align: center;">
                        <div style="font-size: 48px; margin-bottom: 16px;">⏳</div>
                        <div>等待执行...</div>
                    </div>
                </div>
                """)
            
            # 执行日志
            exec_logs = gr.Textbox(
                label="执行日志",
                lines=8,
                interactive=False
            )
            
            # 当前 State 状态
            gr.Markdown("<div style='margin-top: 16px; font-weight: 600;'>📋 当前State状态</div>")
            state_display = gr.JSON(label="State 数据")
            
            gr.Markdown("</div></div>")
    
    # 执行结果展示
    gr.Markdown("---")
    gr.Markdown("## 📊 执行结果")
    
    with gr.Tabs():
        with gr.TabItem("📊 执行结果"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 最终输出")
                    final_output = gr.JSON(label="输出结果")
                
                with gr.Column():
                    gr.Markdown("### 执行统计")
                    exec_stats = gr.JSON(label="统计信息")
        
        with gr.TabItem("🔄 执行轨迹"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 轨迹列表")
                    trajectory_list = gr.Dataframe(
                        headers=["轨迹ID", "Agent", "步骤数", "状态"],
                        interactive=False
                    )
                
                with gr.Column(scale=2):
                    gr.Markdown("### 步骤详情")
                    step_detail = gr.JSON(label="详细信息")
                    
                    with gr.Row():
                        step_prompt = gr.Textbox(
                            label="Prompt",
                            lines=5,
                            interactive=False
                        )
                        step_response = gr.Textbox(
                            label="Response",
                            lines=5,
                            interactive=False
                        )
        
        with gr.TabItem("📈 可视化流程"):
            gr.Markdown("### 执行流程可视化")
            flow_visualization = gr.HTML("<div style='padding: 20px;'>执行后将显示流程图</div>")
    
    # 事件处理函数
    def run_execution(config_id, dataset_id, use_teacher_gt, record_traj):
        if not config_id:
            return (
                "<div style='padding: 20px; color: red;'>请选择系统配置</div>",
                "请先选择一个系统配置",
                {},
                {},
                [["", "", "", ""]],
                {"info": "No execution"},
                "No prompt",
                "No response",
                "<div style='padding: 20px;'>请选择配置</div>"
            )
        
        logs = []
        state_data = {}
        
        try:
            # 获取配置
            config = db.get_system_config(int(config_id))
            if not config:
                return (
                    "<div style='padding: 20px; color: red;'>配置不存在</div>",
                    "配置不存在或已被删除",
                    {},
                    {"error": "Config not found"},
                    [["", "", "", ""]],
                    {"error": "No data"},
                    "Error",
                    "Error",
                    "<div style='padding: 20px;'>错误</div>"
                )
            
            logs.append(f"[INFO] 配置: {config.name} (ID: {config.id})")
            logs.append(f"[INFO] Agent 数量: {config.agent_count}")
            logs.append(f"[INFO] 执行顺序: {config.execution_order}")
            
            # 获取数据集
            inputs = []
            if dataset_id:
                logs.append(f"[INFO] 使用数据集 ID: {dataset_id}")
                dataset = db.get_dataset(int(dataset_id))
                if dataset:
                    logs.append(f"[INFO] 数据集: {dataset.name}")
                    if os.path.exists(dataset.file_path):
                        with open(dataset.file_path, 'r', encoding='utf-8') as f:
                            if dataset.file_format == 'jsonl':
                                inputs = [json.loads(line) for line in f.readlines()]
                            else:
                                inputs = json.load(f)
                        logs.append(f"[INFO] 成功读取数据集，包含 {len(inputs)} 条记录")
                    else:
                        logs.append(f"[WARN] 数据集文件不存在: {dataset.file_path}")
                else:
                    logs.append("[WARN] 数据集不存在")
            
            # 如果没有数据集，使用示例输入
            if not inputs:
                inputs = [{"user_request": "帮我制定一个学习计划，准备下周的数学考试"}]
                logs.append("[INFO] 使用默认示例输入")
            
            # 创建执行记录
            execution = db.create_execution(
                config_id=int(config_id),
                dataset_id=int(dataset_id) if dataset_id else None
            )
            logs.append(f"[INFO] 创建执行记录 (ID: {execution.id})")
            
            # 更新状态为运行中
            db.update_execution_status(execution.id, 'running')
            logs.append(f"[INFO] 样本数量: {len(inputs)}")
            
            # 解析配置
            logs.append("[INFO] 解析配置...")
            spec = SystemSpec(agents=config.config_json)
            logs.append(f"[INFO] 配置解析成功，包含 {len(spec.agents)} 个 Agent")
            
            # 使用 TrajectoryGenerator 生成轨迹
            logs.append("[INFO] 正在生成轨迹...")
            generator = TrajectoryGenerator(spec, config_id=int(config_id))
            
            # 生成轨迹
            trajectories = generator.generate_batch(inputs, use_teacher=False)
            logs.append(f"[SUCCESS] 执行完成！生成了 {len(trajectories)} 条轨迹")
            
            # 收集结果
            results = []
            for traj in trajectories:
                final_output_data = traj.steps[-1].output_data if traj.steps else {}
                results.append({
                    'trajectory_id': traj.trajectory_id,
                    'final_output': final_output_data
                })
            
            # 保存轨迹到数据库
            for traj in trajectories:
                for step in traj.steps:
                    db.create_generated_data(
                        agent_id=step.agent_id,
                        trajectory=step.to_dict(),
                        config_id=int(config_id),
                        dataset_id=int(dataset_id) if dataset_id else None,
                        input_data=step.input_data,
                        output_data=step.output_data,
                        ground_truth={'response': step.ground_truth} if step.ground_truth else None
                    )
            
            # 更新执行状态
            db.update_execution_status(
                execution_id=execution.id,
                status='completed',
                result={'sample_count': len(results), 'outputs': results}
            )
            
            # 准备输出
            final_result = {
                'execution_id': execution.id,
                'config_name': config.name,
                'sample_count': len(results),
                'outputs': results[:3]  # 只显示前3个
            }
            
            stats = {
                'total_samples': len(inputs),
                'completed': len(results),
                'agents': config.agent_count,
                'execution_order': config.execution_order or []
            }
            
            # 轨迹数据
            traj_data = []
            for traj in trajectories:
                for step in traj.steps:
                    traj_data.append([
                        traj.trajectory_id,
                        step.agent_id,
                        step.step_index + 1,
                        "完成"
                    ])
            
            if not traj_data:
                traj_data = [["", "", "", ""]]
            
            # 获取最后一步的详细信息
            last_traj = trajectories[0] if trajectories else None
            last_step = last_traj.steps[-1] if last_traj and last_traj.steps else None
            
            step_detail_data = {
                "trajectory_id": last_traj.trajectory_id if last_traj else "",
                "agent": last_step.agent_id if last_step else "",
                "step": last_step.step_index if last_step else 0,
                "timestamp": last_step.timestamp if last_step else ""
            } if last_traj else {"info": "No trajectory data"}
            
            step_prompt_text = last_step.prompt if last_step else "No prompt"
            step_response_text = last_step.response if last_step else "No response"
            
            # 生成可视化
            viz_html = generate_exec_viz(config.execution_order or [], "completed")
            
            # 更新 state 显示
            if last_step:
                state_data = last_step.output_data
            
            return (
                viz_html,
                "\\n".join(logs),
                state_data,
                final_result,
                stats,
                traj_data,
                step_detail_data,
                step_prompt_text,
                step_response_text,
                viz_html
            )
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logs.append(f"\\n[ERROR] 执行失败: {str(e)}")
            logs.append(f"[ERROR] 错误详情:\\n{error_detail}")
            
            return (
                f"<div style='padding: 20px; color: red;'>执行失败: {str(e)}</div>",
                "\\n".join(logs),
                {},
                {"error": str(e)},
                {"status": "failed"},
                [["", "", "", ""]],
                {"error": "Execution failed"},
                "Error",
                "Error occurred",
                f"<div style='padding: 20px; color: red;'>错误: {str(e)}</div>"
            )
    
    def generate_exec_viz(execution_order, status):
        """生成执行可视化 HTML"""
        if not execution_order:
            return "<div style='padding: 20px;'>未配置执行顺序</div>"
        
        html = ['<div style="display: flex; align-items: center; justify-content: center; padding: 40px;">']
        
        for i, agent_id in enumerate(execution_order):
            # 确定状态样式
            if status == "completed":
                node_status = "completed"
                border_color = "#52c41a"
                badge = "✓"
                badge_bg = "#52c41a"
            elif status == "running" and i == 0:
                node_status = "running"
                border_color = "#1890ff"
                badge = "●"
                badge_bg = "#1890ff"
            else:
                node_status = "pending"
                border_color = "#d9d9d9"
                badge = ""
                badge_bg = "transparent"
            
            # Agent 节点
            badge_html = f'''<div style="position: absolute; top: -10px; right: -10px; width: 24px; height: 24px; 
                            border-radius: 50%; display: flex; align-items: center; justify-content: center; 
                            font-size: 12px; color: white; border: 2px solid white; background: {badge_bg};">
                            {badge}</div>''' if badge else ""
            
            html.append(f'''
                <div style="display: inline-flex; flex-direction: column; align-items: center; padding: 20px 28px; 
                            background: white; border: 2px solid {border_color}; border-radius: 16px; 
                            margin: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); position: relative; min-width: 120px;">
                    {badge_html}
                    <div style="font-weight: 600; font-size: 16px;">{agent_id}</div>
                </div>
            ''')
            
            # 箭头（除了最后一个）
            if i < len(execution_order) - 1:
                html.append('<div style="display: flex; align-items: center; color: #bfbfbf; font-size: 24px; margin: 0 20px;">→</div>')
        
        html.append('</div>')
        return "".join(html)
    
    def refresh_datasets():
        """刷新数据集列表"""
        datasets = db.get_all_datasets()
        choices = [(f"{d.name} (ID: {d.id})", d.id) for d in datasets]
        return gr.Dropdown(choices=choices if choices else [("无数据集", None)])
    
    def refresh_configs():
        """刷新配置列表"""
        configs = db.get_all_system_configs(only_valid=True)
        choices = [(f"{c.name} (ID: {c.id}, {'✅' if c.is_valid else '❌'})", c.id) for c in configs]
        return gr.Dropdown(choices=choices if choices else [("无配置", None)])
    
    # 绑定事件
    refresh_data_btn.click(
        fn=refresh_datasets,
        outputs=exec_dataset
    )
    
    run_btn.click(
        fn=run_execution,
        inputs=[exec_config, exec_dataset, use_teacher, record_trajectory],
        outputs=[
            exec_viz,
            exec_logs,
            state_display,
            final_output,
            exec_stats,
            trajectory_list,
            step_detail,
            step_prompt,
            step_response,
            flow_visualization
        ]
    )
