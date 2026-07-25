#!/usr/bin/env python3
"""
Multi-Agent System Builder - Streamlit 版本
"""

import streamlit as st

# 页面配置 - 必须在最前面
st.set_page_config(
    page_title="Multi-Agent System Builder",
    page_icon="🤖",
    layout="wide"
)

import json
import os
from dotenv import load_dotenv
load_dotenv()

from database.db_manager import DatabaseManager
from spec.system_spec import SystemSpec
from core.trajectory_generator import TrajectoryGenerator
from core.json_validator import JSONValidator
from graphviz import Digraph

# 初始化数据库
@st.cache(allow_output_mutation=True)
def get_db():
    return DatabaseManager()

db = get_db()

# 生成流程图函数
def generate_flowchart(config_json: list, user_input: str = "用户输入"):
    """根据配置生成流程图 - 主线用粗实线，引用用细虚线"""
    dot = Digraph(comment='Multi-Agent Flow')
    dot.attr(rankdir='LR', bgcolor='white')
    
    # 设置节点样式
    dot.attr('node', shape='box', style='filled', fillcolor='#E6E6FA', fontname='Arial', fontsize='12')
    
    # 添加用户输入节点
    dot.node('user_input', f'用户输入:\\n{user_input[:30]}...' if len(user_input) > 30 else f'用户输入:\\n{user_input}', fillcolor='#90EE90')
    
    # 收集所有 agent 节点
    agents = {}
    for agent in config_json:
        agent_id = agent.get('agent_id', 'unknown')
        agents[agent_id] = agent
    
    # 添加 agent 节点
    for agent_id in agents.keys():
        dot.node(agent_id, agent_id)
    
    # 添加最终输出节点
    dot.node('final_output', '最终输出', fillcolor='#FFE4B5')
    
    # 确定主线：按照配置顺序连接 agent
    main_flow = list(agents.keys())
    
    # 添加边
    edges_added = set()
    
    for agent in config_json:
        agent_id = agent.get('agent_id', 'unknown')
        
        for inp in agent.get('input', []):
            from_source = inp.get('from', '')
            
            if from_source == 'user':
                # 用户输入到第一个 agent 是主线，其他是引用
                if agent_id == main_flow[0]:
                    # 主线：粗实线
                    dot.edge('user_input', agent_id, penwidth='3', style='solid', color='#333333')
                else:
                    # 引用：细虚线
                    dot.edge('user_input', agent_id, penwidth='1', style='dashed', color='#666666', arrowhead='none')
                    
            elif from_source in agents:
                # 判断是否是主线连接（按照配置顺序）
                from_idx = main_flow.index(from_source) if from_source in main_flow else -1
                to_idx = main_flow.index(agent_id) if agent_id in main_flow else -1
                
                is_main_flow = (from_idx >= 0 and to_idx >= 0 and from_idx + 1 == to_idx)
                
                if is_main_flow:
                    # 主线：粗实线
                    dot.edge(from_source, agent_id, penwidth='3', style='solid', color='#333333')
                else:
                    # 支线：中等实线
                    dot.edge(from_source, agent_id, penwidth='1.5', style='solid', color='#555555')
        
        # 输出到最终节点
        for out in agent.get('output', []):
            to_list = out.get('to', [])
            for target in to_list:
                if target.get('user'):
                    if agent_id == main_flow[-1]:
                        # 最后一个 agent 到输出是主线
                        dot.edge(agent_id, 'final_output', penwidth='3', style='solid', color='#333333')
                    else:
                        dot.edge(agent_id, 'final_output', penwidth='1.5', style='solid', color='#555555')
    
    return dot

st.title("🤖 Multi-Agent System Builder")
st.markdown("基于 JSON 配置的多智能体系统构建与训练平台")

# 侧边栏导航
st.sidebar.title("导航")
page = st.sidebar.radio(
    "选择页面",
    ["🏠 首页", "⚙️ 配置管理", "📁 数据管理", "▶️ 执行流程", "🎯 训练管理"]
)

