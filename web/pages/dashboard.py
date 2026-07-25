# web/pages/dashboard.py
import gradio as gr


def create_dashboard_page(app_state):
    """创建仪表盘页面 - V6 风格"""
    
    db = app_state.db_manager
    
    # 获取统计数据
    def get_stats():
        datasets = db.get_all_datasets()
        configs = db.get_all_system_configs()
        executions = db.get_all_executions()
        training_jobs = db.get_all_training_jobs()
        
        # 获取轨迹数据数量
        trajectory_count = 0
        for config in configs:
            trajectory_count += len(db.get_generated_data_by_config(config.id))
        
        return {
            'dataset_count': len(datasets),
            'config_count': len(configs),
            'valid_config_count': len([c for c in configs if c.is_valid]),
            'execution_count': len(executions),
            'training_count': len(training_jobs),
            'trajectory_count': trajectory_count,
            'running_trainings': len([j for j in training_jobs if j.status == 'running'])
        }
    
    stats = get_stats()
    
    # 页面头部
    gr.Markdown("""
    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
        <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                    font-size: 24px; color: white;">📊</div>
        <div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 600;">系统概览</h1>
            <p style="margin: 0; font-size: 14px; color: #8c8c8c;">Multi-Agent System Builder 仪表盘</p>
        </div>
    </div>
    """)
    
    # 统计卡片行 - V6 风格
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown(f"""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #1890ff; margin-bottom: 4px;">{stats['config_count']}</div>
                <div style="font-size: 14px; color: #8c8c8c;">系统配置</div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown(f"""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #52c41a; margin-bottom: 4px;">{stats['valid_config_count']}</div>
                <div style="font-size: 14px; color: #8c8c8c;">有效配置</div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown(f"""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #722ed1; margin-bottom: 4px;">{stats['dataset_count']}</div>
                <div style="font-size: 14px; color: #8c8c8c;">数据集</div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown(f"""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #fa8c16; margin-bottom: 4px;">{stats['trajectory_count']}</div>
                <div style="font-size: 14px; color: #8c8c8c;">执行轨迹</div>
            </div>
            """)
    
    # 快捷操作 - V6 风格卡片
    gr.Markdown("---")
    gr.Markdown("## 🚀 快捷操作")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; padding: 24px; height: 100%;">
                <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                            font-size: 24px; color: white; margin-bottom: 16px;">🔧</div>
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">系统构建器</div>
                <div style="font-size: 13px; color: #8c8c8c; line-height: 1.6;">
                    上传 JSON 配置文件，自动解析并生成数据流可视化
                </div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; padding: 24px; height: 100%;">
                <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%); 
                            border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                            font-size: 24px; color: white; margin-bottom: 16px;">📁</div>
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">数据资产</div>
                <div style="font-size: 13px; color: #8c8c8c; line-height: 1.6;">
                    管理数据集、模型权重和训练数据
                </div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; padding: 24px; height: 100%;">
                <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%); 
                            border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                            font-size: 24px; color: white; margin-bottom: 16px;">▶️</div>
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">执行中心</div>
                <div style="font-size: 13px; color: #8c8c8c; line-height: 1.6;">
                    批量推理与实时监控执行流程
                </div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; padding: 24px; height: 100%;">
                <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #722ed1 0%, #531dab 100%); 
                            border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                            font-size: 24px; color: white; margin-bottom: 16px;">🎓</div>
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">训练工厂</div>
                <div style="font-size: 13px; color: #8c8c8c; line-height: 1.6;">
                    System-level SFT / GRPO / DPO 训练
                </div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; padding: 24px; height: 100%;">
                <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%); 
                            border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                            font-size: 24px; color: white; margin-bottom: 16px;">📊</div>
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">轨迹追溯</div>
                <div style="font-size: 13px; color: #8c8c8c; line-height: 1.6;">
                    查询、分析与导出执行轨迹
                </div>
            </div>
            """)
    
    # 最近活动 - V6 风格
    gr.Markdown("---")
    gr.Markdown("## 📋 最近活动")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                            background: linear-gradient(to right, #fafafa, #ffffff);">
                    <div style="font-size: 16px; font-weight: 600;">最近的配置</div>
                </div>
                <div style="padding: 24px;">
            """)
            
            configs = db.get_all_system_configs()[:5]
            if configs:
                for c in configs:
                    status_badge = "✅ 有效" if c.is_valid else "❌ 无效"
                    status_color = "#52c41a" if c.is_valid else "#ff4d4f"
                    gr.Markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; 
                                padding: 12px 0; border-bottom: 1px solid #f0f0f0;">
                        <div>
                            <div style="font-weight: 500;">{c.name}</div>
                            <div style="font-size: 12px; color: #8c8c8c;">{c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ''}</div>
                        </div>
                        <span style="background: {status_color}20; color: {status_color}; padding: 4px 10px; 
                                     border-radius: 6px; font-size: 12px;">{status_badge}</span>
                    </div>
                    """)
            else:
                gr.Markdown("<div style='color: #8c8c8c; padding: 20px 0;'>暂无配置</div>")
            
            gr.Markdown("</div></div>")
        
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                            background: linear-gradient(to right, #fafafa, #ffffff);">
                    <div style="font-size: 16px; font-weight: 600;">最近的执行</div>
                </div>
                <div style="padding: 24px;">
            """)
            
            executions = db.get_all_executions()[:5]
            if executions:
                for e in executions:
                    status_colors = {
                        'completed': '#52c41a',
                        'running': '#1890ff',
                        'failed': '#ff4d4f',
                        'pending': '#8c8c8c'
                    }
                    status_color = status_colors.get(e.status, '#8c8c8c')
                    
                    config_name = ""
                    if e.config_id:
                        config = db.get_system_config(e.config_id)
                        config_name = config.name if config else f"Config {e.config_id}"
                    
                    gr.Markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; 
                                padding: 12px 0; border-bottom: 1px solid #f0f0f0;">
                        <div>
                            <div style="font-weight: 500;">{config_name}</div>
                            <div style="font-size: 12px; color: #8c8c8c;">{e.created_at.strftime('%Y-%m-%d %H:%M') if e.created_at else ''}</div>
                        </div>
                        <span style="background: {status_color}20; color: {status_color}; padding: 4px 10px; 
                                     border-radius: 6px; font-size: 12px; text-transform: uppercase;">{e.status}</span>
                    </div>
                    """)
            else:
                gr.Markdown("<div style='color: #8c8c8c; padding: 20px 0;'>暂无执行记录</div>")
            
            gr.Markdown("</div></div>")
        
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                            background: linear-gradient(to right, #fafafa, #ffffff);">
                    <div style="font-size: 16px; font-weight: 600;">最近的训练任务</div>
                </div>
                <div style="padding: 24px;">
            """)
            
            jobs = db.get_all_training_jobs()[:5]
            if jobs:
                for j in jobs:
                    type_colors = {
                        'sft': '#fa8c16',
                        'dpo': '#13c2c2',
                        'grpo': '#722ed1'
                    }
                    type_color = type_colors.get(j.type, '#8c8c8c')
                    
                    status_colors = {
                        'completed': '#52c41a',
                        'running': '#1890ff',
                        'failed': '#ff4d4f',
                        'pending': '#8c8c8c'
                    }
                    status_color = status_colors.get(j.status, '#8c8c8c')
                    
                    gr.Markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; 
                                padding: 12px 0; border-bottom: 1px solid #f0f0f0;">
                        <div>
                            <div style="font-weight: 500;">{j.name}</div>
                            <div style="font-size: 12px; color: #8c8c8c;">{j.created_at.strftime('%Y-%m-%d %H:%M') if j.created_at else ''}</div>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <span style="background: {type_color}20; color: {type_color}; padding: 4px 10px; 
                                         border-radius: 6px; font-size: 12px; text-transform: uppercase;">{j.type}</span>
                            <span style="background: {status_color}20; color: {status_color}; padding: 4px 10px; 
                                         border-radius: 6px; font-size: 12px; text-transform: uppercase;">{j.status}</span>
                        </div>
                    </div>
                    """)
            else:
                gr.Markdown("<div style='color: #8c8c8c; padding: 20px 0;'>暂无训练任务</div>")
            
            gr.Markdown("</div></div>")
    
    # 刷新按钮
    refresh_btn = gr.Button("🔄 刷新数据", variant="secondary")
    refresh_status = gr.Textbox(label="状态", visible=False)
    
    def refresh_dashboard():
        return "数据已刷新"
    
    refresh_btn.click(fn=refresh_dashboard, outputs=refresh_status)
