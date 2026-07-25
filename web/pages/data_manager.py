# web/pages/data_manager.py
import os
import json
import gradio as gr
from datetime import datetime
import hashlib


def generate_dataset_table(data):
    """生成数据集表格 HTML"""
    if not data:
        return "<div style='padding: 20px; color: #8c8c8c;'>暂无数据集</div>"
    
    html = """
    <table style="width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px;">
        <thead>
            <tr style="background: #fafafa;">
                <th style="padding: 14px 16px; text-align: left; font-weight: 600;">ID</th>
                <th style="padding: 14px 16px; text-align: left; font-weight: 600;">名称</th>
                <th style="padding: 14px 16px; text-align: left; font-weight: 600;">类型</th>
                <th style="padding: 14px 16px; text-align: left; font-weight: 600;">样本数</th>
                <th style="padding: 14px 16px; text-align: left; font-weight: 600;">状态</th>
                <th style="padding: 14px 16px; text-align: left; font-weight: 600;">操作</th>
            </tr>
        </thead>
        <tbody>
    """
    for row in data:
        html += "<tr style='border-bottom: 1px solid #f0f0f0;'>"
        for cell in row:
            html += f'<td style="padding: 14px 16px; border-bottom: 1px solid #f0f0f0;">{cell}</td>'
        html += "</tr>"
    html += "</tbody></table>"
    return html


def compute_content_hash(records):
    """计算数据集内容的哈希值，用于去重"""
    content_str = json.dumps(records, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content_str.encode('utf-8')).hexdigest()