# 首页
if page == "🏠 首页":
    st.header("欢迎使用 Multi-Agent System Builder")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("系统配置数", len(db.get_all_system_configs()))
    with col2:
        st.metric("数据集数", len(db.get_all_datasets()))
    with col3:
        st.metric("执行记录数", len(db.get_all_executions()))
    
    st.markdown("""
    ### 快速开始
    1. **配置管理** - 上传 JSON 配置文件定义多智能体系统
    2. **数据管理** - 上传测试数据集
    3. **执行流程** - 运行推理并生成轨迹
    4. **训练管理** - 进行 SFT / DPO / GRPO 训练
    """)

# 配置管理
elif page == "⚙️ 配置管理":
    st.header("⚙️ 配置管理")
    
    tab1, tab2 = st.tabs(["📤 上传配置", "📋 配置列表"])
    
    with tab1:
        st.subheader("上传 JSON 配置")
        
        # 示例配置 - 使用本地 Qwen2.5-0.5B-Instruct 模型（适合笔记本运行）
        # 模型会自动从 HuggingFace 下载到本地缓存
        example_config = [
            {
                "agent_id": "planner",
                "model": {"name_or_path": "Qwen/Qwen2.5-0.5B-Instruct"},
                "instruction_prompt": {
                    "instruction": "你是 Planner Agent：把用户需求拆成可执行的步骤计划。",
                    "prompt_template": "用户需求：{{input.user_request}}\n请输出 JSON 格式的 plan。"
                },
                "input": [{"from": "user", "key": "user_request"}],
                "output": [{"key": "plan", "to": [{"agent": "infer", "as": "plan"}]}]
            },
            {
                "agent_id": "infer",
                "model": {"name_or_path": "Qwen/Qwen2.5-0.5B-Instruct"},
                "instruction_prompt": {
                    "instruction": "你是 Inference Agent：按照 plan 解决问题并生成答案。",
                    "prompt_template": "Plan：{{input.plan}}\n问题：{{input.user_request}}\n请给出答案："
                },
                "input": [
                    {"from": "user", "key": "user_request"},
                    {"from": "planner", "key": "plan"}
                ],
                "output": [{"key": "draft_answer", "to": [{"agent": "checker", "as": "draft_answer"}]}]
            },
            {
                "agent_id": "checker",
                "model": {"name_or_path": "Qwen/Qwen2.5-0.5B-Instruct"},
                "instruction_prompt": {
                    "instruction": "你是 Checker Agent：检查答案是否正确、是否满足格式要求，并给出最终输出。",
                    "prompt_template": "问题：{{input.user_request}}\n候选答案：{{input.draft_answer}}\n请输出：{verdict, feedback, final_answer}"
                },
                "input": [
                    {"from": "user", "key": "user_request"},
                    {"from": "infer", "key": "draft_answer"}
                ],
                "output": [
                    {"key": "final_answer", "to": [{"user": True}]},
                    {"key": "verdict", "to": [{"user": True}]},
                    {"key": "feedback", "to": [{"user": True}]}
                ]
            }
        ]
        
        config_json = st.text_area(
            "JSON 配置",
            value=json.dumps(example_config, ensure_ascii=False, indent=2),
            height=400
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 校验配置"):
                try:
                    config_data = json.loads(config_json)
                    validator = JSONValidator()
                    result = validator.validate(config_data)
                    
                    if result.is_valid:
                        st.success("✅ 配置格式正确")
                        st.write("执行顺序:")
                        st.json(result.execution_order)
                        if result.warnings:
                            st.warning("警告:")
                            for warning in result.warnings:
                                st.warning(warning)
                        
                        # 显示流程图
                        st.subheader("📊 流程图")
                        flowchart = generate_flowchart(config_data, "用户输入")
                        st.graphviz_chart(flowchart.source)
                    else:
                        st.error("❌ 配置校验失败")
                        st.write("错误详情:")
                        for error in result.errors:
                            st.error(f"• {error}")
                        if result.warnings:
                            st.warning("警告:")
                            for warning in result.warnings:
                                st.warning(f"• {warning}")
                except json.JSONDecodeError as e:
                    st.error(f"❌ JSON 解析错误: {e}")
        
        with col2:
            config_name = st.text_input("配置名称", value="Plan-Infer-Check 示例")
            if st.button("💾 保存配置"):
                try:
                    config_data = json.loads(config_json)
                    validator = JSONValidator()
                    result = validator.validate(config_data)
                    
                    if result.is_valid:
                        config = db.create_system_config(
                            name=config_name,
                            config_json=config_data
                        )
                        # 更新校验状态和执行顺序
                        db.update_config_validation(
                            config_id=config.id,
                            is_valid=True,
                            execution_order=result.execution_order
                        )
                        st.success(f"✅ 配置已保存 (ID: {config.id})")
                    else:
                        st.error("❌ 配置校验失败，无法保存")
                except Exception as e:
                    st.error(f"❌ 保存失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    with tab2:
        st.subheader("已保存的配置")
        configs = db.get_all_system_configs()
        
        for config in configs:
            with st.expander(f"{config.name} (ID: {config.id}, {'✅' if config.is_valid else '❌'})"):
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.json(config.config_json)
                with col2:
                    if config.is_valid:
                        st.subheader("📊 流程图")
                        # 获取输入 key
                        input_key = '用户输入'
                        if config.config_json and config.config_json[0].get('input'):
                            for inp in config.config_json[0]['input']:
                                if inp.get('from') == 'user':
                                    input_key = inp.get('key', '用户输入')
                                    break
                        flowchart = generate_flowchart(config.config_json, input_key)
                        st.graphviz_chart(flowchart.source)

# 数据管理
elif page == "📁 数据管理":
    st.header("📁 数据管理")
    
    tab1, tab2 = st.tabs(["📤 上传数据", "📋 数据列表"])
    
    with tab1:
        st.subheader("上传测试数据")
        
        dataset_name = st.text_input("数据集名称", value="测试数据集")
        dataset_type = st.selectbox("数据集类型", ["test", "train", "validation"])
        
        # 示例数据
        example_data = '{"user_request": "帮我制定一个学习计划"}\n{"user_request": "帮我写一段Python代码"}'
        data_content = st.text_area(
            "数据内容 (JSONL 格式，每行一个 JSON 对象)",
            value=example_data,
            height=200
        )
        
        if st.button("📤 上传数据集"):
            try:
                # 验证 JSONL 格式
                lines = data_content.strip().split('\n')
                for line in lines:
                    json.loads(line)
                
                # 保存到文件
                os.makedirs('data/datasets', exist_ok=True)
                file_path = f'data/datasets/{dataset_name}.jsonl'
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(data_content)
                
                # 保存到数据库
                dataset_id = db.create_dataset(
                    name=dataset_name,
                    file_path=file_path,
                    file_format='jsonl',
                    data_type=dataset_type
                )
                st.success(f"✅ 数据集已上传 (ID: {dataset_id})")
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON 格式错误: {e}")
            except Exception as e:
                st.error(f"❌ 上传失败: {e}")
    
    with tab2:
        st.subheader("已上传的数据集")
        datasets = db.get_all_datasets()
        
        for dataset in datasets:
            with st.expander(f"{dataset.name} (ID: {dataset.id}, 类型: {dataset.data_type})"):
                st.write(f"文件路径: {dataset.file_path}")
                if os.path.exists(dataset.file_path):
                    with open(dataset.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    st.text(content[:500] + "..." if len(content) > 500 else content)

# 执行流程
elif page == "▶️ 执行流程":
    st.header("▶️ 执行流程")
    
    # 获取有效配置
    configs = db.get_all_system_configs(only_valid=True)
    config_options = {f"{c.name} (ID: {c.id})": c.id for c in configs}
    
    # 获取数据集
    datasets = db.get_all_datasets()
    dataset_options = {"不使用数据集": None}
    dataset_options.update({f"{d.name} (ID: {d.id})": d.id for d in datasets})
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_config = st.selectbox("选择系统配置", list(config_options.keys()))
        selected_dataset = st.selectbox("选择测试数据集", list(dataset_options.keys()))
        use_teacher = st.checkbox("使用教师模型", value=False)
        record_traj = st.checkbox("记录执行轨迹", value=True)
    
    with col2:
        # 根据配置动态显示输入提示
        if configs:
            first_config = list(config_options.values())[0]
            config_temp = db.get_system_config(first_config)
            if config_temp and config_temp.config_json:
                first_agent = config_temp.config_json[0]
                if first_agent.get('input'):
                    for inp in first_agent['input']:
                        if inp.get('from') == 'user':
                            input_key_hint = inp.get('key', 'user_request')
                            break
                    else:
                        input_key_hint = first_agent['input'][0].get('key', 'user_request')
                else:
                    input_key_hint = 'user_request'
            else:
                input_key_hint = 'user_request'
        else:
            input_key_hint = 'user_request'
        
        # 默认输入
        default_input = st.text_area(
            f"测试输入 ({input_key_hint})",
            value="帮我制定一个学习计划，准备下周的数学考试" if input_key_hint == 'user_request' else "解方程: 2x + 5 = 15",
            height=100
        )
    
    if st.button("▶️ 开始执行", type="primary"):
        if not selected_config:
            st.error("❌ 请选择一个系统配置")
        else:
            config_id = config_options[selected_config]
            config = db.get_system_config(config_id)
            
            with st.spinner("正在执行推理..."):
                try:
                    # 自动检测输入 key（从第一个 agent 的输入配置中获取）
                    first_agent = config.config_json[0] if config.config_json else None
                    if first_agent and first_agent.get('input'):
                        # 找到 from: user 的输入 key
                        user_input_key = None
                        for inp in first_agent['input']:
                            if inp.get('from') == 'user':
                                user_input_key = inp.get('key')
                                break
                        # 如果没找到，使用第一个输入的 key
                        if not user_input_key:
                            user_input_key = first_agent['input'][0].get('key', 'user_request')
                    else:
                        user_input_key = 'user_request'
                    
                    # 准备输入
                    inputs = [{user_input_key: default_input}]
                    
                    # 执行推理
                    spec = SystemSpec(agents=config.config_json)
                    generator = TrajectoryGenerator(spec, config_id=config_id)
                    trajectories = generator.generate_batch(inputs, use_teacher=use_teacher)
                    
                    st.success(f"✅ 成功生成 {len(trajectories)} 条轨迹")
                    
                    # 显示轨迹
                    for i, traj in enumerate(trajectories):
                        st.subheader(f"轨迹 {i+1}: {traj.trajectory_id}")
                        
                        for step in traj.steps:
                            with st.expander(f"步骤 {step.step_index + 1}: {step.agent_id}"):
                                st.markdown("**Prompt:**")
                                st.code(step.prompt)
                                st.markdown("**Response:**")
                                st.code(step.response)
                    
                    # 保存轨迹
                    if record_traj:
                        for traj in trajectories:
                            for step in traj.steps:
                                db.create_generated_data(
                                    agent_id=step.agent_id,
                                    trajectory=step.to_dict(),
                                    config_id=config_id,
                                    input_data=step.input_data,
                                    output_data=step.output_data
                                )
                        st.info("✓ 轨迹已保存到数据库")
                    
                except Exception as e:
                    st.error(f"❌ 执行失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())

# 训练管理
elif page == "🎯 训练管理":
    st.header("🎯 训练管理")
    
    st.info("训练功能正在开发中...")
    
    st.markdown("""
    ### 计划支持的训练类型
    1. **SFT (Supervised Fine-Tuning)** - 监督微调
    2. **DPO (Direct Preference Optimization)** - 直接偏好优化
    3. **GRPO (Group Relative Policy Optimization)** - 组相对策略优化
    """)

if __name__ == "__main__":
    pass
