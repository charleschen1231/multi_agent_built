# web/app.py
import gradio as gr
from web.pages.dashboard import create_dashboard_page
from web.pages.data_manager import create_data_manager_page
from web.pages.json_config import create_json_config_page
from web.pages.execution_flow import create_execution_flow_page
from web.pages.training import create_training_page
from web.pages.trajectory import create_trajectory_page
from database.db_manager import DatabaseManager


class AppState:
    """应用全局状态"""
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.current_config_id = None
        self.current_dataset_id = None
        self.current_execution_id = None


def create_app() -> gr.Blocks:
    """创建 Gradio 应用 - V6 风格"""
    
    # 初始化全局状态
    app_state = AppState()
    
    # 创建主题
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="gray",
        neutral_hue="gray",
        font=["Inter", "sans-serif"]
    )
    
    with gr.Blocks(theme=theme, title="Multi-Agent System Builder", css="""
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            padding: 20px 0;
        }
        .nav-button {
            width: 100%;
        }
    """) as app:
        
        # 状态存储
        current_page = gr.State("dashboard")
        
        # 头部 - V6 风格
        gr.Markdown("""
        <div style="background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%); 
                    color: white; padding: 16px 32px; margin: -20px -20px 20px -20px;
                    display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%); 
                            border-radius: 10px; display: flex; align-items: center; justify-content: center; 
                            font-size: 22px; box-shadow: 0 4px 15px rgba(0,212,255,0.3);">🤖</div>
                <span style="font-size: 20px; font-weight: 600;">Multi-Agent System Builder</span>
            </div>
        </div>
        """)
        
        # 导航栏 - V6 风格
        with gr.Row():
            with gr.Column(scale=1):
                dashboard_btn = gr.Button("📊 仪表盘", variant="primary", elem_classes=["nav-button"])
            with gr.Column(scale=1):
                config_btn = gr.Button("🔧 系统构建器", elem_classes=["nav-button"])
            with gr.Column(scale=1):
                data_btn = gr.Button("📁 数据资产", elem_classes=["nav-button"])
            with gr.Column(scale=1):
                execution_btn = gr.Button("▶️ 执行中心", elem_classes=["nav-button"])
            with gr.Column(scale=1):
                trajectory_btn = gr.Button("📊 轨迹追溯", elem_classes=["nav-button"])
            with gr.Column(scale=1):
                training_btn = gr.Button("🎓 训练工厂", elem_classes=["nav-button"])
        
        gr.Markdown("---")
        
        # 页面内容容器
        with gr.Column() as page_container:
            
            # 仪表盘页面
            with gr.Column(visible=True) as dashboard_page:
                create_dashboard_page(app_state)
            
            # 系统构建器页面 (原配置管理)
            with gr.Column(visible=False) as json_config_page:
                create_json_config_page(app_state)
            
            # 数据资产页面
            with gr.Column(visible=False) as data_manager_page:
                create_data_manager_page(app_state)
            
            # 执行中心页面
            with gr.Column(visible=False) as execution_flow_page:
                create_execution_flow_page(app_state)
            
            # 轨迹追溯页面 (新增)
            with gr.Column(visible=False) as trajectory_page:
                create_trajectory_page(app_state)
            
            # 训练工厂页面
            with gr.Column(visible=False) as training_page:
                create_training_page(app_state)
        
        # 底部
        gr.Markdown(
            """
            ---
            <center><small>Multi-Agent System Builder | 基于 JSON 配置的多智能体系统搭建与训练平台</small></center>
            """
        )
        
        # 页面切换函数
        def switch_page(page_name):
            return {
                dashboard_page: gr.Column(visible=(page_name == "dashboard")),
                json_config_page: gr.Column(visible=(page_name == "config")),
                data_manager_page: gr.Column(visible=(page_name == "data")),
                execution_flow_page: gr.Column(visible=(page_name == "execution")),
                trajectory_page: gr.Column(visible=(page_name == "trajectory")),
                training_page: gr.Column(visible=(page_name == "training")),
                dashboard_btn: gr.Button(variant="primary" if page_name == "dashboard" else "secondary"),
                config_btn: gr.Button(variant="primary" if page_name == "config" else "secondary"),
                data_btn: gr.Button(variant="primary" if page_name == "data" else "secondary"),
                execution_btn: gr.Button(variant="primary" if page_name == "execution" else "secondary"),
                trajectory_btn: gr.Button(variant="primary" if page_name == "trajectory" else "secondary"),
                training_btn: gr.Button(variant="primary" if page_name == "training" else "secondary"),
            }
        
        # 绑定导航按钮
        dashboard_btn.click(
            fn=lambda: switch_page("dashboard"),
            outputs=[dashboard_page, json_config_page, data_manager_page, 
                    execution_flow_page, trajectory_page, training_page,
                    dashboard_btn, config_btn, data_btn, execution_btn, trajectory_btn, training_btn]
        )
        
        config_btn.click(
            fn=lambda: switch_page("config"),
            outputs=[dashboard_page, json_config_page, data_manager_page,
                    execution_flow_page, trajectory_page, training_page,
                    dashboard_btn, config_btn, data_btn, execution_btn, trajectory_btn, training_btn]
        )
        
        data_btn.click(
            fn=lambda: switch_page("data"),
            outputs=[dashboard_page, json_config_page, data_manager_page,
                    execution_flow_page, trajectory_page, training_page,
                    dashboard_btn, config_btn, data_btn, execution_btn, trajectory_btn, training_btn]
        )
        
        execution_btn.click(
            fn=lambda: switch_page("execution"),
            outputs=[dashboard_page, json_config_page, data_manager_page,
                    execution_flow_page, trajectory_page, training_page,
                    dashboard_btn, config_btn, data_btn, execution_btn, trajectory_btn, training_btn]
        )
        
        trajectory_btn.click(
            fn=lambda: switch_page("trajectory"),
            outputs=[dashboard_page, json_config_page, data_manager_page,
                    execution_flow_page, trajectory_page, training_page,
                    dashboard_btn, config_btn, data_btn, execution_btn, trajectory_btn, training_btn]
        )
        
        training_btn.click(
            fn=lambda: switch_page("training"),
            outputs=[dashboard_page, json_config_page, data_manager_page,
                    execution_flow_page, trajectory_page, training_page,
                    dashboard_btn, config_btn, data_btn, execution_btn, trajectory_btn, training_btn]
        )
    
    return app


def launch_app(server_name: str = "0.0.0.0", server_port: int = 7860, share: bool = False):
    """启动应用"""
    app = create_app()
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        show_error=True
    )


if __name__ == "__main__":
    launch_app()
