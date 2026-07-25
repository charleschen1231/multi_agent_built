# web/components/common.py
import gradio as gr


def create_header():
    """创建页面头部"""
    with gr.Row():
        with gr.Column():
            gr.Markdown(
                """
                # 🤖 Multi-Agent System Builder
                ## 多智能体系统构建与训练平台
                """
            )


def create_footer():
    """创建页面底部"""
    gr.Markdown(
        """
        ---
        **Multi-Agent System Builder** | 基于 JSON 配置的多智能体系统搭建与训练平台
        """
    )


def create_navigation():
    """创建导航栏"""
    with gr.Row():
        with gr.Column(scale=1):
            dashboard_btn = gr.Button("📊 仪表盘", variant="secondary")
        with gr.Column(scale=1):
            data_btn = gr.Button("📁 数据管理", variant="secondary")
        with gr.Column(scale=1):
            config_btn = gr.Button("⚙️ 配置管理", variant="secondary")
        with gr.Column(scale=1):
            execution_btn = gr.Button("▶️ 执行流程", variant="secondary")
        with gr.Column(scale=1):
            training_btn = gr.Button("🎯 训练管理", variant="secondary")
    
    return dashboard_btn, data_btn, config_btn, execution_btn, training_btn


def create_status_indicator(status: str, message: str = ""):
    """创建状态指示器"""
    colors = {
        'success': 'green',
        'error': 'red',
        'warning': 'orange',
        'info': 'blue',
        'pending': 'gray'
    }
    
    color = colors.get(status, 'gray')
    
    icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'pending': '⏳'
    }
    
    icon = icons.get(status, '•')
    
    return gr.Markdown(f"<span style='color: {color}; font-size: 16px;'>{icon} {message}</span>")


def format_json_display(data: dict) -> str:
    """格式化 JSON 显示"""
    import json
    return f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"


def create_info_card(title: str, content: str, icon: str = "📋"):
    """创建信息卡片"""
    return gr.Markdown(f"""
    ### {icon} {title}
    
    {content}
    """)


def create_stat_card(label: str, value: str, description: str = ""):
    """创建统计卡片"""
    return gr.Column([
        gr.Markdown(f"**{label}**"),
        gr.Markdown(f"<h2 style='margin: 0;'>{value}</h2>"),
        gr.Markdown(f"<small>{description}</small>") if description else gr.Markdown("")
    ])