def create_data_manager_page(app_state):
    """创建数据管理页面 - V6 风格"""
    
    db = app_state.db_manager
    
    # 页面头部
    gr.Markdown("""
    <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
        <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%); 
                    border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                    font-size: 24px; color: white;">📁</div>
        <div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 600;">数据资产</h1>
            <p style="margin: 0; font-size: 14px; color: #8c8c8c;">数据集与模型权重管理</p>
        </div>
    </div>
    """)
    
    # 统计卡片
    with gr.Row():
        with gr.Column(scale=1):
            dataset_count = len(db.get_all_datasets())
            gr.Markdown(f"""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #1890ff; margin-bottom: 4px;">{dataset_count}</div>
                <div style="font-size: 14px; color: #8c8c8c;">数据集</div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #722ed1; margin-bottom: 4px;">0</div>
                <div style="font-size: 14px; color: #8c8c8c;">模型权重</div>
            </div>
            """)
        with gr.Column(scale=1):
            gr.Markdown("""
            <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #e8e8e8;">
                <div style="font-size: 32px; font-weight: 700; color: #52c41a; margin-bottom: 4px;">--</div>
                <div style="font-size: 14px; color: #8c8c8c;">存储使用</div>
            </div>
            """)
    
    # 主内容区
    with gr.Tabs():
        # 数据集列表 Tab
        with gr.TabItem("📊 数据集列表"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("""
                    <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                        <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                                    background: linear-gradient(to right, #fafafa, #ffffff);">
                            <div style="font-size: 16px; font-weight: 600;">数据集列表</div>
                        </div>
                        <div style="padding: 0;">
                    """)
                    
                    # 数据集列表
                    datasets = db.get_all_datasets()
                    dataset_data = []
                    dataset_id_map = {}  # 用于存储ID到索引的映射
                    for idx, d in enumerate(datasets):
                        type_tag = {
                            "test": "<span style='background: #e6f7ff; color: #1890ff; padding: 4px 10px; border-radius: 6px; font-size: 12px;'>测试</span>",
                            "train": "<span style='background: #f6ffed; color: #52c41a; padding: 4px 10px; border-radius: 6px; font-size: 12px;'>训练</span>",
                            "validation": "<span style='background: #fff7e6; color: #fa8c16; padding: 4px 10px; border-radius: 6px; font-size: 12px;'>验证</span>"
                        }.get(d.type, d.type)
                        
                        status_tag = "<span style='background: #f6ffed; color: #52c41a; padding: 4px 10px; border-radius: 6px; font-size: 12px;'>✓ 就绪</span>"
                        
                        dataset_data.append([
                            d.id,
                            f"<b>{d.name}</b>",
                            type_tag,
                            d.record_count,
                            status_tag,
                            d.id  # 存储ID用于查看按钮
                        ])
                        dataset_id_map[d.id] = idx
                    
                    dataset_table = gr.Dataframe(
                        value=dataset_data if dataset_data else [],
                        headers=["ID", "名称", "类型", "样本数", "状态", "操作"],
                        datatype=["number", "markdown", "markdown", "number", "markdown", "number"],
                        interactive=False,
                        wrap=True
                    )
                    
                    with gr.Row():
                        refresh_dataset_btn = gr.Button("🔄 刷新")
                        upload_new_btn = gr.Button("📤 上传新数据集", variant="primary")
                    
                    # 数据集详情显示区域
                    dataset_detail = gr.JSON(label="数据集详情", visible=False)
                    dataset_preview = gr.Dataframe(label="数据预览", visible=False)
                    
                    gr.Markdown("</div></div>")
        
        # 上传数据集 Tab
        with gr.TabItem("📤 上传数据集"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("""
                    <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden;">
                        <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; 
                                    background: linear-gradient(to right, #fafafa, #ffffff);">
                            <div style="font-size: 16px; font-weight: 600;">上传新数据集</div>
                        </div>
                        <div style="padding: 24px;">
                    """)
                    
                    dataset_name = gr.Textbox(
                        label="数据集名称",
                        placeholder="输入数据集名称"
                    )
                    dataset_desc = gr.Textbox(
                        label="描述",
                        placeholder="输入数据集描述（可选）",
                        lines=2
                    )
                    dataset_type = gr.Dropdown(
                        label="数据集类型",
                        choices=["test", "train", "validation"],
                        value="test"
                    )
                    dataset_file = gr.File(
                        label="上传数据文件 (JSON/JSONL)",
                        file_types=[".json", ".jsonl"]
                    )
                    
                    upload_btn = gr.Button("📤 上传数据集", variant="primary")
                    upload_status = gr.Textbox(label="上传状态", interactive=False)
                    
                    gr.Markdown("</div></div>")
                
                with gr.Column(scale=1):
                    gr.Markdown("""
                    <div style="background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 12px; padding: 20px;">
                        <div style="font-weight: 600; color: #52c41a; margin-bottom: 12px;">📋 数据格式说明</div>
                        <div style="font-size: 13px; color: #595959; line-height: 1.8;">
                            <p><b>JSON格式：</b>标准JSON数组，每个元素是一个样本</p>
                            <p><b>JSONL格式：</b>每行一个JSON对象</p>
                            <p><b>必需字段：</b></p>
                            <ul>
                                <li>user_request: 用户输入</li>
                                <li>ground truth字段（用于训练）</li>
                            </ul>
                        </div>
                    </div>
                    """)
        
        # 数据集预览 Tab
        with gr.TabItem("👁️ 数据预览"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 选择数据集")
                    preview_dataset_id = gr.Dropdown(
                        label="数据集",
                        choices=[(f"{d.name} (ID: {d.id})", d.id) for d in db.get_all_datasets()],
                        value=None
                    )
                    preview_btn = gr.Button("👁️ 预览数据", variant="primary")
                
                with gr.Column(scale=2):
                    gr.Markdown("### 数据预览")
                    preview_output = gr.JSON(label="数据内容")
                    preview_stats = gr.JSON(label="统计信息")
    
    # 事件处理函数
    def upload_dataset(name, desc, dtype, file):
        if not name or not file:
            return "❌ 请提供数据集名称和文件"
        
        try:
            # 读取文件
            with open(file.name, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 JSON/JSONL
            if file.name.endswith('.jsonl'):
                records = [json.loads(line) for line in content.strip().split('\n') if line.strip()]
                file_format = 'jsonl'
            else:
                data = json.loads(content)
                records = data if isinstance(data, list) else [data]
                file_format = 'json'
            
            # 计算内容哈希值用于去重
            content_hash = compute_content_hash(records)
            
            # 检查是否已存在相同内容的数据集
            all_datasets = db.get_all_datasets()
            for existing_dataset in all_datasets:
                try:
                    if os.path.exists(existing_dataset.file_path):
                        with open(existing_dataset.file_path, 'r', encoding='utf-8') as ef:
                            existing_content = ef.read()
                            if existing_dataset.file_format == 'jsonl':
                                existing_records = [json.loads(line) for line in existing_content.strip().split('\n') if line.strip()]
                            else:
                                existing_data = json.loads(existing_content)
                                existing_records = existing_data if isinstance(existing_data, list) else [existing_data]
                            
                            existing_hash = compute_content_hash(existing_records)
                            if existing_hash == content_hash:
                                return f"⚠️ 数据集 '{name}' 已存在相同内容的数据集 (ID: {existing_dataset.id}, 名称: {existing_dataset.name})，已去重未保存新数据集。"
                except Exception:
                    continue
            
            # 保存到上传目录
            upload_dir = "data/uploads"
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, f"{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file_format}")
            
            with open(save_path, 'w', encoding='utf-8') as f:
                if file_format == 'jsonl':
                    for r in records:
                        f.write(json.dumps(r, ensure_ascii=False) + '\n')
                else:
                    json.dump(records, f, ensure_ascii=False, indent=2)
            
            # 创建数据库记录
            dataset = db.create_dataset(
                name=name,
                description=desc,
                type=dtype,
                file_path=save_path,
                file_format=file_format,
                record_count=len(records)
            )
            
            return f"✅ 数据集 '{name}' 上传成功！ID: {dataset.id}, 记录数: {len(records)}"
        
        except Exception as e:
            return f"❌ 上传失败: {str(e)}"
    
    def refresh_datasets():
        """刷新数据集列表"""
        datasets = db.get_all_datasets()
        dataset_data = []
        for d in datasets:
            type_tag = {
                "test": "<span style='background: #e6f7ff; color: #1890ff; padding: 4px 10px; border-radius: 6px; font-size: 12px;'>测试</span>",
                "train": "<span style='background: #f6ffed; color: #52c41a; padding: 4px 10px; border-radius: 6px; font-size: 12px;'>训练</span>",
                "validation": "<span style='background: #fff7e6; color: #fa8c16; padding: 4px 10px; border-radius: 6px; font-size: 12px;'>验证</span>"
            }.get(d.type, d.type)
            
            status_tag = "<span style='background: #f6ffed; color: #52c41a; padding: 4px 10px; border-radius: 6px; font-size: 12px;'>✓ 就绪</span>"
            
            dataset_data.append([
                d.id,
                f"<b>{d.name}</b>",
                type_tag,
                d.record_count,
                status_tag,
                d.id  # 存储ID用于查看
            ])
        
        return dataset_data if dataset_data else []
    
    def on_dataset_select(evt: gr.SelectData):
        """处理数据集表格选中事件"""
        try:
            # 获取选中的行数据
            selected_row = evt.index[0] if hasattr(evt, 'index') and isinstance(evt.index, (list, tuple)) else None
            if selected_row is None:
                return None, None, False, False
            
            # 获取数据集ID（在最后一列）
            datasets = db.get_all_datasets()
            if selected_row < len(datasets):
                dataset = datasets[selected_row]
                
                # 读取数据预览
                preview_data = []
                try:
                    with open(dataset.file_path, 'r', encoding='utf-8') as f:
                        if dataset.file_format == 'jsonl':
                            for i, line in enumerate(f):
                                if i >= 5:  # 预览前5条
                                    break
                                preview_data.append(json.loads(line))
                        else:
                            data = json.load(f)
                            preview_data = data[:5] if isinstance(data, list) else [data]
                except Exception as e:
                    preview_data = [{"error": str(e)}]
                
                detail = {
                    "数据集信息": {
                        "ID": dataset.id,
                        "名称": dataset.name,
                        "类型": dataset.type,
                        "描述": dataset.description or "无",
                        "样本数": dataset.record_count,
                        "文件格式": dataset.file_format,
                        "创建时间": dataset.created_at.strftime("%Y-%m-%d %H:%M:%S") if dataset.created_at else "-"
                    }
                }
                
                # 转换预览数据为表格格式
                if preview_data and len(preview_data) > 0:
                    # 获取所有可能的列
                    all_keys = set()
                    for record in preview_data:
                        if isinstance(record, dict):
                            all_keys.update(record.keys())
                    columns = sorted(all_keys)
                    
                    # 构建表格数据
                    table_data = []
                    for record in preview_data:
                        if isinstance(record, dict):
                            row = []
                            for key in columns:
                                val = record.get(key, "")
                                # 截断长文本
                                val_str = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
                                if len(val_str) > 100:
                                    val_str = val_str[:100] + "..."
                                row.append(val_str)
                            table_data.append(row)
                        else:
                            table_data.append([str(record)])
                    
                    return detail, gr.Dataframe(value=table_data, headers=columns), True, True
                
                return detail, None, True, False
            
            return None, None, False, False
        except Exception as e:
            return {"error": str(e)}, None, True, False
    
    def preview_dataset(dataset_id):
        if not dataset_id:
            return {"error": "请提供数据集 ID"}, {}
        
        dataset = db.get_dataset(int(dataset_id))
        if not dataset:
            return {"error": "数据集不存在"}, {}
        
        try:
            with open(dataset.file_path, 'r', encoding='utf-8') as f:
                if dataset.file_format == 'jsonl':
                    records = [json.loads(line) for line in f.readlines()[:5]]  # 预览前5条
                else:
                    records = json.load(f)[:5]
            
            stats = {
                "dataset_info": {
                    "id": dataset.id,
                    "name": dataset.name,
                    "type": dataset.type,
                    "record_count": dataset.record_count,
                    "file_format": dataset.file_format
                }
            }
            
            return records, stats
        except Exception as e:
            return {"error": str(e)}, {}
    
    # 绑定事件
    upload_btn.click(
        fn=upload_dataset,
        inputs=[dataset_name, dataset_desc, dataset_type, dataset_file],
        outputs=upload_status
    )
    
    refresh_dataset_btn.click(
        fn=refresh_datasets,
        outputs=dataset_table
    )
    
    # 数据集表格选中事件 - 点击查看数据
    dataset_table.select(
        fn=on_dataset_select,
        outputs=[dataset_detail, dataset_preview, dataset_detail, dataset_preview]
    )
    
    preview_btn.click(
        fn=preview_dataset,
        inputs=preview_dataset_id,
        outputs=[preview_output, preview_stats]
    )
