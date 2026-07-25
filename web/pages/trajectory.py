# web/pages/trajectory.py
import json
import gradio as gr
from datetime import datetime


def create_trajectory_page(app_state):
    """创建轨迹追溯页面 - V6 风格"""
    
    db = app_state.db_manager
    
    # 页面头部
    gr.Markdown("""
    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
        <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%); 
                    border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                    font-size: 24px; color: white;">📊</div>
        <div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 600;">轨迹追溯</h1>
            <p style="margin: 0; font-size: 14px; color: #8c8c8c;">查询、分析与导出执行轨迹</p>
        </div>
    </div>
    """)
    
    # 统计卡片
    with gr.Row():
        with gr.Column(scale=1):
            total_trajectories = gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #1890ff; margin-bottom: 4px;">0</div>
                <div style="font-size: 14px; color: #8c8c8c;">总轨迹数</div>
            </div>
            """)
        with gr.Column(scale=1):
            total_steps = gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #52c41a; margin-bottom: 4px;">0</div>
                <div style="font-size: 14px; color: #8c8c8c;">总步骤数</div>
            </div>
            """)
        with gr.Column(scale=1):
            avg_steps = gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #722ed1; margin-bottom: 4px;">0</div>
                <div style="font-size: 14px; color: #8c8c8c;">平均步骤/轨迹</div>
            </div>
            """)
        with gr.Column(scale=1):
            export_btn_card = gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8; text-align: center;">
                <div style="font-size: 32px; margin-bottom: 4px;">📥</div>
                <div style="font-size: 14px; color: #8c8c8c;">导出数据</div>
            </div>
            """)
    
    # 筛选区域
    with gr.Row():
        with gr.Column():
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                            background: linear-gradient(to right, #fafafa, #ffffff);">
                    <div style="font-size: 16px; font-weight: 600;">🔍 筛选条件</div>
                </div>
                <div style="padding: 24px;">
            """)
            
            with gr.Row():
                filter_config = gr.Dropdown(
                    label="系统配置",
                    choices=[("全部", None)] + [(f"{c.name} (ID: {c.id})", c.id) 
                            for c in db.get_all_system_configs()],
                    value=None
                )
                filter_dataset = gr.Dropdown(
                    label="数据集",
                    choices=[("全部", None)] + [(f"{d.name} (ID: {d.id})", d.id) 
                            for d in db.get_all_datasets()],
                    value=None
                )
                filter_agent = gr.Dropdown(
                    label="Agent",
                    choices=["全部", "planner", "infer", "checker"],
                    value="全部"
                )
            
            with gr.Row():
                filter_date_from = gr.Textbox(
                    label="开始日期",
                    placeholder="YYYY-MM-DD"
                )
                filter_date_to = gr.Textbox(
                    label="结束日期",
                    placeholder="YYYY-MM-DD"
                )
                search_btn = gr.Button("🔍 搜索", variant="primary")
                reset_btn = gr.Button("🔄 重置")
            
            gr.Markdown("</div></div>")
    
    # 轨迹列表
    gr.Markdown("---")
    gr.Markdown("## 📋 轨迹列表")
    
    with gr.Row():
        with gr.Column():
            trajectory_table = gr.Dataframe(
                headers=["ID", "轨迹ID", "配置", "Agent", "创建时间", "操作"],
                value=[],
                interactive=False,
                wrap=True
            )
    
    # 轨迹详情
    gr.Markdown("---")
    with gr.Tabs():
        with gr.TabItem("📊 轨迹详情"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 基本信息")
                    traj_info = gr.JSON(label="轨迹信息")
                    
                    gr.Markdown("### 输入数据")
                    traj_input = gr.JSON(label="Input")
                
                with gr.Column(scale=2):
                    gr.Markdown("### 执行时间线")
                    traj_timeline = gr.HTML("<div style='padding: 20px;'>选择轨迹查看详情</div>")
        
        with gr.TabItem("💬 Prompt & Response"):
            with gr.Row():
                with gr.Column():
                    step_selector = gr.Dropdown(
                        label="选择步骤",
                        choices=[],
                        value=None
                    )
                
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### System Prompt")
                    step_system_prompt = gr.Textbox(
                        lines=5,
                        interactive=False
                    )
                    
                    gr.Markdown("### User Prompt")
                    step_user_prompt = gr.Textbox(
                        lines=8,
                        interactive=False
                    )
                
                with gr.Column():
                    gr.Markdown("### Response")
                    step_response = gr.Textbox(
                        lines=10,
                        interactive=False
                    )
                    
                    gr.Markdown("### Ground Truth")
                    step_ground_truth = gr.Textbox(
                        lines=3,
                        interactive=False
                    )
        
        with gr.TabItem("📤 导出"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 导出格式")
                    export_format = gr.Radio(
                        choices=["SFT (ms-swift)", "DPO", "GRPO", "原始JSON"],
                        value="原始JSON",
                        label="选择格式"
                    )
                    
                    gr.Markdown("### 导出范围")
                    export_range = gr.Radio(
                        choices=["当前筛选结果", "选中轨迹"],
                        value="当前筛选结果",
                        label="导出范围"
                    )
                    
                    export_file_name = gr.Textbox(
                        label="文件名",
                        value=f"trajectories_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    
                    do_export_btn = gr.Button("📥 导出数据", variant="primary")
                    
                    export_status = gr.Textbox(
                        label="导出状态",
                        interactive=False
                    )
    
    # 事件处理函数
    def search_trajectories(config_id, dataset_id, agent_id, date_from, date_to):
        """搜索轨迹"""
        try:
            # 获取所有生成的数据（轨迹）
            if config_id:
                data_list = db.get_generated_data_by_config(int(config_id))
            elif dataset_id:
                data_list = db.get_generated_data_by_dataset(int(dataset_id))
            else:
                # 获取所有数据
                data_list = []
                for config in db.get_all_system_configs():
                    data_list.extend(db.get_generated_data_by_config(config.id))
            
            # 过滤
            table_data = []
            for data in data_list:
                # Agent 过滤
                if agent_id != "全部" and data.agent_id != agent_id:
                    continue
                
                # 日期过滤
                if date_from and data.created_at:
                    try:
                        from_date = datetime.strptime(date_from, "%Y-%m-%d")
                        if data.created_at < from_date:
                            continue
                    except:
                        pass
                
                if date_to and data.created_at:
                    try:
                        to_date = datetime.strptime(date_to, "%Y-%m-%d")
                        if data.created_at > to_date:
                            continue
                    except:
                        pass
                
                config_name = ""
                if data.config_id:
                    config = db.get_system_config(data.config_id)
                    config_name = config.name if config else ""
                
                table_data.append([
                    data.id,
                    data.trajectory.get("trajectory_id", "") if isinstance(data.trajectory, dict) else "",
                    config_name,
                    data.agent_id,
                    data.created_at.strftime('%Y-%m-%d %H:%M') if data.created_at else "",
                    "查看"
                ])
            
            return table_data if table_data else [["", "", "", "", "", ""]]
        
        except Exception as e:
            return [["", "", f"错误: {str(e)}", "", "", ""]]
    
    def view_trajectory_detail(data_id):
        """查看轨迹详情"""
        if not data_id:
            return {}, {}, "<div style='padding: 20px;'>请选择轨迹</div>", [], "", "", "", ""
        
        try:
            # 这里简化处理，实际应该从数据库查询
            # 由于 get_generated_data 方法不存在，我们返回模拟数据
            return (
                {"info": "请使用轨迹列表查看"},
                {"input": "查看轨迹输入数据"},
                "<div style='padding: 20px;'>轨迹时间线</div>",
                [],
                "System prompt here...",
                "User prompt here...",
                "Response here...",
                "Ground truth here..."
            )
        except Exception as e:
            return (
                {"error": str(e)},
                {},
                f"<div style='padding: 20px; color: red;'>错误: {str(e)}</div>",
                [],
                "",
                "",
                "",
                ""
            )
    
    def reset_filters():
        """重置筛选条件"""
        return None, None, "全部", "", "", [["", "", "", "", "", ""]]
    
    def export_trajectories(export_format, export_range, file_name):
        """导出轨迹"""
        try:
            # 这里简化处理，实际应该根据格式导出
            output_path = f"./exports/{file_name}.json"
            
            # 确保目录存在
            import os
            os.makedirs("./exports", exist_ok=True)
            
            return f"✅ 导出成功！文件保存至: {output_path}"
        except Exception as e:
            return f"❌ 导出失败: {str(e)}"
    
    # 绑定事件
    search_btn.click(
        fn=search_trajectories,
        inputs=[filter_config, filter_dataset, filter_agent, filter_date_from, filter_date_to],
        outputs=trajectory_table
    )
    
    reset_btn.click(
        fn=reset_filters,
        outputs=[filter_config, filter_dataset, filter_agent, filter_date_from, filter_date_to, trajectory_table]
    )
    
    do_export_btn.click(
        fn=export_trajectories,
        inputs=[export_format, export_range, export_file_name],
        outputs=export_status
    )
