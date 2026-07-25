# web/pages/json_config.py
import os
import json
import gradio as gr
from core.json_validator import JSONValidator


def create_json_config_page(app_state):
    """创建 JSON 配置管理页面 - V6 风格"""
    
    db = app_state.db_manager
    validator = JSONValidator()
    
    # 页面头部
    with gr.Row():
        with gr.Column():
            gr.Markdown("""
            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
                <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                            font-size: 24px; color: white;">🔧</div>
                <div>
                    <h1 style="margin: 0; font-size: 24px; font-weight: 600;">系统构建器</h1>
                    <p style="margin: 0; font-size: 14px; color: #8c8c8c;">JSON定义 → 自动解析 → 可视化生成</p>
                </div>
            </div>
            """)
    
    # 主内容区 - 两列布局
    with gr.Row():
        # 左侧：JSON编辑和配置
        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.TabItem("System Spec (JSON)"):
                    # 文件上传
                    config_file_upload = gr.File(
                        label="📥 导入 JSON 文件",
                        file_types=[".json"],
                        type="filepath"
                    )
                    
                    # JSON 编辑器
                    json_editor = gr.Code(
                        label="System Spec (JSON)",
                        language="json",
                        value="""[
  {
    "agent_id": "planner",
    "model": { "name_or_path": "Qwen2.5-0.5B-Instruct" },
    "instruction_prompt": {
      "instruction": "你是 Planner Agent：把用户需求拆成可执行的步骤计划。",
      "prompt_template": "用户需求：{{input.user_request}}\\n请输出 JSON 格式的 plan。"
    },
    "input": [{ "from": "user", "key": "user_request" }],
    "output": [{ "key": "plan", "to": [{ "agent": "infer", "as": "plan" }] }]
  },
  {
    "agent_id": "infer",
    "model": { "name_or_path": "Qwen2.5-0.5B-Instruct" },
    "instruction_prompt": {
      "instruction": "你是 Inference Agent：按照 plan 解决问题并生成答案。",
      "prompt_template": "Plan：{{input.plan}}\\n问题：{{input.user_request}}\\n请给出答案："
    },
    "input": [
      { "from": "user", "key": "user_request" },
      { "from": "planner", "key": "plan" }
    ],
    "output": [{ "key": "draft_answer", "to": [{ "agent": "checker", "as": "draft_answer" }] }]
  },
  {
    "agent_id": "checker",
    "model": { "name_or_path": "Qwen2.5-0.5B-Instruct" },
    "instruction_prompt": {
      "instruction": "你是 Checker Agent：检查答案是否正确。",
      "prompt_template": "问题：{{input.user_request}}\\n候选答案：{{input.draft_answer}}\\n请输出：{verdict, final_answer}"
    },
    "input": [
      { "from": "user", "key": "user_request" },
      { "from": "infer", "key": "draft_answer" }
    ],
    "output": [
      { "key": "final_answer", "to": [{ "user": true }] },
      { "key": "verdict", "to": [{ "user": true }] }
    ]
  }
]""",
                        lines=25
                    )
                    
                    # GPT-4o Prompt 优化区域
                    gr.Markdown("""
                    <div style="background: linear-gradient(135deg, #f6ffed 0%, #e6f7ff 100%); 
                                border: 1px solid #b7eb8f; border-radius: 10px; padding: 16px; margin-top: 16px;">
                        <div style="font-weight: 600; color: #52c41a; margin-bottom: 12px;">✨ GPT-4o Prompt优化</div>
                    </div>
                    """)
                    with gr.Row():
                        optimize_agent_select = gr.Dropdown(
                            label="选择Agent",
                            choices=["planner", "infer", "checker"],
                            value="planner"
                        )
                        optimize_btn = gr.Button("🚀 优化", variant="primary")
                    
                    # 操作按钮
                    with gr.Row():
                        validate_btn = gr.Button("🔍 解析并生成", variant="primary", size="lg")
                        save_btn = gr.Button("💾 保存配置", variant="secondary")
                    
                    upload_status = gr.Textbox(
                        label="状态",
                        interactive=False,
                        visible=True
                    )
                
                with gr.TabItem("分支/循环配置"):
                    gr.Markdown("""
                    <div style="background: #fffbe6; border: 1px solid #ffe58f; border-radius: 10px; 
                                padding: 16px; margin-bottom: 16px;">
                        <div style="display: flex; align-items: flex-start; gap: 12px;">
                            <span>⚠️</span>
                            <div>配置条件分支和循环，控制Agent执行流程</div>
                        </div>
                    </div>
                    """)
                    
                    with gr.Group():
                        gr.Markdown("**🔀 条件分支配置**")
                        branch_agent = gr.Dropdown(
                            label="在Agent后添加条件判断",
                            choices=["planner", "infer", "checker"]
                        )
                        branch_condition = gr.Textbox(
                            label="条件表达式",
                            placeholder="例如: state.verdict == 'pass'"
                        )
                        with gr.Row():
                            branch_true = gr.Dropdown(
                                label="条件为真时跳转",
                                choices=["继续执行下一个Agent", "跳转到: checker", "结束流程"]
                            )
                            branch_false = gr.Dropdown(
                                label="条件为假时跳转",
                                choices=["重试当前Agent", "跳转到: planner", "结束流程"]
                            )
                        add_branch_btn = gr.Button("➕ 添加分支")
                    
                    with gr.Group():
                        gr.Markdown("**🔄 循环配置**")
                        loop_type = gr.Dropdown(
                            label="循环类型",
                            choices=["固定次数循环", "条件循环 (while)", "直到满足条件 (do-while)"]
                        )
                        loop_range = gr.Dropdown(
                            label="循环范围",
                            choices=["选择要循环的Agent...", "planner → infer", "infer 单独"]
                        )
                        loop_condition = gr.Textbox(
                            label="退出条件",
                            placeholder="例如: state.verdict == 'pass' 或 迭代次数 >= 3"
                        )
                        add_loop_btn = gr.Button("➕ 添加循环")
        
        # 右侧：数据流可视化
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                            background: linear-gradient(to right, #fafafa, #ffffff);">
                    <div style="font-size: 16px; font-weight: 600;">数据流可视化</div>
                </div>
                <div style="padding: 24px;">
            """)
            
            # 可视化容器
            viz_container = gr.HTML(
                label="数据流图",
                value="""
                <div style="background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%); 
                            border: 2px dashed #d9d9d9; border-radius: 16px; padding: 32px; 
                            min-height: 300px; display: flex; align-items: center; justify-content: center;">
                    <div style="text-align: center; color: #8c8c8c;">
                        <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
                        <div>点击"解析并生成"查看数据流图</div>
                    </div>
                </div>
                """
            )
            
            # State 字段分析表格
            gr.Markdown("<div style='margin-top: 24px; font-weight: 600; margin-bottom: 16px;'>📊 State字段分析</div>")
            state_analysis_table = gr.Dataframe(
                headers=["State字段", "操作", "Agent"],
                value=[],
                interactive=False
            )
            
            # 校验结果
            gr.Markdown("<div style='margin-top: 24px; font-weight: 600; margin-bottom: 16px;'>✅ 校验结果</div>")
            validation_status = gr.Markdown("等待校验...")
            validation_errors = gr.Textbox(label="错误信息", lines=3, interactive=False)
            validation_warnings = gr.Textbox(label="警告信息", lines=2, interactive=False)
            execution_order = gr.Textbox(label="执行顺序", interactive=False)
            
            gr.Markdown("</div></div>")
    
    # 配置列表区域
    gr.Markdown("---")
    gr.Markdown("## 📋 已保存的配置")
    
    with gr.Row():
        with gr.Column():
            configs = db.get_all_system_configs()
            config_data = []
            for c in configs:
                config_data.append([
                    c.id,
                    c.name,
                    "✅ 有效" if c.is_valid else "❌ 无效",
                    c.agent_count,
                    c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ""
                ])
            
            config_table = gr.Dataframe(
                headers=["ID", "名称", "状态", "Agent数", "创建时间"],
                value=config_data if config_data else [["", "", "", "", ""]],
                interactive=False,
                wrap=True
            )
            
            with gr.Row():
                refresh_config_btn = gr.Button("🔄 刷新")
                view_config_btn = gr.Button("👁️ 查看详情")
                delete_config_btn = gr.Button("🗑️ 删除", variant="stop")
            
            config_id_input = gr.Number(label="配置 ID", precision=0)
        
        with gr.Column():
            gr.Markdown("### 配置详情")
            config_detail = gr.JSON(label="配置内容")
    
    # 事件处理函数
    def handle_file_upload(file_path):
        """处理文件上传"""
        if file_path is None:
            return "未选择文件", ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 验证是否为有效 JSON
            json.loads(content)
            
            # 从文件名提取配置名称
            file_name = os.path.basename(file_path)
            config_name = os.path.splitext(file_name)[0]
            
            return f"✅ 文件 '{file_name}' 上传成功", content
        except json.JSONDecodeError as e:
            return f"❌ JSON 解析错误: {str(e)}", ""
        except Exception as e:
            return f"❌ 读取文件失败: {str(e)}", ""
    
    def generate_agent_node(agent_id, model_name, status="pending", trainable=False):
        """生成 Agent 节点 HTML"""
        status_colors = {
            "pending": "#d9d9d9",
            "running": "#1890ff",
            "completed": "#52c41a"
        }
        status_icons = {
            "pending": "",
            "running": "●",
            "completed": "✓"
        }
        border_color = status_colors.get(status, "#d9d9d9")
        badge = ""
        if status != "pending":
            badge = f'''<div style="position: absolute; top: -10px; right: -10px; width: 24px; height: 24px; 
                        border-radius: 50%; display: flex; align-items: center; justify-content: center; 
                        font-size: 12px; color: white; border: 2px solid white; background: {border_color};">
                        {status_icons.get(status, "")}</div>'''
        
        trainable_badge = ""
        if trainable:
            trainable_badge = '''<div style="position: absolute; top: -10px; left: -10px; padding: 4px 10px; 
                                background: linear-gradient(135deg, #722ed1 0%, #531dab 100%); color: white; 
                                font-size: 10px; font-weight: 600; border-radius: 12px; border: 2px solid white;">
                                可训练</div>'''
        
        return f'''
        <div style="display: inline-flex; flex-direction: column; align-items: center; padding: 20px 28px; 
                    background: white; border: 2px solid {border_color}; border-radius: 16px; 
                    margin: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); position: relative; min-width: 160px;">
            {badge}
            {trainable_badge}
            <div style="font-weight: 600; font-size: 16px;">{agent_id}</div>
            <div style="font-size: 11px; color: #667eea; background: rgba(102,126,234,0.1); 
                        padding: 4px 10px; border-radius: 6px; margin-top: 8px;">{model_name}</div>
        </div>
        '''
    
    def generate_state_node(field_name, color="#52c41a"):
        """生成 State 节点 HTML"""
        return f'''
        <div style="display: inline-flex; flex-direction: column; align-items: center; padding: 16px 24px; 
                    background: #f6ffed; border: 2px solid {color}; border-radius: 12px; margin: 10px; min-width: 120px;">
            <div style="font-weight: 600; font-size: 13px; color: {color};">{field_name}</div>
        </div>
        '''
    
    def generate_connection_line():
        """生成连接线 HTML"""
        return '<div style="display: flex; align-items: center; color: #bfbfbf; font-size: 24px; margin: 0 20px;">→</div>'
    
    def validate_and_visualize(json_text):
        """校验配置并生成可视化"""
        if not json_text:
            return (
                "❌ 请输入 JSON 配置",
                "",
                "",
                "",
                "<div style='padding: 20px;'>请输入 JSON 配置</div>",
                []
            )
        
        try:
            result = validator.validate(json_text)
            
            status = "✅ **配置有效**" if result.is_valid else "❌ **配置无效**"
            errors = "\\n".join(result.errors) if result.errors else "无"
            warnings = "\\n".join(result.warnings) if result.warnings else "无"
            order = " → ".join(result.execution_order) if result.execution_order else "无法确定"
            
            # 生成可视化
            try:
                data = json.loads(json_text)
                viz_html = generate_viz_html(data, result.execution_order)
            except Exception as e:
                viz_html = f"<div style='padding: 20px; color: red;'>可视化生成失败: {str(e)}</div>"
            
            # 生成 State 分析表格
            state_data = generate_state_analysis(data)
            
            return status, errors, warnings, order, viz_html, state_data
        
        except Exception as e:
            return f"❌ 校验失败: {str(e)}", str(e), "", "", "<div style='padding: 20px;'>校验失败</div>", []
    
    def generate_viz_html(data, execution_order):
        """生成可视化 HTML"""
        if not execution_order:
            return "<div style='padding: 20px;'>无法生成可视化</div>"
        
        html_parts = ['<div style="background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%); '
                     'border: 2px dashed #d9d9d9; border-radius: 16px; padding: 32px; overflow-x: auto;">']
        html_parts.append('<div style="display: flex; align-items: center; justify-content: center; flex-wrap: wrap;">')
        
        # 添加用户输入节点
        html_parts.append(generate_state_node("📥 user_request", "#1890ff"))
        html_parts.append(generate_connection_line())
        
        # 构建 agent 信息映射
        agent_map = {a["agent_id"]: a for a in data if isinstance(a, dict)}
        
        for i, agent_id in enumerate(execution_order):
            agent = agent_map.get(agent_id, {})
            model_name = agent.get("model", {}).get("name_or_path", "Unknown")
            # 简化模型名称
            if len(model_name) > 20:
                model_name = model_name.split("-")[-1] if "-" in model_name else model_name[:20]
            
            html_parts.append(generate_agent_node(agent_id, model_name))
            
            # 如果不是最后一个，添加连接线和 state 节点
            if i < len(execution_order) - 1:
                html_parts.append(generate_connection_line())
                # 获取输出字段
                outputs = agent.get("output", [])
                if outputs:
                    output_key = outputs[0].get("key", "output")
                    html_parts.append(generate_state_node(f"state.{output_key}"))
                    html_parts.append(generate_connection_line())
        
        html_parts.append('</div>')
        html_parts.append('</div>')
        
        return "".join(html_parts)
    
    def generate_state_analysis(data):
        """生成 State 字段分析"""
        state_ops = {}
        
        for agent in data:
            if not isinstance(agent, dict):
                continue
            agent_id = agent.get("agent_id", "unknown")
            
            # 读取操作
            for inp in agent.get("input", []):
                key = inp.get("key", "")
                if key not in state_ops:
                    state_ops[key] = {"read": [], "write": []}
                state_ops[key]["read"].append(agent_id)
            
            # 写入操作
            for out in agent.get("output", []):
                key = out.get("key", "")
                if key not in state_ops:
                    state_ops[key] = {"read": [], "write": []}
                state_ops[key]["write"].append(agent_id)
        
        # 生成表格数据
        table_data = []
        for field, ops in state_ops.items():
            if ops["read"]:
                table_data.append([field, "READ", ", ".join(ops["read"])])
            if ops["write"]:
                table_data.append([field, "WRITE", ", ".join(ops["write"])])
        
        return table_data if table_data else [["", "", ""]]
    
    def save_config(json_text):
        """保存配置"""
        if not json_text:
            return "❌ 请提供 JSON 配置"
        
        try:
            # 先校验
            result = validator.validate(json_text)
            
            # 解析 JSON
            config_data = json.loads(json_text)
            
            # 使用第一个 agent_id 作为配置名称
            config_name = config_data[0].get("agent_id", "config") + "_system" if config_data else "unnamed_config"
            
            # 保存到数据库
            config = db.create_system_config(
                name=config_name,
                description="",
                config_json=config_data
            )
            
            # 更新校验状态
            db.update_config_validation(
                config_id=config.id,
                is_valid=result.is_valid,
                errors="\\n".join(result.errors) if result.errors else None,
                execution_order=result.execution_order
            )
            
            status = "有效" if result.is_valid else "无效"
            return f"✅ 配置 '{config_name}' 已保存！ID: {config.id}, 状态: {status}"
        
        except json.JSONDecodeError as e:
            return f"❌ JSON 解析错误: {str(e)}"
        except Exception as e:
            return f"❌ 保存失败: {str(e)}"
    
    def refresh_configs():
        """刷新配置列表"""
        configs = db.get_all_system_configs()
        config_data = []
        for c in configs:
            config_data.append([
                c.id,
                c.name,
                "✅ 有效" if c.is_valid else "❌ 无效",
                c.agent_count,
                c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ""
            ])
        return config_data if config_data else [["", "", "", "", ""]]
    
    def view_config(config_id):
        """查看配置详情"""
        if not config_id:
            return {"error": "请提供配置 ID"}
        
        config = db.get_system_config(int(config_id))
        if not config:
            return {"error": "配置不存在"}
        
        return {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "is_valid": config.is_valid,
            "agent_count": config.agent_count,
            "execution_order": config.execution_order,
            "config": config.config_json
        }
    
    def delete_config(config_id):
        """删除配置"""
        if not config_id:
            return "❌ 请提供配置 ID"
        
        success = db.delete_system_config(int(config_id))
        if success:
            return f"✅ 配置 ID {config_id} 已删除"
        else:
            return f"❌ 配置 ID {config_id} 不存在"
    
    # 绑定事件
    config_file_upload.change(
        fn=handle_file_upload,
        inputs=config_file_upload,
        outputs=[upload_status, json_editor]
    )
    
    validate_btn.click(
        fn=validate_and_visualize,
        inputs=json_editor,
        outputs=[validation_status, validation_errors, validation_warnings, execution_order, viz_container, state_analysis_table]
    )
    
    save_btn.click(
        fn=save_config,
        inputs=json_editor,
        outputs=upload_status
    )
    
    refresh_config_btn.click(
        fn=refresh_configs,
        outputs=config_table
    )
    
    view_config_btn.click(
        fn=view_config,
        inputs=config_id_input,
        outputs=config_detail
    )
    
    delete_config_btn.click(
        fn=delete_config,
        inputs=config_id_input,
        outputs=upload_status
    )
