/**
 * Multi-Agent System Builder - Frontend Application
 * Enterprise-grade JavaScript for FastAPI backend
 */

// ============== Configuration ==============
const API_BASE = '';
let currentPage = 'dashboard';

// ============== Authentication ==============
function getToken() {
    return localStorage.getItem('access_token');
}

function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/';
}

// Check authentication on load
if (!getToken() && !window.location.pathname.includes('login')) {
    window.location.href = '/';
}

// ============== API Helpers ==============
async function apiRequest(url, options = {}) {
    const token = getToken();
    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };
    
    const response = await fetch(`${API_BASE}${url}`, {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    });
    
    if (response.status === 401) {
        logout();
        return null;
    }
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Request failed');
    }
    
    return response.json();
}

function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// ============== Page Navigation ==============
function switchPage(page) {
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-page="${page}"]`).classList.add('active');
    
    // Update page content
    document.querySelectorAll('.page-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`page-${page}`).classList.add('active');
    
    currentPage = page;
    
    // Load page data
    switch(page) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'builder':
            loadConfigs();
            loadBuilderConfigOptions();
            break;
        case 'data':
            loadDatasets();
            break;
        case 'execution':
            loadExecutionOptions();
            break;
        case 'trajectory':
            loadTrajectoryFilters();
            break;
        case 'training':
            loadTrainingJobs();
            break;
    }
}

function switchBuilderTab(tab, element) {
    document.querySelectorAll('#page-builder .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#page-builder .tab-content').forEach(c => c.classList.remove('active'));
    
    element.classList.add('active');
    document.getElementById(`builder-${tab}`).classList.add('active');
}

function switchTrainingTab(tab, element) {
    document.querySelectorAll('#page-training .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#page-training .tab-content').forEach(c => c.classList.remove('active'));
    
    element.classList.add('active');
    document.getElementById(`training-${tab}`).classList.add('active');
    
    // Load data for specific tabs
    if (tab === 'eval') {
        loadEvaluableJobs();
    }
}

// ============== Dashboard ==============
async function loadDashboardData() {
    try {
        showLoading();
        const stats = await apiRequest('/api/stats');
        
        document.getElementById('stat-configs').textContent = stats.config_count;
        document.getElementById('stat-valid-configs').textContent = stats.valid_config_count;
        document.getElementById('stat-datasets').textContent = stats.dataset_count;
        document.getElementById('stat-trajectories').textContent = stats.trajectory_count;
        
        // Load recent configs
        const configs = await apiRequest('/api/configs');
        const recentConfigs = configs.slice(0, 5);
        document.getElementById('recent-configs').innerHTML = recentConfigs.map(c => `
            <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f0f0f0;">
                <span>${c.name}</span>
                <span class="tag ${c.is_valid ? 'tag-write' : 'tag-sft'}">${c.is_valid ? '✅ 有效' : '❌ 无效'}</span>
            </div>
        `).join('') || '<p style="color: #8c8c8c;">暂无配置</p>';
        
        // Load recent executions
        const executions = await apiRequest('/api/executions');
        const recentExecs = executions.slice(0, 5);
        document.getElementById('recent-executions').innerHTML = recentExecs.map(e => `
            <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f0f0f0;">
                <span>执行 #${e.id}</span>
                <span class="tag ${e.status === 'completed' ? 'tag-write' : e.status === 'running' ? 'tag-read' : 'tag-sft'}">${e.status}</span>
            </div>
        `).join('') || '<p style="color: #8c8c8c;">暂无执行记录</p>';
        
        // Load recent trainings
        const trainings = await apiRequest('/api/training/jobs');
        const recentTrainings = trainings.slice(0, 5);
        document.getElementById('recent-trainings').innerHTML = recentTrainings.map(t => `
            <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f0f0f0;">
                <span>${t.name}</span>
                <span class="tag tag-grpo">${t.type.toUpperCase()}</span>
            </div>
        `).join('') || '<p style="color: #8c8c8c;">暂无训练任务</p>';
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
    } finally {
        hideLoading();
    }
}

// ============== Builder ==============
const exampleConfig = [
    {
        "agent_id": "planner",
        "model": { "name_or_path": "Qwen2.5-0.5B-Instruct" },
        "instruction_prompt": {
            "instruction": "你是 Planner Agent：把用户需求拆成可执行的步骤计划。",
            "prompt_template": "用户需求：{{input.user_request}}\n请输出 JSON 格式的 plan。"
        },
        "input": [{ "from": "user", "key": "user_request" }],
        "output": [{ "key": "plan", "to": [{ "agent": "infer", "as": "plan" }] }]
    },
    {
        "agent_id": "infer",
        "model": { "name_or_path": "Qwen2.5-0.5B-Instruct" },
        "instruction_prompt": {
            "instruction": "你是 Inference Agent：按照 plan 解决问题并生成答案。",
            "prompt_template": "Plan：{{input.plan}}\n问题：{{input.user_request}}\n请给出答案："
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
            "prompt_template": "问题：{{input.user_request}}\n候选答案：{{input.draft_answer}}\n请输出：{verdict, final_answer}"
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
];

let vizZoomLevel = 1;

function zoomViz(factor) {
    vizZoomLevel *= factor;
    vizZoomLevel = Math.max(0.3, Math.min(3, vizZoomLevel));
    const viz = document.getElementById('dataflow-viz');
    if (viz) {
        viz.style.transform = `scale(${vizZoomLevel})`;
    }
}

function resetVizZoom() {
    vizZoomLevel = 1;
    const viz = document.getElementById('dataflow-viz');
    if (viz) {
        viz.style.transform = 'scale(1)';
    }
}

let isFullscreen = false;

function toggleFullscreenViz() {
    const container = document.getElementById('dataflow-viz-container');
    const viz = document.getElementById('dataflow-viz');
    
    if (!isFullscreen) {
        // Enter fullscreen
        container.classList.add('viz-fullscreen');
        
        // Create floating controls
        const controls = document.createElement('div');
        controls.id = 'viz-fullscreen-controls';
        controls.className = 'viz-fullscreen-overlay';
        controls.innerHTML = `
            <div style="display: flex; gap: 8px; flex-direction: column; min-width: 120px;">
                <div style="font-weight: 600; font-size: 14px; margin-bottom: 8px; text-align: center; color: #333;">数据流图控制</div>
                <button class="btn btn-secondary" style="padding: 10px 16px; font-size: 14px;" onclick="zoomViz(0.8)">🔍- 缩小</button>
                <button class="btn btn-secondary" style="padding: 10px 16px; font-size: 14px;" onclick="zoomViz(1.25)">🔍+ 放大</button>
                <button class="btn btn-secondary" style="padding: 10px 16px; font-size: 14px;" onclick="resetVizZoom()">⟲ 重置</button>
                <div style="border-top: 1px solid #e5e7eb; margin: 8px 0;"></div>
                <button class="btn btn-primary" style="padding: 10px 16px; font-size: 14px;" onclick="toggleFullscreenViz()">✕ 退出全屏</button>
            </div>
        `;
        document.body.appendChild(controls);
        
        // Auto zoom to fit - larger scale for fullscreen
        vizZoomLevel = 2.0;
        viz.style.transform = `scale(${vizZoomLevel})`;
        
        isFullscreen = true;
    } else {
        // Exit fullscreen
        container.classList.remove('viz-fullscreen');
        
        // Remove floating controls
        const controls = document.getElementById('viz-fullscreen-controls');
        if (controls) {
            controls.remove();
        }
        
        // Reset zoom to normal
        vizZoomLevel = 1;
        viz.style.transform = 'scale(1)';
        
        isFullscreen = false;
    }
}

// Exit fullscreen on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isFullscreen) {
        toggleFullscreenViz();
    }
});

async function loadBuilderConfig(configId) {
    if (!configId) return;
    
    try {
        showLoading();
        const config = await apiRequest(`/api/configs/${configId}`);
        document.getElementById('config-name').value = config.name;
        document.getElementById('config-json').value = JSON.stringify(config.config_json, null, 2);
    } catch (error) {
        alert('加载配置失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function loadBuilderConfigOptions() {
    try {
        const configs = await apiRequest('/api/configs');
        const select = document.getElementById('builder-config-select');
        if (select) {
            select.innerHTML = '<option value="">-- 选择已保存的配置 --</option>' +
                configs.map(c => `<option value="${c.id}">${c.name} (ID: ${c.id})</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading builder config options:', error);
    }
}

function loadExampleConfig() {
    document.getElementById('config-json').value = JSON.stringify(exampleConfig, null, 2);
    document.getElementById('config-name').value = 'Plan-Infer-Check System';
}

async function loadBranchLoopExample() {
    try {
        const response = await fetch('/static/examples/simple_loop_config.json');
        const config = await response.json();
        document.getElementById('config-json').value = JSON.stringify(config, null, 2);
        document.getElementById('config-name').value = 'Simple Loop System';
    } catch (error) {
        alert('加载示例失败: ' + error.message);
    }
}

async function loadComplexBranchExample() {
    try {
        const response = await fetch('/static/examples/branch_loop_config.json');
        const config = await response.json();
        document.getElementById('config-json').value = JSON.stringify(config, null, 2);
        document.getElementById('config-name').value = 'Branch & Loop System';
    } catch (error) {
        alert('加载示例失败: ' + error.message);
    }
}

// ============== Prompt Optimization ==============
async function optimizePrompts() {
    const configId = document.getElementById('builder-config-select').value;
    if (!configId) {
        alert('请先保存配置或选择已有配置');
        return;
    }
    
    try {
        showLoading();
        const result = await apiRequest(`/api/configs/${configId}/optimize-prompts`, {
            method: 'POST'
        });
        
        if (result.success) {
            // 显示优化结果
            document.getElementById('config-json').value = JSON.stringify(result.optimized_config, null, 2);
            
            // 显示对比
            let comparisonHtml = '<div style="max-height: 400px; overflow: auto;">';
            comparisonHtml += `<h4>✨ Prompt 优化完成</h4>`;
            comparisonHtml += `<p>优化了 ${result.summary.optimized_count}/${result.summary.total_agents} 个 Agent</p>`;
            comparisonHtml += '<hr>';
            
            result.comparisons.forEach((comp, idx) => {
                comparisonHtml += `<div style="margin-bottom: 20px;">${comp.replace(/\n/g, '<br>')}</div>`;
            });
            
            comparisonHtml += '</div>';
            
            document.getElementById('validation-result').innerHTML = `
                <div class="alert alert-success">
                    <span>✅</span>
                    <div>${comparisonHtml}</div>
                </div>
            `;
            
            alert('Prompt 优化完成！优化后的配置已加载到编辑器。');
        }
    } catch (error) {
        alert('优化失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

// ============== Execution ==============
async function executeConfig() {
    const configId = document.getElementById('builder-config-select').value;
    const testInput = document.getElementById('test-input').value;
    
    if (!configId) {
        alert('请先选择配置');
        return;
    }
    
    if (!testInput) {
        alert('请输入测试内容');
        return;
    }
    
    try {
        showLoading();
        document.getElementById('validation-result').innerHTML = `
            <div class="alert alert-info">
                <span>⏳</span>
                <div>正在执行...</div>
            </div>
        `;
        
        const result = await apiRequest(`/api/configs/${configId}/execute`, {
            method: 'POST',
            body: JSON.stringify({
                input: { user_request: testInput },
                max_steps: 100
            })
        });
        
        if (result.success) {
            // 显示执行结果
            let logHtml = '<div style="max-height: 300px; overflow: auto; background: #f5f5f5; padding: 10px; border-radius: 8px;">'
            logHtml += `<h4>执行日志 (${result.total_steps} 步)</h4>`;
            
            result.execution_log.forEach(log => {
                logHtml += `<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 4px;">`;
                logHtml += `<strong>Step ${log.step}:</strong> ${log.agent_id}<br>`;
                logHtml += `<small>输出: ${JSON.stringify(log.output).substring(0, 200)}...</small>`;
                logHtml += `</div>`;
            });
            
            logHtml += '</div>';
            
            document.getElementById('validation-result').innerHTML = `
                <div class="alert alert-success">
                    <span>✅</span>
                    <div>
                        <h4>执行成功</h4>
                        <p>总步数: ${result.total_steps}</p>
                        ${logHtml}
                        <h4>最终输出:</h4>
                        <pre style="background: #f5f5f5; padding: 10px; border-radius: 8px; overflow: auto;">${JSON.stringify(result.final_state, null, 2)}</pre>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('validation-result').innerHTML = `
            <div class="alert alert-error">
                <span>❌</span>
                <div>执行失败: ${error.message}</div>
            </div>
        `;
    } finally {
        hideLoading();
    }
}

// ============== Batch Execution ==============
function showBatchModal() {
    const configId = document.getElementById('builder-config-select').value;
    if (!configId) {
        alert('请先选择配置');
        return;
    }
    
    // 简单的批量输入对话框
    const batchInput = prompt('请输入批量测试数据（每行一个，JSON格式）:', 
        '{"user_request": "问题1"}\n{"user_request": "问题2"}');
    
    if (!batchInput) return;
    
    try {
        const inputs = batchInput.split('\n')
            .filter(line => line.trim())
            .map(line => JSON.parse(line));
        
        executeBatch(configId, inputs);
    } catch (e) {
        alert('输入格式错误: ' + e.message);
    }
}

async function executeBatch(configId, inputs) {
    try {
        showLoading();
        document.getElementById('validation-result').innerHTML = `
            <div class="alert alert-info">
                <span>⏳</span>
                <div>批量执行中，共 ${inputs.length} 条...</div>
            </div>
        `;
        
        const result = await apiRequest(`/api/configs/${configId}/execute-batch`, {
            method: 'POST',
            body: JSON.stringify({
                inputs: inputs,
                parallel: true,
                max_workers: 4
            })
        });
        
        // 显示批量结果
        let resultHtml = `<h4>批量执行完成</h4>`;
        resultHtml += `<p>总计: ${result.total}, 成功: ${result.completed}, 失败: ${result.failed}</p>`;
        resultHtml += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">';
        resultHtml += '<tr style="background: #f5f5f5;"><th style="padding: 8px; border: 1px solid #ddd;">ID</th><th style="padding: 8px; border: 1px solid #ddd;">状态</th><th style="padding: 8px; border: 1px solid #ddd;">输出</th></tr>';
        
        result.results.forEach(r => {
            const status = r.success ? '✅' : '❌';
            const output = r.success ? JSON.stringify(r.output).substring(0, 100) : r.error;
            resultHtml += `<tr><td style="padding: 8px; border: 1px solid #ddd;">${r.item_id}</td><td style="padding: 8px; border: 1px solid #ddd;">${status}</td><td style="padding: 8px; border: 1px solid #ddd;">${output}...</td></tr>`;
        });
        
        resultHtml += '</table>';
        
        document.getElementById('validation-result').innerHTML = `
            <div class="alert alert-success">
                <span>✅</span>
                <div>${resultHtml}</div>
            </div>
        `;
    } catch (error) {
        document.getElementById('validation-result').innerHTML = `
            <div class="alert alert-error">
                <span>❌</span>
                <div>批量执行失败: ${error.message}</div>
            </div>
        `;
    } finally {
        hideLoading();
    }
}

async function validateConfig() {
    const jsonText = document.getElementById('config-json').value;
    if (!jsonText) {
        alert('请输入 JSON 配置');
        return;
    }
    
    try {
        showLoading();
        const configJson = JSON.parse(jsonText);
        const result = await apiRequest('/api/configs/validate', {
            method: 'POST',
            body: JSON.stringify({ config_json: configJson })
        });
        
        // Update validation result
        const resultDiv = document.getElementById('validation-result');
        if (result.is_valid) {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <span>✅</span>
                    <div>配置有效！执行顺序：${result.execution_order.join(' → ')}</div>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="alert alert-error">
                    <span>❌</span>
                    <div>${result.errors.join('<br>')}</div>
                </div>
            `;
        }
        
        // Update visualization
        updateDataflowViz(result.graph, result.execution_order, configJson);
        
        // Update state analysis
        updateStateAnalysis(configJson);
        
    } catch (error) {
        document.getElementById('validation-result').innerHTML = `
            <div class="alert alert-error">
                <span>❌</span>
                <div>${error.message}</div>
            </div>
        `;
    } finally {
        hideLoading();
    }
}

function updateDataflowViz(graph, executionOrder, configJson) {
    if (!graph || graph.error) {
        document.getElementById('dataflow-viz').innerHTML = `
            <div style="text-align: center; color: #8c8c8c;">
                <div style="font-size: 48px; margin-bottom: 16px;">❌</div>
                <div>无法生成可视化</div>
            </div>
        `;
        return;
    }
    
    // Build a complete dependency graph
    const nodes = new Map();
    const edges = [];
    
    // Add user input node
    nodes.set('user_input', { id: 'user_input', type: 'input', label: '用户输入' });
    
    // Add agent nodes and edges from config
    configJson.forEach(agent => {
        const agentId = agent.agent_id;
        nodes.set(agentId, {
            id: agentId,
            type: 'agent',
            label: agentId,
            model: agent.model?.name_or_path?.split('/').pop() || 'Unknown',
            trainable: agent.training?.trainable || false
        });
        
        // Add input edges
        (agent.input || []).forEach(input => {
            const fromId = input.from === 'user' ? 'user_input' : input.from;
            edges.push({
                from: fromId,
                to: agentId,
                label: input.key,
                type: input.from === 'user' ? 'solid' : 'dashed'
            });
        });
        
        // Add output nodes and edges
        (agent.output || []).forEach(output => {
            const outputId = `${agentId}_output_${output.key}`;
            nodes.set(outputId, {
                id: outputId,
                type: 'state',
                label: output.key,
                parent: agentId
            });
            
            // Edge from agent to output
            edges.push({
                from: agentId,
                to: outputId,
                label: output.key,
                type: 'solid'
            });
            
            // Edges from output to target agents
            (output.to || []).forEach(target => {
                if (target.agent) {
                    edges.push({
                        from: outputId,
                        to: target.agent,
                        label: target.as || output.key,
                        type: 'dashed'
                    });
                }
            });
        });
    });
    
    // Generate Mermaid diagram
    let mermaidCode = 'graph LR\n';
    
    // Define styles
    mermaidCode += '    classDef inputStyle fill:#52c41a,stroke:#389e0d,stroke-width:2px,color:#fff;\n';
    mermaidCode += '    classDef agentStyle fill:#e6f7ff,stroke:#1890ff,stroke-width:2px;\n';
    mermaidCode += '    classDef stateStyle fill:#f6ffed,stroke:#52c41a,stroke-width:1px;\n';
    mermaidCode += '    classDef finalStyle fill:#fff7e6,stroke:#fa8c16,stroke-width:2px;\n';
    
    // Add nodes
    nodes.forEach((node, id) => {
        const safeId = id.replace(/[^a-zA-Z0-9_]/g, '_');
        if (node.type === 'input') {
            mermaidCode += `    ${safeId}[${node.label}]:::inputStyle\n`;
        } else if (node.type === 'agent') {
            const modelInfo = node.model ? `<br/><small>${node.model}</small>` : '';
            mermaidCode += `    ${safeId}[${node.label}${modelInfo}]:::agentStyle\n`;
        } else if (node.type === 'state') {
            mermaidCode += `    ${safeId}([${node.label}]):::stateStyle\n`;
        }
    });
    
    // Add edges
    edges.forEach(edge => {
        const fromId = edge.from.replace(/[^a-zA-Z0-9_]/g, '_');
        const toId = edge.to.replace(/[^a-zA-Z0-9_]/g, '_');
        const lineType = edge.type === 'dashed' ? '-.-' : '-->';
        const label = edge.label ? `|${edge.label}|` : '';
        mermaidCode += `    ${fromId} ${lineType}${label} ${toId}\n`;
    });
    
    // Render with Mermaid
    const html = `
        <div class="mermaid" style="background: white; padding: 20px; border-radius: 8px;">
            ${mermaidCode}
        </div>
        <div style="margin-top: 20px; padding: 15px; background: #fafafa; border-radius: 8px; display: flex; gap: 30px; justify-content: center; font-size: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 30px; height: 2px; background: #1890ff;"></div>
                <span>直接数据流</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 30px; height: 2px; border-top: 2px dashed #1890ff;"></div>
                <span>间接数据流</span>
            </div>
        </div>
    `;
    
    document.getElementById('dataflow-viz').innerHTML = html;
    
    // Initialize Mermaid
    if (window.mermaid) {
        mermaid.init(undefined, document.querySelectorAll('.mermaid'));
    }
}

function createAgentNode(agentId, modelName, status, isTrainable = false) {
    const borderColor = status === 'completed' ? '#52c41a' : status === 'running' ? '#1890ff' : '#667eea';
    const borderStyle = isTrainable ? 'dashed' : 'solid';
    const trainableBadge = isTrainable ? '<div style="position: absolute; top: -8px; right: -8px; background: #722ed1; color: white; font-size: 10px; padding: 2px 6px; border-radius: 4px;">可训练</div>' : '';
    
    return `
        <div style="display: inline-flex; flex-direction: column; align-items: center; padding: 20px 28px; 
                    background: white; border: 2px ${borderStyle} ${borderColor}; border-radius: 16px; 
                    margin: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); position: relative; min-width: 160px;">
            ${trainableBadge}
            <div style="font-weight: 600; font-size: 16px;">${agentId}</div>
            <div style="font-size: 11px; color: #667eea; background: rgba(102,126,234,0.1); 
                        padding: 4px 10px; border-radius: 6px; margin-top: 8px;">${modelName}</div>
        </div>
    `;
}

function createStateNode(fieldName, color = '#52c41a', label = '') {
    const displayLabel = label || fieldName;
    return `
        <div style="display: inline-flex; flex-direction: column; align-items: center; padding: 16px 24px; 
                    background: #f6ffed; border: 2px solid ${color}; border-radius: 12px; margin: 10px; min-width: 120px;">
            <div style="font-weight: 600; font-size: 13px; color: ${color};">${displayLabel}</div>
        </div>
    `;
}

function createConnectionArrow(style = 'solid', label = '') {
    const borderStyle = style === 'dashed' ? 'dashed' : 'solid';
    const labelHtml = label ? `<div style="position: absolute; top: -20px; font-size: 10px; color: #8c8c8c; white-space: nowrap;">${label}</div>` : '';
    
    return `
        <div style="display: flex; flex-direction: column; align-items: center; position: relative;">
            ${labelHtml}
            <div style="display: flex; align-items: center;">
                <div style="width: 40px; height: 2px; border-top: 2px ${borderStyle} #667eea;"></div>
                <div style="width: 0; height: 0; border-left: 8px solid #667eea; border-top: 5px solid transparent; border-bottom: 5px solid transparent;"></div>
            </div>
        </div>
    `;
}

function createConnectionLine() {
    return '<div style="display: flex; align-items: center; color: #bfbfbf; font-size: 24px; margin: 0 20px;">→</div>';
}

function updateStateAnalysis(configJson) {
    const stateOps = {};
    
    configJson.forEach(agent => {
        const agentId = agent.agent_id;
        
        // Read operations
        agent.input.forEach(inp => {
            const key = inp.key;
            if (!stateOps[key]) stateOps[key] = { read: [], write: [] };
            stateOps[key].read.push(agentId);
        });
        
        // Write operations
        agent.output.forEach(out => {
            const key = out.key;
            if (!stateOps[key]) stateOps[key] = { read: [], write: [] };
            stateOps[key].write.push(agentId);
        });
    });
    
    const tbody = document.querySelector('#state-analysis tbody');
    tbody.innerHTML = '';
    
    Object.entries(stateOps).forEach(([field, ops]) => {
        if (ops.read.length > 0) {
            tbody.innerHTML += `
                <tr>
                    <td>${field}</td>
                    <td><span class="tag tag-read">READ</span></td>
                    <td>${ops.read.join(', ')}</td>
                </tr>
            `;
        }
        if (ops.write.length > 0) {
            tbody.innerHTML += `
                <tr>
                    <td>${field}</td>
                    <td><span class="tag tag-write">WRITE</span></td>
                    <td>${ops.write.join(', ')}</td>
                </tr>
            `;
        }
    });
}

async function saveConfig() {
    const name = document.getElementById('config-name').value;
    const jsonText = document.getElementById('config-json').value;
    
    if (!name || !jsonText) {
        alert('请提供配置名称和 JSON 内容');
        return;
    }
    
    try {
        showLoading();
        const configJson = JSON.parse(jsonText);
        const result = await apiRequest('/api/configs', {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                description: '',
                config_json: configJson
            })
        });
        
        if (result.existing) {
            alert(`配置已存在！ID: ${result.id}，名称: ${result.name}`);
        } else {
            alert(`配置已保存！ID: ${result.id}`);
        }
        
        // Refresh all config lists
        loadConfigs();
        loadExecutionOptions();
        loadTrainingOptions();
        await loadBuilderConfigOptions();
        // Auto-select the newly saved config
        const select = document.getElementById('builder-config-select');
        if (select && result.id) {
            select.value = result.id;
        }
    } catch (error) {
        alert('保存失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function loadConfigs() {
    try {
        const configs = await apiRequest('/api/configs');
        const tbody = document.querySelector('#config-list tbody');
        tbody.innerHTML = configs.map(c => `
            <tr>
                <td>${c.id}</td>
                <td>${c.name}</td>
                <td><span class="tag ${c.is_valid ? 'tag-write' : 'tag-sft'}">${c.is_valid ? '✅ 有效' : '❌ 无效'}</span></td>
                <td>${c.agent_count}</td>
                <td>${new Date(c.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="loadConfigDetail(${c.id})">查看</button>
                    <button class="btn btn-danger" style="padding: 6px 12px; font-size: 12px;" onclick="deleteConfig(${c.id})">删除</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading configs:', error);
    }
}

async function loadConfigDetail(configId) {
    try {
        const config = await apiRequest(`/api/configs/${configId}`);
        document.getElementById('config-name').value = config.name;
        document.getElementById('config-json').value = JSON.stringify(config.config_json, null, 2);
    } catch (error) {
        alert('加载配置失败: ' + error.message);
    }
}

async function deleteConfig(configId) {
    if (!confirm('确定要删除此配置吗？')) return;
    
    try {
        await apiRequest(`/api/configs/${configId}`, { method: 'DELETE' });
        loadConfigs();
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// ============== Data ==============
async function loadDatasets() {
    try {
        const datasets = await apiRequest('/api/datasets');
        document.getElementById('data-count').textContent = datasets.length;
        
        const tbody = document.querySelector('#dataset-list tbody');
        tbody.innerHTML = datasets.map(d => `
            <tr>
                <td>${d.id}</td>
                <td><strong>${d.name}</strong></td>
                <td><span class="tag tag-${d.type === 'test' ? 'read' : d.type === 'train' ? 'write' : 'sft'}">${d.type}</span></td>
                <td>${d.record_count}</td>
                <td><span class="tag tag-write">✓ 就绪</span></td>
                <td>
                    <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="viewDataset(${d.id})">查看</button>
                </td>
            </tr>
        `).join('') || '<tr><td colspan="6" style="text-align: center; color: #8c8c8c;">暂无数据集</td></tr>';
        
        // 加载已部署的模型
        loadDeployedModels();
    } catch (error) {
        console.error('Error loading datasets:', error);
    }
}

async function loadDeployedModels() {
    try {
        // 从训练任务中获取已部署的模型
        const jobs = await apiRequest('/api/training/jobs');
        
        // 显示已完成的训练任务
        const completedJobs = jobs.filter(j => j.status === 'completed');
        
        // 更新模型数量统计
        const modelCountEl = document.getElementById('model-count');
        if (modelCountEl) {
            modelCountEl.textContent = completedJobs.length;
        }
        
        // 更新模型列表
        const modelListContainer = document.getElementById('model-list-container');
        
        if (modelListContainer) {
            if (completedJobs.length === 0) {
                modelListContainer.innerHTML = '<div style="padding: 40px; text-align: center; color: #8c8c8c;">暂无已部署的模型<br><span style="font-size: 12px;">完成训练并部署后即可在此查看</span></div>';
                return;
            }
            
            modelListContainer.innerHTML = `
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: #f9fafb;">
                        <tr>
                            <th style="padding: 12px 16px; text-align: left; font-weight: 600; font-size: 13px;">任务名称</th>
                            <th style="padding: 12px 16px; text-align: left; font-weight: 600; font-size: 13px;">类型</th>
                            <th style="padding: 12px 16px; text-align: left; font-weight: 600; font-size: 13px;">模型路径</th>
                            <th style="padding: 12px 16px; text-align: left; font-weight: 600; font-size: 13px;">完成时间</th>
                            <th style="padding: 12px 16px; text-align: left; font-weight: 600; font-size: 13px;">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${completedJobs.map(m => `
                            <tr style="border-bottom: 1px solid #f0f0f0;">
                                <td style="padding: 12px 16px;"><strong>${m.name}</strong></td>
                                <td style="padding: 12px 16px;"><span class="tag tag-${m.type === 'sft' ? 'write' : m.type === 'grpo' ? 'sft' : 'read'}">${m.type.toUpperCase()}</span></td>
                                <td style="padding: 12px 16px; font-size: 12px; color: #666; max-width: 300px; overflow: hidden; text-overflow: ellipsis;" title="${m.model_path || m.output_dir || '-'}">${m.model_path || m.output_dir || '-'}</td>
                                <td style="padding: 12px 16px; font-size: 13px; color: #666;">${m.completed_at ? new Date(m.completed_at).toLocaleString() : '-'}</td>
                                <td style="padding: 12px 16px;">
                                    <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="testDeployedModel(${m.id})">🧪 测试</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
    } catch (error) {
        console.error('Error loading deployed models:', error);
    }
}

function showUploadModal() {
    alert('数据集上传功能需要后端文件上传支持，请通过 API 上传');
}

async function viewDataset(datasetId) {
    try {
        showLoading();
        const dataset = await apiRequest(`/api/datasets/${datasetId}`);
        
        // 构建预览内容
        let previewHtml = `
            <div style="background: white; border-radius: 16px; border: 1px solid #e8e8e8; overflow: hidden; max-width: 900px; max-height: 80vh; overflow-y: auto;">
                <div style="padding: 20px 24px; border-bottom: 1px solid #f0f0f0; background: linear-gradient(to right, #fafafa, #ffffff); display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 18px; font-weight: 600;">📊 数据集详情</div>
                    <button onclick="closeDatasetModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #8c8c8c;">×</button>
                </div>
                <div style="padding: 24px;">
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px; padding: 16px; background: #f9fafb; border-radius: 8px;">
                        <div><span style="color: #666;">ID：</span><strong>${dataset.id}</strong></div>
                        <div><span style="color: #666;">名称：</span><strong>${dataset.name}</strong></div>
                        <div><span style="color: #666;">类型：</span><span class="tag tag-${dataset.type === 'test' ? 'read' : dataset.type === 'train' ? 'write' : 'sft'}">${dataset.type}</span></div>
                        <div><span style="color: #666;">记录数：</span><strong>${dataset.record_count}</strong></div>
                        <div><span style="color: #666;">文件格式：</span>${dataset.file_format}</div>
                        <div><span style="color: #666;">创建时间：</span>${new Date(dataset.created_at).toLocaleString()}</div>
                    </div>
                    
                    <div style="margin-bottom: 16px;">
                        <div style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">数据预览（前5条）</div>
        `;
        
        if (dataset.preview && dataset.preview.length > 0) {
            // 获取所有列
            const allKeys = new Set();
            dataset.preview.forEach(record => {
                if (typeof record === 'object' && record !== null) {
                    Object.keys(record).forEach(key => allKeys.add(key));
                }
            });
            const columns = Array.from(allKeys);
            
            if (columns.length > 0) {
                previewHtml += `<table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead>
                        <tr style="background: #fafafa;">
                            ${columns.map(col => `<th style="padding: 12px; text-align: left; border-bottom: 1px solid #f0f0f0; font-weight: 600;">${col}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>`;
                
                dataset.preview.forEach((record, idx) => {
                    previewHtml += `<tr style="background: ${idx % 2 === 0 ? 'white' : '#fafafa'};">`;
                    columns.forEach(col => {
                        let value = record[col];
                        if (typeof value === 'object') {
                            value = JSON.stringify(value);
                        }
                        if (typeof value === 'string' && value.length > 100) {
                            value = value.substring(0, 100) + '...';
                        }
                        previewHtml += `<td style="padding: 12px; border-bottom: 1px solid #f0f0f0; max-width: 300px; overflow: hidden; text-overflow: ellipsis;">${value !== undefined ? value : '-'}</td>`;
                    });
                    previewHtml += '</tr>';
                });
                
                previewHtml += '</tbody></table>';
            } else {
                previewHtml += `<pre style="background: #f5f5f5; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px;">${JSON.stringify(dataset.preview, null, 2)}</pre>`;
            }
        } else {
            previewHtml += '<div style="color: #8c8c8c; text-align: center; padding: 40px;">暂无预览数据</div>';
        }
        
        previewHtml += `
                    </div>
                </div>
            </div>
        `;
        
        // 创建或更新模态框
        let modal = document.getElementById('dataset-preview-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'dataset-preview-modal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;';
            document.body.appendChild(modal);
        }
        modal.innerHTML = previewHtml;
        modal.style.display = 'flex';
        
    } catch (error) {
        alert('查看失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function closeDatasetModal() {
    const modal = document.getElementById('dataset-preview-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// ============== Execution ==============
async function loadExecutionOptions() {
    try {
        const [configs, datasets] = await Promise.all([
            apiRequest('/api/configs'),
            apiRequest('/api/datasets')
        ]);
        
        const configSelect = document.getElementById('exec-config');
        configSelect.innerHTML = '<option value="">请选择...</option>' + 
            configs.filter(c => c.is_valid).map(c => 
                `<option value="${c.id}">${c.name} (ID: ${c.id})</option>`
            ).join('');
        
        const datasetSelect = document.getElementById('exec-dataset');
        datasetSelect.innerHTML = '<option value="">请选择...</option>' + 
            datasets.map(d => 
                `<option value="${d.id}">${d.name} (ID: ${d.id})</option>`
            ).join('');
    } catch (error) {
        console.error('Error loading execution options:', error);
    }
}

async function startExecution() {
    const configId = document.getElementById('exec-config').value;
    const datasetId = document.getElementById('exec-dataset').value;
    const useTeacher = document.getElementById('use-teacher').checked;
    const recordTrajectory = document.getElementById('record-trajectory').checked;
    
    if (!configId) {
        alert('请选择系统配置');
        return;
    }
    
    try {
        showLoading();
        document.getElementById('exec-logs').textContent = '[INFO] 开始执行...\n';
        
        const result = await apiRequest('/api/executions', {
            method: 'POST',
            body: JSON.stringify({
                config_id: parseInt(configId),
                dataset_id: datasetId ? parseInt(datasetId) : null,
                use_teacher: useTeacher,
                record_trajectory: recordTrajectory
            })
        });
        
        document.getElementById('exec-logs').textContent += `[SUCCESS] 执行完成！生成了 ${result.trajectory_count} 条轨迹\n`;
        document.getElementById('exec-viz').innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; padding: 40px;">
                <div style="color: #52c41a; font-size: 48px;">✓</div>
                <div style="margin-left: 16px;">
                    <div style="font-size: 18px; font-weight: 600;">执行完成</div>
                    <div style="color: #8c8c8c;">执行ID: ${result.execution_id}</div>
                </div>
            </div>
        `;
        
        alert(`执行完成！生成了 ${result.trajectory_count} 条轨迹`);
    } catch (error) {
        document.getElementById('exec-logs').textContent += `[ERROR] ${error.message}\n`;
        alert('执行失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

// ============== Training ==============
async function loadTrainingOptions() {
    try {
        const configs = await apiRequest('/api/configs');
        
        const configSelect = document.getElementById('training-config');
        if (configSelect) {
            configSelect.innerHTML = '<option value="">请选择...</option>' + 
                configs.filter(c => c.is_valid).map(c => 
                    `<option value="${c.id}">${c.name} (ID: ${c.id})</option>`
                ).join('');
        }
    } catch (error) {
        console.error('Error loading training options:', error);
    }
}

// ============== Trajectory ==============
async function loadTrajectoryFilters() {
    try {
        const [configs, datasets] = await Promise.all([
            apiRequest('/api/configs'),
            apiRequest('/api/datasets')
        ]);
        
        const configSelect = document.getElementById('filter-config');
        configSelect.innerHTML = '<option value="">全部</option>' + 
            configs.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        
        const datasetSelect = document.getElementById('filter-dataset');
        datasetSelect.innerHTML = '<option value="">全部</option>' + 
            datasets.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
    } catch (error) {
        console.error('Error loading trajectory filters:', error);
    }
}

async function searchTrajectories() {
    const configId = document.getElementById('filter-config').value;
    const datasetId = document.getElementById('filter-dataset').value;
    
    try {
        showLoading();
        let url = '/api/trajectories?';
        if (configId) url += `config_id=${configId}&`;
        if (datasetId) url += `dataset_id=${datasetId}`;
        
        const trajectories = await apiRequest(url);
        
        const tbody = document.querySelector('#trajectory-list tbody');
        tbody.innerHTML = trajectories.map(t => `
            <tr>
                <td>${t.id}</td>
                <td>${t.trajectory_id}</td>
                <td>${t.config_id}</td>
                <td>${t.agent_id}</td>
                <td>${new Date(t.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;">查看</button>
                </td>
            </tr>
        `).join('') || '<tr><td colspan="6" style="text-align: center; color: #8c8c8c;">暂无轨迹数据</td></tr>';
    } catch (error) {
        alert('搜索失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function resetFilters() {
    document.getElementById('filter-config').value = '';
    document.getElementById('filter-dataset').value = '';
    document.getElementById('filter-agent').value = '';
    searchTrajectories();
}

function exportTrajectories() {
    alert('导出功能开发中...');
}

// ============== Training ==============
let currentTrainingJobs = [];

async function loadTrainingJobs() {
    try {
        const jobs = await apiRequest('/api/training/jobs');
        currentTrainingJobs = jobs;
        
        // Render jobs for each type tab
        const typeMap = { 'sft': 'sft', 'dpo': 'dpo', 'grpo': 'grpo' };
        for (const [type, tabType] of Object.entries(typeMap)) {
            const tbody = document.getElementById(`${tabType}-task-table-body`);
            if (!tbody) continue;
            
            const filteredJobs = jobs.filter(j => (j.type || 'sft') === type);
            tbody.innerHTML = filteredJobs.map(job => renderJobRow(job)).join('') 
                || `<tr><td colspan="6" style="padding: 24px; text-align: center; color: #8c8c8c;">暂无 ${type.toUpperCase()} 训练任务</td></tr>`;
        }
    } catch (error) {
        console.error('Error loading training jobs:', error);
    }
}

function renderJobRow(job) {
    const statusColors = {
        'pending': { bg: '#f0f0f0', color: '#666', text: '⏳ 等待中' },
        'running': { bg: '#e6f7ff', color: '#1890ff', text: '🔄 运行中' },
        'completed': { bg: '#f6ffed', color: '#52c41a', text: '✅ 已完成' },
        'failed': { bg: '#fff2f0', color: '#ff4d4f', text: '❌ 失败' },
        'stopped': { bg: '#f0f0f0', color: '#999', text: '⏹️ 已停止' }
    };
    const status = statusColors[job.status] || statusColors['pending'];
    const typeColors = {'sft': '#3b82f6', 'dpo': '#8b5cf6', 'grpo': '#f59e0b'};
    const typeColor = typeColors[job.type] || '#666';
    return `
        <tr style="border-bottom: 1px solid #f0f0f0;">
            <td style="padding: 12px 16px; font-size: 14px;">${job.name}</td>
            <td style="padding: 12px 16px; font-size: 14px; color: #666;">${job.config?.name || '-'}</td>
            <td style="padding: 12px 16px;">
                <span style="padding: 2px 8px; border-radius: 4px; font-size: 11px; background: ${typeColor}20; color: ${typeColor}; font-weight: 600;">${(job.type || 'sft').toUpperCase()}</span>
                <span style="padding: 4px 8px; border-radius: 4px; font-size: 12px; background: ${status.bg}; color: ${status.color}; margin-left: 4px;">${status.text}</span>
            </td>
            <td style="padding: 12px 16px; font-size: 14px;">${job.progress || 0}%</td>
            <td style="padding: 12px 16px; font-size: 14px; color: #666;">${new Date(job.created_at).toLocaleString()}</td>
            <td style="padding: 12px 16px;">
                <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px;" onclick="viewTrainingJob(${job.id})">查看</button>
                ${job.status === 'running' ? `<button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px; margin-left: 8px;" onclick="stopTrainingJob(${job.id})">停止</button>` : ''}
                <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 12px; margin-left: 8px; background: #ff4d4f; color: white; border-color: #ff4d4f;" onclick="deleteTrainingJob(${job.id})">删除</button>
            </td>
        </tr>
    `;
}

function showCreateTrainingModal(type) {
    document.getElementById('create-training-modal').style.display = 'block';
    loadTrainingModalOptions();
    // Pre-select the training type if specified
    if (type) {
        const radio = document.querySelector(`input[name="training-type"][value="${type}"]`);
        if (radio) {
            radio.checked = true;
            onTrainingTypeChange();
        }
    }
}

function showCreateTrainingModalForCurrentTab() {
    const activeTab = document.querySelector('#page-training .tab.active');
    const tabId = activeTab ? activeTab.textContent : '';
    let type = 'sft';
    if (tabId.includes('GRPO')) type = 'grpo';
    else if (tabId.includes('DPO')) type = 'dpo';
    showCreateTrainingModal(type);
}

function closeCreateTrainingModal() {
    document.getElementById('create-training-modal').style.display = 'none';
}

async function loadTrainingModalOptions() {
    try {
        const [configs, datasets] = await Promise.all([
            apiRequest('/api/configs'),
            apiRequest('/api/datasets')
        ]);
        
        // Load configs
        const configSelect = document.getElementById('training-config-select');
        configSelect.innerHTML = '<option value="">请选择系统配置</option>' + 
            configs.filter(c => c.is_valid).map(c => 
                `<option value="${c.id}">${c.name}</option>`
            ).join('');
        
        // Load datasets
        const datasetSelect = document.getElementById('training-dataset-select');
        datasetSelect.innerHTML = '<option value="">请选择数据集</option>' + 
            datasets.map(d => 
                `<option value="${d.id}">${d.name} (${d.record_count}条)</option>`
            ).join('');
        
        // Setup LoRA toggle
        const loraCheckbox = document.getElementById('training-use-lora');
        const loraSettings = document.getElementById('lora-settings');
        if (loraCheckbox && loraSettings) {
            loraCheckbox.addEventListener('change', (e) => {
                loraSettings.style.display = e.target.checked ? 'grid' : 'none';
            });
        }
    } catch (error) {
        console.error('Error loading modal options:', error);
    }
}

async function onTrainingConfigChange() {
    const configId = document.getElementById('training-config-select').value;
    const agentsInfo = document.getElementById('training-agents-info');
    const agentsList = document.getElementById('training-agents-list');
    
    if (!configId) {
        agentsInfo.style.display = 'none';
        return;
    }
    
    try {
        const config = await apiRequest(`/api/configs/${configId}`);
        const agents = config.config_json || [];
        
        // Get currently selected training type
        const trainingType = document.querySelector('input[name="training-type"]:checked')?.value || 'sft';
        
        // Find trainable agents based on type
        const trainableAgents = agents.filter(a => {
            const training = a.training || {};
            if (!training.trainable) return false;
            if (trainingType === 'auto') return true;
            return training.mode === trainingType;
        });
        
        if (trainableAgents.length > 0) {
            agentsList.innerHTML = trainableAgents.map(a => {
                const gt = a.training?.ground_truth || {};
                const mode = a.training?.mode || 'sft';
                const modeColors = {'sft': '#3b82f6', 'dpo': '#8b5cf6', 'grpo': '#f59e0b'};
                const modeColor = modeColors[mode] || '#666';
                let extraInfo = `输出: ${gt.output_key || '-'} → Ground Truth: ${gt.gt_key || '-'}`;
                if (mode === 'grpo') {
                    const rewards = a.training?.reward_spec || [];
                    extraInfo = `Reward Specs: ${rewards.length}, Trainable: ${a.training?.trainable}`;
                }
                if (mode === 'dpo') {
                    extraInfo = `GT Key: ${gt.gt_key || '-'} (chosen), Student output = rejected`;
                }
                return `
                    <div style="padding: 8px; background: white; border-radius: 4px; margin-bottom: 8px; border: 1px solid #e5e7eb;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 500;">${a.agent_id}</span>
                            <span style="padding: 2px 6px; border-radius: 3px; font-size: 11px; background: ${modeColor}20; color: ${modeColor}; font-weight: 600;">${mode.toUpperCase()}</span>
                        </div>
                        <div style="font-size: 12px; color: #666; margin-top: 4px;">${extraInfo}</div>
                    </div>
                `;
            }).join('');
            agentsInfo.style.display = 'block';
        } else {
            const typeLabel = trainingType === 'auto' ? '' : ` (${trainingType.toUpperCase()})`;
            agentsList.innerHTML = `<div style="color: #ff4d4f;">⚠️ 该配置中没有可训练的Agent${typeLabel}，请在JSON中添加 training 配置</div>`;
            agentsInfo.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading config details:', error);
    }
}

function onTrainingTypeChange() {
    const trainingType = document.querySelector('input[name="training-type"]:checked')?.value || 'sft';
    
    // Show/hide hyperparameter sections
    document.getElementById('sft-hparams').style.display = (trainingType === 'sft' || trainingType === 'auto') ? 'block' : 'none';
    document.getElementById('dpo-hparams').style.display = (trainingType === 'dpo') ? 'block' : 'none';
    document.getElementById('grpo-hparams').style.display = (trainingType === 'grpo') ? 'block' : 'none';
    
    // Also show SFT advanced options only for SFT
    const loraSection = document.getElementById('training-use-lora')?.closest('div[style*="margin-bottom: 24px"]');
    if (loraSection) {
        loraSection.style.display = (trainingType === 'sft' || trainingType === 'auto') ? 'block' : 'none';
    }
    
    // Update label styles
    const labels = {'sft': 'type-sft-label', 'dpo': 'type-dpo-label', 'grpo': 'type-grpo-label', 'auto': 'type-auto-label'};
    const typeBorderColors = {'sft': '#1890ff', 'dpo': '#8b5cf6', 'grpo': '#f59e0b', 'auto': '#1890ff'};
    const typeBgColors = {'sft': '#f0f9ff', 'dpo': '#f5f3ff', 'grpo': '#fffbeb', 'auto': '#f0f9ff'};
    Object.entries(labels).forEach(([type, id]) => {
        const el = document.getElementById(id);
        if (el) {
            if (type === trainingType) {
                el.style.border = `2px solid ${typeBorderColors[type] || '#1890ff'}`;
                el.style.background = typeBgColors[type] || '#f0f9ff';
            } else {
                el.style.border = '1px solid #d1d5db';
                el.style.background = 'white';
            }
        }
    });
    
    // Update modal title
    const titles = {'sft': '新建 SFT 训练任务', 'dpo': '新建 DPO 训练任务', 'grpo': '新建 GRPO 训练任务', 'auto': '新建训练任务 (自动检测)'};
    document.getElementById('training-modal-title').textContent = titles[trainingType] || '新建训练任务';
    
    // Re-trigger config change to update agent list
    onTrainingConfigChange();
}

async function onTrainingDatasetChange() {
    const datasetId = document.getElementById('training-dataset-select').value;
    const previewDiv = document.getElementById('training-dataset-preview');
    const infoDiv = document.getElementById('training-dataset-info');
    
    if (!datasetId) {
        previewDiv.style.display = 'none';
        return;
    }
    
    try {
        const dataset = await apiRequest(`/api/datasets/${datasetId}`);
        infoDiv.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;">
                <div><span style="color: #666;">记录数：</span>${dataset.record_count}</div>
                <div><span style="color: #666;">格式：</span>${dataset.file_format}</div>
                <div><span style="color: #666;">类型：</span>${dataset.type}</div>
                <div><span style="color: #666;">创建时间：</span>${new Date(dataset.created_at).toLocaleString()}</div>
            </div>
        `;
        previewDiv.style.display = 'block';
    } catch (error) {
        console.error('Error loading dataset details:', error);
    }
}

async function createTrainingTask() {
    const name = document.getElementById('training-name').value.trim();
    const configId = document.getElementById('training-config-select').value;
    const datasetId = document.getElementById('training-dataset-select').value;
    const description = document.getElementById('training-description').value.trim();
    const trainingType = document.querySelector('input[name="training-type"]:checked')?.value || 'sft';
    
    // Validation
    if (!name) {
        alert('请输入任务名称');
        return;
    }
    if (!configId) {
        alert('请选择系统配置');
        return;
    }
    if (!datasetId) {
        alert('请选择数据集');
        return;
    }
    
    // Get hyperparameters based on training type
    let hyperparameters = {};
    
    if (trainingType === 'sft' || trainingType === 'auto') {
        hyperparameters = {
            lr: parseFloat(document.getElementById('training-lr').value) || 2e-5,
            num_epochs: parseInt(document.getElementById('training-epochs').value) || 3,
            batch_size: parseInt(document.getElementById('training-batch-size').value) || 4,
            max_length: parseInt(document.getElementById('training-max-length').value) || 2048,
            warmup_ratio: parseFloat(document.getElementById('training-warmup').value) || 0.1,
            weight_decay: parseFloat(document.getElementById('training-weight-decay').value) || 0.01,
            fp16: document.getElementById('training-fp16').checked,
            use_lora: document.getElementById('training-use-lora').checked,
            lora_rank: parseInt(document.getElementById('training-lora-rank').value) || 8,
            lora_alpha: parseInt(document.getElementById('training-lora-alpha').value) || 32,
            use_flash_attn: document.getElementById('training-use-flash-attn').checked,
            gradient_checkpointing: document.getElementById('training-gradient-checkpointing').checked,
            quantization: document.getElementById('training-quantization').value || null
        };
    } else if (trainingType === 'dpo') {
        hyperparameters = {
            lr: parseFloat(document.getElementById('dpo-lr').value) || 5e-7,
            beta: parseFloat(document.getElementById('dpo-beta').value) || 0.1,
            num_epochs: parseInt(document.getElementById('dpo-epochs').value) || 3,
            batch_size: parseInt(document.getElementById('dpo-batch-size').value) || 2,
            max_length: 2048,
            gradient_accumulation_steps: 4,
            fp16: true,
            use_lora: true,
            lora_rank: 8,
            lora_alpha: 32,
        };
    } else if (trainingType === 'grpo') {
        hyperparameters = {
            lr: parseFloat(document.getElementById('grpo-lr').value) || 1e-6,
            rollout_batch_size: parseInt(document.getElementById('grpo-rollout-batch').value) || 64,
            kl_coef: parseFloat(document.getElementById('grpo-kl-coef').value) || 0.01,
            clip_range: parseFloat(document.getElementById('grpo-clip-range').value) || 0.2,
            mini_batch_size: parseInt(document.getElementById('grpo-mini-batch').value) || 8,
            advantage: document.getElementById('grpo-advantage').value || 'gae',
            num_epochs: 1,
            fp16: true,
        };
    }
    
    const dataSource = document.querySelector('input[name="data-source"]:checked').value;
    
    try {
        showLoading();
        
        const result = await apiRequest('/api/training/jobs', {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                type: trainingType === 'auto' ? 'auto' : trainingType,
                training_type: trainingType,
                description: description,
                config_id: parseInt(configId),
                dataset_id: parseInt(datasetId),
                hyperparameters: hyperparameters,
                data_source: dataSource,
                training_mode: 'auto'
            })
        });
        
        closeCreateTrainingModal();
        loadTrainingJobs();
        alert(`${trainingType.toUpperCase()} 训练任务创建成功！`);
        
    } catch (error) {
        alert('创建失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

let trainingDetailInterval = null;
let currentTrainingJobId = null;

async function viewTrainingJob(jobId) {
    try {
        currentTrainingJobId = jobId;
        const job = await apiRequest(`/api/training/jobs/${jobId}`);
        
        const content = document.getElementById('training-detail-content');
        content.innerHTML = `
            <div style="display: grid; gap: 20px;">
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; padding: 16px; background: #f9fafb; border-radius: 8px;">
                    <div><span style="color: #666;">任务名称：</span>${job.name}</div>
                    <div><span style="color: #666;">状态：</span><span id="job-status-${jobId}" style="font-weight: 600;">${job.status === 'completed' ? '✅ 已完成' : job.status === 'running' ? '🔄 运行中' : job.status === 'failed' ? '❌ 失败' : job.status}</span></div>
                    <div><span style="color: #666;">类型：</span>${(job.type || 'sft').toUpperCase()}</div>
                    <div><span style="color: #666;">创建时间：</span>${new Date(job.created_at).toLocaleString()}</div>
                    ${job.metrics && job.metrics.mode === 'system_level' ? `<div><span style="color: #666;">训练模式：</span><span style="color: #7c3aed; font-weight: 600;">System-Level 多 Agent SFT</span></div>` : job.metrics && job.metrics.mode === 'system_level_dpo' ? `<div><span style="color: #666;">训练模式：</span><span style="color: #8b5cf6; font-weight: 600;">System-Level 多 Agent DPO</span></div>` : job.metrics && job.metrics.mode === 'system_level_grpo' ? `<div><span style="color: #666;">训练模式：</span><span style="color: #f59e0b; font-weight: 600;">System-Level 多 Agent GRPO</span></div>` : job.metrics && job.metrics.mode === 'mixed' ? `<div><span style="color: #666;">训练模式：</span><span style="color: #ec4899; font-weight: 600;">Mixed Mode 多类型训练</span></div>` : `<div><span style="color: #666;">模型路径：</span>${job.model_path || '-'}</div>`}
                </div>
                
                ${job.hyperparameters ? `
                <div>
                    <h4 style="font-weight: 600; margin-bottom: 12px;">超参数</h4>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 16px; background: #f9fafb; border-radius: 8px; font-size: 13px;">
                        ${Object.entries(job.hyperparameters).map(([k, v]) => `
                            <div><span style="color: #666;">${k}:</span> ${v}</div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
                <!-- System-Level Multi-Agent 结果 (works for SFT, DPO, GRPO, Mixed) -->
                ${job.metrics && (job.metrics.mode === 'system_level' || job.metrics.mode === 'system_level_dpo' || job.metrics.mode === 'system_level_grpo' || job.metrics.mode === 'mixed') ? `
                <div>
                    <h4 style="font-weight: 600; margin-bottom: 12px;">🤖 多 Agent 训练结果</h4>
                    <div style="margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span>整体进度</span>
                            <span id="progress-text-${jobId}">${job.metrics.overall_message || ''}</span>
                        </div>
                        <div style="background: #e5e7eb; border-radius: 4px; height: 8px; overflow: hidden;">
                            <div id="progress-bar-${jobId}" style="background: linear-gradient(90deg, #7c3aed, #3b82f6); height: 100%; width: ${((job.metrics.agents || []).filter(a => a.status === 'completed').length / Math.max(1, (job.metrics.agents || []).length)) * 100}%; transition: width 0.5s ease;"></div>
                        </div>
                    </div>
                    <div style="display: grid; gap: 12px;">
                        ${(job.metrics.agents || []).map(agent => `
                        <div style="padding: 16px; background: ${agent.status === 'completed' ? '#f6ffed' : agent.status === 'failed' ? '#fff2f0' : '#e6f7ff'}; border: 1px solid ${agent.status === 'completed' ? '#b7eb8f' : agent.status === 'failed' ? '#ffccc7' : '#91d5ff'}; border-radius: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-weight: 600; font-size: 15px;">🤖 ${agent.agent_id}</span>
                                <span style="padding: 4px 8px; border-radius: 4px; font-size: 12px; background: ${agent.status === 'completed' ? '#52c41a' : agent.status === 'failed' ? '#ff4d4f' : '#1890ff'}; color: white;">
                                    ${agent.status === 'completed' ? '✅ 完成' : agent.status === 'failed' ? '❌ 失败' : '🔄 训练中'}
                                </span>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 13px;">
                                <div><span style="color: #666;">模型:</span> ${agent.model || '-'}</div>
                                ${agent.final_loss ? `<div><span style="color: #666;">Loss:</span> <span style="color: #3b82f6; font-weight: 600;">${agent.final_loss.toFixed(4)}</span></div>` : ''}
                                ${agent.elapsed_seconds ? `<div><span style="color: #666;">耗时:</span> ${(agent.elapsed_seconds / 60).toFixed(1)} 分钟</div>` : ''}
                                ${agent.loss_weight ? `<div><span style="color: #666;">Loss 权重:</span> ${agent.loss_weight}</div>` : ''}
                                ${agent.output_dir ? `<div style="grid-column: span 2; font-size: 11px;"><span style="color: #666;">输出:</span> <code style="background: white; padding: 2px 4px; border-radius: 2px;">${agent.output_dir}</code></div>` : ''}
                                ${agent.error ? `<div style="grid-column: span 2; color: #ff4d4f; font-size: 12px;">${agent.error}</div>` : ''}
                            </div>
                        </div>
                        `).join('')}
                    </div>
                </div>
                ` : `
                <!-- 单模型训练进度 -->
                <div id="training-viz-${jobId}">
                    <h4 style="font-weight: 600; margin-bottom: 12px;">📊 训练进度</h4>
                    <div style="padding: 16px; background: #f9fafb; border-radius: 8px;">
                        <div style="margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <span>训练进度</span>
                                <span id="progress-text-${jobId}">${job.progress || 0}%</span>
                            </div>
                            <div style="background: #e5e7eb; border-radius: 4px; height: 8px; overflow: hidden;">
                                <div id="progress-bar-${jobId}" style="background: linear-gradient(90deg, #3b82f6, #8b5cf6); height: 100%; width: ${job.progress || 0}%; transition: width 0.5s ease;"></div>
                            </div>
                        </div>
                        ${job.metrics && job.metrics.current_loss ? `
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                            <div style="background: white; padding: 12px; border-radius: 8px; text-align: center;">
                                <div style="color: #666; font-size: 12px; margin-bottom: 4px;">当前 Loss</div>
                                <div id="current-loss-${jobId}" style="font-size: 20px; font-weight: 600; color: #3b82f6;">${job.metrics.current_loss.toFixed(4)}</div>
                            </div>
                            <div style="background: white; padding: 12px; border-radius: 8px; text-align: center;">
                                <div style="color: #666; font-size: 12px; margin-bottom: 4px;">学习率</div>
                                <div id="current-lr-${jobId}" style="font-size: 20px; font-weight: 600; color: #8b5cf6;">${job.metrics.learning_rate ? job.metrics.learning_rate.toExponential(2) : '-'}</div>
                            </div>
                            <div style="background: white; padding: 12px; border-radius: 8px; text-align: center;">
                                <div style="color: #666; font-size: 12px; margin-bottom: 4px;">已训练步数</div>
                                <div id="current-step-${jobId}" style="font-size: 20px; font-weight: 600; color: #10b981;">${job.metrics.step || 0}</div>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                `}
                
                <!-- 训练日志 -->
                <div>
                    <h4 style="font-weight: 600; margin-bottom: 12px;">📝 训练日志 <span style="font-size: 12px; color: #666; font-weight: normal;">(实时更新)</span></h4>
                    <pre id="training-logs-${jobId}" style="background: #1a1a1a; color: #e5e5e5; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px; max-height: 400px; overflow-y: auto; white-space: pre-wrap; word-wrap: break-word;">${job.logs || '等待训练开始...'}</pre>
                </div>
                
                ${job.status === 'completed' ? `
                <div style="padding: 16px; background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px;">
                    <h4 style="font-weight: 600; margin-bottom: 12px; color: #52c41a;">🎉 训练完成</h4>
                    ${job.metrics && (job.metrics.mode === 'system_level' || job.metrics.mode === 'system_level_dpo' || job.metrics.mode === 'system_level_grpo' || job.metrics.mode === 'mixed') ? `
                        <p style="margin-bottom: 12px;">${job.metrics.overall_message || '所有 Agent 训练完成'}</p>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            ${(job.metrics.agents || []).filter(a => a.output_dir).map(a => `
                                <button class="btn btn-secondary" style="padding: 8px 16px; font-size: 13px;" onclick="deployTrainedModel(${jobId}, '${a.agent_id}')">🚀 部署 ${a.agent_id}</button>
                            `).join('')}
                        </div>
                    ` : `
                        <p>模型已保存至: <code>${job.output_dir || '-'}</code></p>
                        <button class="btn btn-primary" style="margin-top: 8px;" onclick="deployTrainedModel(${jobId})">🚀 部署模型</button>
                    `}
                    <button class="btn btn-secondary" style="margin-top: 12px; background: #8b5cf6; color: white; border-color: #8b5cf6;" onclick="validateTrainingJob(${jobId})">📝 验证蒸馏效果</button>
                </div>
                ` : ''}
                
                ${job.status === 'failed' ? `
                <div style="padding: 16px; background: #fff2f0; border: 1px solid #ffccc7; border-radius: 8px;">
                    <h4 style="font-weight: 600; margin-bottom: 12px; color: #ff4d4f;">❌ 训练失败</h4>
                    <p style="margin-bottom: 12px; color: #666;">${job.error_message || job.metrics && job.metrics.overall_message || '训练过程中发生错误'}</p>
                </div>
                ` : ''}
            </div>
        `;
        
        document.getElementById('training-detail-modal').style.display = 'block';
        
        // 如果任务正在运行，启动自动刷新
        if (job.status === 'running') {
            startTrainingDetailRefresh(jobId);
        }
    } catch (error) {
        alert('加载详情失败: ' + error.message);
    }
}

function startTrainingDetailRefresh(jobId) {
    // 清除之前的定时器
    if (trainingDetailInterval) {
        clearInterval(trainingDetailInterval);
    }
    
    // 每 3 秒刷新一次
    trainingDetailInterval = setInterval(async () => {
        try {
            const job = await apiRequest(`/api/training/jobs/${jobId}`);
            
            // 更新状态
            const statusEl = document.getElementById(`job-status-${jobId}`);
            if (statusEl) statusEl.textContent = job.status;
            
            // 更新进度
            const progressEl = document.getElementById(`job-progress-${jobId}`);
            if (progressEl) progressEl.textContent = `${job.progress || 0}%`;
            
            // 更新进度条
            const progressBar = document.getElementById(`progress-bar-${jobId}`);
            if (progressBar) {
                if (job.metrics && (job.metrics.mode === 'system_level' || job.metrics.mode === 'system_level_dpo' || job.metrics.mode === 'system_level_grpo' || job.metrics.mode === 'mixed')) {
                    const agents = job.metrics.agents || [];
                    const completedCount = agents.filter(a => a.status === 'completed').length;
                    const totalCount = Math.max(1, agents.length);
                    const pct = (completedCount / totalCount) * 100;
                    progressBar.style.width = `${pct}%`;
                    const progressText = document.getElementById(`progress-text-${jobId}`);
                    if (progressText) progressText.textContent = job.metrics.overall_message || '';
                } else {
                    progressBar.style.width = `${job.progress || 0}%`;
                }
            }
            
            // 更新进度文本
            const progressText = document.getElementById(`progress-text-${jobId}`);
            if (progressText) progressText.textContent = `${job.progress || 0}%`;
            
            // 更新指标
            if (job.metrics) {
                const lossEl = document.getElementById(`current-loss-${jobId}`);
                if (lossEl && job.metrics.current_loss) lossEl.textContent = job.metrics.current_loss.toFixed(4);
                
                const lrEl = document.getElementById(`current-lr-${jobId}`);
                if (lrEl && job.metrics.learning_rate) lrEl.textContent = job.metrics.learning_rate.toExponential(2);
                
                const stepEl = document.getElementById(`current-step-${jobId}`);
                if (stepEl && job.metrics.step) stepEl.textContent = job.metrics.step;
            }
            
            // 更新日志
            const logsEl = document.getElementById(`training-logs-${jobId}`);
            if (logsEl && job.logs) {
                logsEl.textContent = job.logs;
                // 自动滚动到底部
                logsEl.scrollTop = logsEl.scrollHeight;
            }
            
            // 如果训练完成或失败，停止刷新
            if (job.status === 'completed' || job.status === 'failed') {
                clearInterval(trainingDetailInterval);
                trainingDetailInterval = null;
                // 重新加载页面以显示完成/失败状态
                viewTrainingJob(jobId);
            }
        } catch (error) {
            console.error('刷新训练详情失败:', error);
        }
    }, 3000);
}

function closeTrainingDetailModal() {
    document.getElementById('training-detail-modal').style.display = 'none';
    // 清除定时器
    if (trainingDetailInterval) {
        clearInterval(trainingDetailInterval);
        trainingDetailInterval = null;
    }
    currentTrainingJobId = null;
}

async function deployModel(jobId) {
    if (!confirm('确定要部署训练好的模型到系统配置吗？\n这将更新配置中的模型路径。')) {
        return;
    }
    
    try {
        showLoading();
        const result = await apiRequest(`/api/training/jobs/${jobId}/deploy`, {
            method: 'POST',
            body: JSON.stringify({
                create_new_version: true
            })
        });
        
        alert('模型部署成功！\n更新的Agents: ' + result.updated_agents.join(', '));
        closeTrainingDetailModal();
    } catch (error) {
        alert('部署失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function deployTrainedModel(jobId, agentId) {
    const agentLabel = agentId ? ` (${agentId})` : '';
    if (!confirm(`确定要部署训练好的模型${agentLabel}到系统配置吗？`)) {
        return;
    }
    
    try {
        showLoading();
        const body = { create_new_version: true };
        if (agentId) body.agent_id = agentId;
        
        const result = await apiRequest(`/api/training/jobs/${jobId}/deploy`, {
            method: 'POST',
            body: JSON.stringify(body)
        });
        
        alert(`模型部署成功！\n更新的Agents: ${result.updated_agents.join(', ')}`);
        closeTrainingDetailModal();
    } catch (error) {
        alert('部署失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function validateTrainingJob(jobId) {
    if (!confirm('确定要验证蒸馏效果吗？\n将加载模型进行三向对比：基座模型 vs 微调模型 vs 教师GT')) {
        return;
    }
    
    const content = document.getElementById('training-detail-content');
    if (content) {
        content.innerHTML += `
            <div id="validation-progress" style="margin-top: 20px; padding: 20px; background: #f0f9ff; border: 1px solid #91caff; border-radius: 12px;">
                <h4 style="color: #0958d9;">⏳ 蒸馏验证中...</h4>
                <div id="validation-logs" style="font-family: monospace; font-size: 12px; color: #555; max-height: 200px; overflow-y: auto; margin-top: 12px; padding: 8px; background: #fafafa; border-radius: 6px;"></div>
            </div>
        `;
    }
    
    try {
        const startResult = await apiRequest(`/api/training/jobs/${jobId}/validate`, {
            method: 'POST',
            body: JSON.stringify({})
        });
        
        const validationKey = startResult.validation_key;
        
        // Poll for status
        let completed = false;
        let attempts = 0;
        const maxAttempts = 180; // 3 minutes at 1s interval
        
        while (!completed && attempts < maxAttempts) {
            await new Promise(r => setTimeout(r, 1000));
            attempts++;
            
            try {
                const status = await apiRequest(
                    `/api/training/jobs/${jobId}/validate/status?validation_key=${validationKey}`
                );
                
                // Update logs
                const logsDiv = document.getElementById('validation-logs');
                if (logsDiv && status.logs) {
                    logsDiv.innerHTML = status.logs.map(l => `<div>${l}</div>`).join('');
                    logsDiv.scrollTop = logsDiv.scrollHeight;
                }
                
                if (status.status === 'completed' || status.status === 'failed') {
                    completed = true;
                    if (status.result) {
                        renderValidationReportInline(jobId, status.result);
                    } else if (status.status === 'failed') {
                        const progressDiv = document.getElementById('validation-progress');
                        if (progressDiv) {
                            progressDiv.innerHTML = `
                                <h4 style="color: #ff4d4f;">❌ 验证失败</h4>
                                <p style="color: #666;">${status.error || 'Unknown error'}</p>
                            `;
                        }
                    }
                }
            } catch (e) {
                // Polling error, continue
            }
        }
        
        if (!completed) {
            const progressDiv = document.getElementById('validation-progress');
            if (progressDiv) {
                progressDiv.innerHTML += `<p style="color: #faad14;">⏱️ 验证仍在进行中，请稍后查看结果</p>`;
            }
        }
        
    } catch (error) {
        alert('验证启动失败: ' + error.message);
        const progressDiv = document.getElementById('validation-progress');
        if (progressDiv) {
            progressDiv.innerHTML = `<h4 style="color: #ff4d4f;">❌ 验证失败: ${error.message}</h4>`;
        }
    }
}

function renderValidationReportInline(jobId, report) {
    const content = document.getElementById('training-detail-content');
    if (!content) return;
    
    // Remove progress div
    const progressDiv = document.getElementById('validation-progress');
    if (progressDiv) progressDiv.remove();
    
    const summary = report.summary || {};
    const agentResults = report.agent_results || {};
    const phases = report.phases || {};
    
    const avgBefore = (summary.avg_before_score || 0) * 100;
    const avgAfter = (summary.avg_after_score || 0) * 100;
    const avgImp = (summary.avg_improvement || 0) * 100;
    const grade = summary.quality_grade || '';
    
    let gradeColor = '#52c41a';
    if (grade.startsWith('C') || grade.startsWith('D')) gradeColor = '#faad14';
    else if (grade.startsWith('F')) gradeColor = '#ff4d4f';
    
    const impColor = avgImp > 0 ? '#52c41a' : avgImp < 0 ? '#ff4d4f' : '#666';
    const impSign = avgImp > 0 ? '+' : '';
    
    let html = `
        <div style="margin-top: 20px; padding: 20px; background: linear-gradient(135deg, #f0f9ff 0%, #e6f7ff 100%); border: 1px solid #91caff; border-radius: 12px;">
            <h4 style="font-weight: 600; margin-bottom: 16px; color: #0958d9;">📊 蒸馏效果三向对比报告</h4>
            
            <!-- Phase Status -->
            <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
    `;
    
    // Phase status badges
    const phaseNames = {
        'teacher_gt': '👨‍🏫 教师GT',
        'student_before': '🔵 基座模型',
        'student_after': '🟢 微调模型'
    };
    for (const [key, label] of Object.entries(phaseNames)) {
        const phase = phases[key] || {};
        const statusIcon = phase.status === 'completed' ? '✅' : phase.status === 'failed' ? '❌' : '⏳';
        const bgColor = phase.status === 'completed' ? '#f6ffed' : phase.status === 'failed' ? '#fff2f0' : '#fffbe6';
        html += `<span style="padding: 4px 10px; background: ${bgColor}; border-radius: 12px; font-size: 12px;">${statusIcon} ${label}</span>`;
    }
    
    html += `</div>
            
            <!-- Overall Summary -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;">
                <div style="text-align: center; padding: 14px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size: 22px; font-weight: 700; color: #1890ff;">${avgBefore.toFixed(1)}%</div>
                    <div style="font-size: 11px; color: #666; margin-top: 4px;">🔵 基座模型得分</div>
                </div>
                <div style="text-align: center; padding: 14px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size: 22px; font-weight: 700; color: #52c41a;">${avgAfter.toFixed(1)}%</div>
                    <div style="font-size: 11px; color: #666; margin-top: 4px;">🟢 微调模型得分</div>
                </div>
                <div style="text-align: center; padding: 14px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size: 22px; font-weight: 700; color: ${impColor};">${impSign}${avgImp.toFixed(1)}%</div>
                    <div style="font-size: 11px; color: #666; margin-top: 4px;">📈 提升幅度</div>
                </div>
                <div style="text-align: center; padding: 14px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="font-size: 22px; font-weight: 700; color: ${gradeColor};">${grade}</div>
                    <div style="font-size: 11px; color: #666; margin-top: 4px;">🏆 质量等级</div>
                </div>
            </div>
    `;
    
    // Per-agent comparison
    const agentIds = Object.keys(agentResults);
    if (agentIds.length > 0) {
        html += `<h5 style="font-weight: 600; margin-bottom: 12px; color: #333;">🤖 各 Agent 对比详情</h5>`;
        
        for (const agentId of agentIds) {
            const ar = agentResults[agentId];
            const imp = ar.improvement || {};
            const beforeScore = (imp.before_score || 0) * 100;
            const afterScore = (imp.after_score || 0) * 100;
            const absImp = (imp.absolute || 0) * 100;
            const agentImpColor = absImp > 0 ? '#52c41a' : absImp < 0 ? '#ff4d4f' : '#666';
            const agentImpSign = absImp > 0 ? '+' : '';
            
            const beforeMetrics = ar.before ? ar.before.metrics : null;
            const afterMetrics = ar.after ? ar.after.metrics : null;
            
            html += `
                <div style="padding: 14px; background: white; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="font-weight: 700; font-size: 14px;">🤖 ${agentId}</span>
                        <span style="font-weight: 700; color: ${agentImpColor}; font-size: 14px;">
                            ${agentImpSign}${absImp.toFixed(1)}%
                        </span>
                    </div>
                    
                    <!-- Before/After comparison bars -->
                    <div style="margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <span style="width: 80px; font-size: 11px; color: #666;">🔵 基座模型</span>
                            <div style="flex: 1; background: #e5e7eb; border-radius: 3px; height: 8px; overflow: hidden;">
                                <div style="background: #1890ff; height: 100%; width: ${beforeScore}%; transition: width 0.5s;"></div>
                            </div>
                            <span style="width: 50px; text-align: right; font-size: 11px; font-weight: 600;">${beforeScore.toFixed(1)}%</span>
                        </div>
                        <div style="display: flex; align-items: center;">
                            <span style="width: 80px; font-size: 11px; color: #666;">🟢 微调模型</span>
                            <div style="flex: 1; background: #e5e7eb; border-radius: 3px; height: 8px; overflow: hidden;">
                                <div style="background: #52c41a; height: 100%; width: ${afterScore}%; transition: width 0.5s;"></div>
                            </div>
                            <span style="width: 50px; text-align: right; font-size: 11px; font-weight: 600;">${afterScore.toFixed(1)}%</span>
                        </div>
                    </div>
                    
                    <!-- Metrics grid -->
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;">
            `;
            
            // Before metrics
            if (beforeMetrics) {
                html += `
                    <div style="padding: 8px; background: #f0f7ff; border-radius: 6px; font-size: 11px;">
                        <div style="font-weight: 600; color: #1890ff; margin-bottom: 4px;">🔵 基座模型</div>
                        <div>EM: ${((beforeMetrics.exact_match_rate||0)*100).toFixed(1)}% | F1: ${((beforeMetrics.avg_token_f1||0)*100).toFixed(1)}%</div>
                        <div>ROUGE-L: ${((beforeMetrics.avg_rouge_l||0)*100).toFixed(1)}%</div>
                    </div>
                `;
            } else {
                html += `<div style="padding: 8px; background: #f5f5f5; border-radius: 6px; font-size: 11px; color: #999;">🔵 基座模型: 无数据</div>`;
            }
            
            // After metrics
            if (afterMetrics) {
                html += `
                    <div style="padding: 8px; background: #f6ffed; border-radius: 6px; font-size: 11px;">
                        <div style="font-weight: 600; color: #52c41a; margin-bottom: 4px;">🟢 微调模型</div>
                        <div>EM: ${((afterMetrics.exact_match_rate||0)*100).toFixed(1)}% | F1: ${((afterMetrics.avg_token_f1||0)*100).toFixed(1)}%</div>
                        <div>ROUGE-L: ${((afterMetrics.avg_rouge_l||0)*100).toFixed(1)}%</div>
                    </div>
                `;
            } else {
                html += `<div style="padding: 8px; background: #f5f5f5; border-radius: 6px; font-size: 11px; color: #999;">🟢 微调模型: 无数据</div>`;
            }
            
            html += `</div>`;
            
            // Sample outputs comparison
            const teacherSamples = ar.teacher_gt_samples || [];
            const beforeOutputs = ar.before ? (ar.before.outputs || []) : [];
            const afterOutputs = ar.after ? (ar.after.outputs || []) : [];
            
            if (teacherSamples.length > 0 || beforeOutputs.length > 0 || afterOutputs.length > 0) {
                html += `
                    <details style="margin-top: 8px;">
                        <summary style="cursor: pointer; font-size: 12px; color: #1890ff; font-weight: 500;">📝 查看输出对比示例</summary>
                        <div style="margin-top: 8px; max-height: 300px; overflow-y: auto;">
                `;
                const maxSamples = Math.min(3, teacherSamples.length, Math.max(beforeOutputs.length, afterOutputs.length));
                for (let i = 0; i < maxSamples; i++) {
                    html += `
                        <div style="padding: 8px; background: #fafafa; border-radius: 6px; margin-bottom: 6px; font-size: 11px;">
                            <div style="font-weight: 600; margin-bottom: 4px;">样本 #${i + 1}</div>
                            <div style="color: #722ed1;">👨‍🏫 Teacher: ${teacherSamples[i] || '-'}</div>
                            ${beforeOutputs[i] ? `<div style="color: #1890ff;">🔵 Before: ${beforeOutputs[i]}</div>` : ''}
                            ${afterOutputs[i] ? `<div style="color: #52c41a;">🟢 After: ${afterOutputs[i]}</div>` : ''}
                        </div>
                    `;
                }
                html += `</div></details>`;
            }
            
            html += `</div>`;
        }
    }
    
    // Best/most improved agents
    if (summary.best_agent || summary.most_improved_agent) {
        html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px;">';
        if (summary.best_agent) {
            const bestResult = agentResults[summary.best_agent] || {};
            const bestScore = ((bestResult.improvement || {}).after_score || 0) * 100;
            html += `<div style="padding: 8px; background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 6px; font-size: 13px;">🏆 最佳: <b>${summary.best_agent}</b> (${bestScore.toFixed(1)}%)</div>`;
        }
        if (summary.most_improved_agent) {
            const impResult = agentResults[summary.most_improved_agent] || {};
            const impVal = ((impResult.improvement || {}).absolute || 0) * 100;
            html += `<div style="padding: 8px; background: #e6f7ff; border: 1px solid #91caff; border-radius: 6px; font-size: 13px;">📈 最大提升: <b>${summary.most_improved_agent}</b> (+${impVal.toFixed(1)}%)</div>`;
        }
        html += '</div>';
    }
    
    html += '</div>';
    
    // Append to existing content
    content.innerHTML += html;
}

async function testDeployedModel(jobId) {
    // 测试微调后的模型
    try {
        const job = await apiRequest(`/api/training/jobs/${jobId}`);
        
        if (!job.config_id) {
            alert('无法找到对应的配置');
            return;
        }
        
        // 显示测试对话框
        const testInput = prompt('请输入测试问题（例如：计算 25 + 36）：', '计算 25 + 36');
        if (!testInput) return;
        
        showLoading();
        
        // 使用微调后的配置执行
        const result = await apiRequest(`/api/configs/${job.config_id}/execute`, {
            method: 'POST',
            body: JSON.stringify({
                input: { user_request: testInput },
                max_steps: 100
            })
        });
        
        if (result.success) {
            // 构建测试结果HTML
            let outputHtml = `
                <div style="background: #f0f9ff; border: 1px solid #91caff; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                    <h4 style="color: #0958d9; margin-bottom: 12px;">🧪 微调后模型测试结果</h4>
                    <div style="margin-bottom: 12px;"><strong>输入：</strong>${testInput}</div>
                    <div style="background: white; padding: 12px; border-radius: 4px; margin-bottom: 12px;">
                        <div style="font-weight: 600; margin-bottom: 8px;">执行步骤：</div>
            `;
            
            result.execution_log.forEach((step, idx) => {
                outputHtml += `
                    <div style="padding: 8px; background: #f5f5f5; border-radius: 4px; margin-bottom: 8px; font-size: 13px;">
                        <div style="color: #666;">Step ${idx + 1}: ${step.agent_id}</div>
                        <div style="margin-top: 4px;">${JSON.stringify(step.output).substring(0, 200)}...</div>
                    </div>
                `;
            });
            
            outputHtml += `
                    </div>
                    <div style="background: #f6ffed; border: 1px solid #b7eb8f; padding: 12px; border-radius: 4px;">
                        <div style="font-weight: 600; color: #52c41a;">最终结果：</div>
                        <div style="margin-top: 8px; font-size: 16px;">${JSON.stringify(result.final_state || result.final_output || '无输出')}</div>
                    </div>
                </div>
                <div style="display: flex; gap: 12px;">
                    <button class="btn btn-primary" onclick="testDeployedModel(${jobId})">再次测试</button>
                    <button class="btn btn-secondary" onclick="closeTestResultModal()">关闭</button>
                </div>
            `;
            
            // 检查是否在训练详情模态框中
            const trainingDetailContent = document.getElementById('training-detail-content');
            if (trainingDetailContent && document.getElementById('training-detail-modal').style.display === 'block') {
                trainingDetailContent.innerHTML = outputHtml;
            } else {
                // 创建或更新测试结果模态框
                showTestResultModal(outputHtml);
            }
        } else {
            alert('测试执行失败: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('测试失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function showTestResultModal(contentHtml) {
    let modal = document.getElementById('test-result-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'test-result-modal';
        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; overflow-y: auto;';
        document.body.appendChild(modal);
    }
    
    modal.innerHTML = `
        <div style="background: white; margin: 50px auto; max-width: 800px; border-radius: 12px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);">
            <div style="padding: 24px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                <h2 style="margin: 0; font-size: 18px; font-weight: 600;">测试结果</h2>
                <button onclick="closeTestResultModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #6b7280;">×</button>
            </div>
            <div style="padding: 24px; max-height: 70vh; overflow-y: auto;">
                ${contentHtml}
            </div>
        </div>
    `;
    modal.style.display = 'block';
}

function closeTestResultModal() {
    const modal = document.getElementById('test-result-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function closeTrainingDetailModal() {
    document.getElementById('training-detail-modal').style.display = 'none';
}

async function stopTrainingJob(jobId) {
    if (!confirm('确定要停止这个训练任务吗？')) return;
    
    try {
        await apiRequest(`/api/training/jobs/${jobId}/stop`, { method: 'POST' });
        loadTrainingJobs();
        alert('训练任务已停止');
    } catch (error) {
        alert('停止失败: ' + error.message);
    }
}

async function deleteTrainingJob(jobId) {
    if (!confirm('确定要删除这个训练任务吗？\n删除后无法恢复！')) return;
    
    try {
        await apiRequest(`/api/training/jobs/${jobId}`, { method: 'DELETE' });
        loadTrainingJobs();
        alert('训练任务已删除');
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// ============== Initialize ==============
document.addEventListener('DOMContentLoaded', () => {
    // Load current user
    apiRequest('/api/auth/me').then(data => {
        if (data) {
            document.getElementById('username').textContent = data.username;
        }
    });
    
    // Load initial page data
    loadDashboardData();
    
    // Load training jobs if on training page
    if (document.getElementById('sft-task-table-body')) {
        loadTrainingJobs();
    }
});

// Load training jobs when switching to training page
const originalSwitchPage = switchPage;
switchPage = function(page) {
    originalSwitchPage(page);
    if (page === 'training') {
        loadTrainingJobs();
        loadEvaluableJobs();
    }
    if (page === 'data') {
        loadDatasets();
    }
};

// ============== Model Picker ==============

const MODELSCOPE_MODELS = [
    { name: 'Qwen2.5-0.5B-Instruct', path: 'Qwen/Qwen2.5-0.5B-Instruct', size: '0.5B', cat: 'qwen', desc: '轻量级指令模型，适合快速测试' },
    { name: 'Qwen2.5-1.5B-Instruct', path: 'Qwen/Qwen2.5-1.5B-Instruct', size: '1.5B', cat: 'qwen', desc: '小型指令模型，平衡性能与资源' },
    { name: 'Qwen2.5-7B-Instruct', path: 'Qwen/Qwen2.5-7B-Instruct', size: '7B', cat: 'qwen', desc: '中型指令模型，性能较好' },
    { name: 'Qwen2.5-14B-Instruct', path: 'Qwen/Qwen2.5-14B-Instruct', size: '14B', cat: 'qwen', desc: '较大型模型，高质量输出' },
    { name: 'Qwen2.5-32B-Instruct', path: 'Qwen/Qwen2.5-32B-Instruct', size: '32B', cat: 'qwen', desc: '大型模型，卓越性能' },
    { name: 'Qwen2.5-72B-Instruct', path: 'Qwen/Qwen2.5-72B-Instruct', size: '72B', cat: 'qwen', desc: '超大型模型，最佳质量' },
    { name: 'Qwen2.5-Coder-7B-Instruct', path: 'Qwen/Qwen2.5-Coder-7B-Instruct', size: '7B', cat: 'qwen', desc: '代码专长模型' },
    { name: 'Qwen2.5-Math-7B-Instruct', path: 'Qwen/Qwen2.5-Math-7B-Instruct', size: '7B', cat: 'qwen', desc: '数学专长模型' },
    { name: 'Llama-3.1-8B-Instruct', path: 'LLM-Research/Meta-Llama-3.1-8B-Instruct', size: '8B', cat: 'llama', desc: 'Meta Llama 3.1 8B' },
    { name: 'Llama-3.1-70B-Instruct', path: 'LLM-Research/Meta-Llama-3.1-70B-Instruct', size: '70B', cat: 'llama', desc: 'Meta Llama 3.1 70B' },
    { name: 'internlm2_5-7b-chat', path: 'Shanghai_AI_Laboratory/internlm2_5-7b-chat', size: '7B', cat: 'other', desc: '书生·浦语 2.5 7B' },
    { name: 'internlm2_5-20b-chat', path: 'Shanghai_AI_Laboratory/internlm2_5-20b-chat', size: '20B', cat: 'other', desc: '书生·浦语 2.5 20B' },
    { name: 'glm-4-9b-chat', path: 'ZhipuAI/glm-4-9b-chat', size: '9B', cat: 'other', desc: '智谱 GLM-4 9B' },
    { name: 'Yi-1.5-9B-Chat', path: '01-ai/Yi-1.5-9B-Chat', size: '9B', cat: 'other', desc: '零一万物 Yi 1.5 9B' },
    { name: 'Baichuan2-13B-Chat', path: 'baichuan-inc/Baichuan2-13B-Chat', size: '13B', cat: 'other', desc: '百川 Baichuan2 13B' },
];

function showModelPicker() {
    document.getElementById('model-picker-modal').style.display = 'block';
    renderModelList(MODELSCOPE_MODELS);
}

function closeModelPicker() {
    document.getElementById('model-picker-modal').style.display = 'none';
}

function renderModelList(models) {
    const container = document.getElementById('model-list');
    if (!models.length) {
        container.innerHTML = '<div style="text-align: center; color: #8c8c8c; padding: 20px;">无匹配模型</div>';
        return;
    }
    container.innerHTML = models.map(m => `
        <div style="padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; display: flex; justify-content: space-between; align-items: center;" 
             onmouseover="this.style.borderColor='#1890ff';this.style.background='#f0f9ff'" 
             onmouseout="this.style.borderColor='#e5e7eb';this.style.background='white'" 
             onclick="selectModel('${m.path}')">
            <div>
                <div style="font-weight: 600; font-size: 14px;">${m.name}</div>
                <div style="font-size: 12px; color: #666; margin-top: 2px;">${m.desc}</div>
                <div style="font-size: 11px; color: #999; margin-top: 2px;">${m.path}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="padding: 2px 8px; background: #f0f0f0; border-radius: 4px; font-size: 11px; font-weight: 600;">${m.size}</span>
                <span style="color: #1890ff; font-size: 12px;">选择 →</span>
            </div>
        </div>
    `).join('');
}

function filterModels(query) {
    const q = query.toLowerCase();
    const filtered = MODELSCOPE_MODELS.filter(m => 
        m.name.toLowerCase().includes(q) || m.path.toLowerCase().includes(q) || m.desc.includes(q)
    );
    renderModelList(filtered);
}

function filterModelsByCategory(cat) {
    if (cat === 'all') {
        renderModelList(MODELSCOPE_MODELS);
    } else {
        renderModelList(MODELSCOPE_MODELS.filter(m => m.cat === cat));
    }
}

function selectModel(path) {
    const textarea = document.getElementById('config-json');
    if (!textarea) return;
    
    // Insert model path at cursor position or replace selection
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    
    const insertText = `"${path}"`;
    textarea.value = text.substring(0, start) + insertText + text.substring(end);
    textarea.selectionStart = textarea.selectionEnd = start + insertText.length;
    textarea.focus();
    
    // Copy to clipboard as well
    navigator.clipboard.writeText(path).catch(() => {});
    
    closeModelPicker();
    alert(`已选择模型: ${path}\n\n路径已插入到 JSON 编辑器光标位置。\n请在 JSON 中将其用于 agent 的 "model.name_or_path" 字段。`);
}

function insertCustomModel() {
    const path = document.getElementById('custom-model-path').value.trim();
    if (!path) {
        alert('请输入模型路径');
        return;
    }
    selectModel(path);
}

// ============== Distillation Evaluation ==============

async function loadEvaluableJobs() {
    const container = document.getElementById('eval-jobs-list');
    if (!container) return;
    
    try {
        const jobs = await apiRequest('/api/training/jobs');
        const completedJobs = jobs.filter(j => j.status === 'completed');
        
        if (!completedJobs.length) {
            container.innerHTML = '<div style="padding: 40px; text-align: center; color: #8c8c8c;">暂无已完成的训练任务，无法进行蒸馏验证</div>';
            return;
        }
        
        const typeColors = {'sft': '#3b82f6', 'dpo': '#8b5cf6', 'grpo': '#f59e0b'};
        container.innerHTML = completedJobs.map(job => {
            const typeColor = typeColors[job.type] || '#666';
            const mode = job.metrics?.mode || 'single';
            const agentCount = job.metrics?.agents?.length || 0;
            return `
                <div style="padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <span style="font-weight: 600; font-size: 15px;">${job.name}</span>
                            <span style="padding: 2px 8px; border-radius: 4px; font-size: 11px; background: ${typeColor}20; color: ${typeColor}; font-weight: 600;">${(job.type || 'sft').toUpperCase()}</span>
                        </div>
                        <div style="font-size: 12px; color: #666;">
                            模式: ${mode} | Agents: ${agentCount} | 完成: ${new Date(job.updated_at || job.created_at).toLocaleString()}
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-secondary" style="padding: 8px 16px; font-size: 13px; background: #8b5cf6; color: white; border-color: #8b5cf6;" 
                                onclick="runValidation(${job.id})">
                            📊 运行验证
                        </button>
                        <button class="btn btn-secondary" style="padding: 8px 16px; font-size: 13px;" 
                                onclick="viewTrainingJob(${job.id})">
                            查看详情
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        container.innerHTML = `<div style="color: #ff4d4f; text-align: center; padding: 20px;">加载失败: ${error.message}</div>`;
    }
}

async function runValidation(jobId) {
    const content = document.getElementById('eval-report-content');
    const section = document.getElementById('eval-report-section');
    if (section) section.style.display = 'block';
    if (content) {
        content.innerHTML = `
            <div id="eval-validation-progress" style="padding: 20px; text-align: center;">
                <h4 style="color: #0958d9;">⏳ 蒸馏验证中，模型推理可能需要几分钟...</h4>
                <div id="eval-validation-logs" style="font-family: monospace; font-size: 12px; color: #555; max-height: 200px; overflow-y: auto; margin-top: 12px; padding: 8px; background: #fafafa; border-radius: 6px; text-align: left;"></div>
            </div>
        `;
    }
    
    try {
        const startResult = await apiRequest(`/api/training/jobs/${jobId}/validate`, {
            method: 'POST',
            body: JSON.stringify({})
        });
        
        const validationKey = startResult.validation_key;
        let completed = false;
        let attempts = 0;
        const maxAttempts = 300;
        
        while (!completed && attempts < maxAttempts) {
            await new Promise(r => setTimeout(r, 1000));
            attempts++;
            
            try {
                const status = await apiRequest(
                    `/api/training/jobs/${jobId}/validate/status?validation_key=${validationKey}`
                );
                
                const logsDiv = document.getElementById('eval-validation-logs');
                if (logsDiv && status.logs) {
                    logsDiv.innerHTML = status.logs.map(l => `<div>${l}</div>`).join('');
                    logsDiv.scrollTop = logsDiv.scrollHeight;
                }
                
                if (status.status === 'completed' || status.status === 'failed') {
                    completed = true;
                    if (status.result && typeof status.result === 'object' && status.result.summary) {
                        renderValidationReport(jobId, status.result, status.result);
                    } else if (status.status === 'failed') {
                        const progressDiv = document.getElementById('eval-validation-progress');
                        if (progressDiv) {
                            progressDiv.innerHTML = `<h4 style="color: #ff4d4f;">❌ 验证失败: ${status.error || 'Unknown'}</h4>`;
                        }
                    } else {
                        // completed but no result
                        const progressDiv = document.getElementById('eval-validation-progress');
                        if (progressDiv) {
                            progressDiv.innerHTML = `<h4 style="color: #faad14;">⚠️ 验证完成但无结果数据</h4>`;
                        }
                    }
                }
            } catch (e) { /* polling error */ }
        }
        
        if (!completed) {
            const progressDiv = document.getElementById('eval-validation-progress');
            if (progressDiv) {
                progressDiv.innerHTML += `<p style="color: #faad14;">⏱️ 验证仍在进行中，请稍后刷新查看</p>`;
            }
        }
    } catch (error) {
        alert('验证失败: ' + error.message);
    }
}

function renderValidationReport(jobId, report, result) {
    const section = document.getElementById('eval-report-section');
    const content = document.getElementById('eval-report-content');
    if (section) section.style.display = 'block';
    if (!content) return;
    
    const summary = report.summary || {};
    const agentResults = report.agent_results || {};
    const phases = report.phases || {};
    
    const avgBefore = (summary.avg_before_score || 0) * 100;
    const avgAfter = (summary.avg_after_score || 0) * 100;
    const avgImp = (summary.avg_improvement || 0) * 100;
    const grade = summary.quality_grade || '';
    
    let gradeColor = '#52c41a';
    if (grade.startsWith('C') || grade.startsWith('D')) gradeColor = '#faad14';
    else if (grade.startsWith('F')) gradeColor = '#ff4d4f';
    
    const impColor = avgImp > 0 ? '#52c41a' : avgImp < 0 ? '#ff4d4f' : '#666';
    const impSign = avgImp > 0 ? '+' : '';
    
    let html = `
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
            <div style="text-align: center; padding: 20px; background: #f0f7ff; border: 1px solid #91caff; border-radius: 8px;">
                <div style="font-size: 28px; font-weight: 700; color: #1890ff;">${avgBefore.toFixed(1)}%</div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">🔵 基座模型</div>
            </div>
            <div style="text-align: center; padding: 20px; background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px;">
                <div style="font-size: 28px; font-weight: 700; color: #52c41a;">${avgAfter.toFixed(1)}%</div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">🟢 微调模型</div>
            </div>
            <div style="text-align: center; padding: 20px; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;">
                <div style="font-size: 28px; font-weight: 700; color: ${impColor};">${impSign}${avgImp.toFixed(1)}%</div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">📈 提升幅度</div>
            </div>
            <div style="text-align: center; padding: 20px; background: #f5f3ff; border: 1px solid #d9d0ff; border-radius: 8px;">
                <div style="font-size: 28px; font-weight: 700; color: ${gradeColor};">${grade}</div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">🏆 质量等级</div>
            </div>
        </div>
    `;
    
    // Per-Agent Results
    const agentIds = Object.keys(agentResults);
    if (agentIds.length > 0) {
        html += `<h4 style="font-weight: 600; margin-bottom: 12px;">🤖 各 Agent 三向对比</h4><div style="display: grid; gap: 12px;">`;
        
        for (const agentId of agentIds) {
            const ar = agentResults[agentId];
            const imp = ar.improvement || {};
            const beforeScore = (imp.before_score || 0) * 100;
            const afterScore = (imp.after_score || 0) * 100;
            const absImp = (imp.absolute || 0) * 100;
            const agentImpColor = absImp > 0 ? '#52c41a' : absImp < 0 ? '#ff4d4f' : '#666';
            
            const beforeMetrics = ar.before ? ar.before.metrics : null;
            const afterMetrics = ar.after ? ar.after.metrics : null;
            
            html += `
                <div style="padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span style="font-weight: 600; font-size: 15px;">🤖 ${agentId}</span>
                        <span style="font-size: 14px; font-weight: 600; color: ${agentImpColor};">${absImp > 0 ? '+' : ''}${absImp.toFixed(1)}%</span>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <span style="width: 80px; font-size: 11px; color: #666;">🔵 基座</span>
                            <div style="flex: 1; background: #e5e7eb; border-radius: 3px; height: 8px; overflow: hidden;">
                                <div style="background: #1890ff; height: 100%; width: ${beforeScore}%;"></div>
                            </div>
                            <span style="width: 50px; text-align: right; font-size: 11px; font-weight: 600;">${beforeScore.toFixed(1)}%</span>
                        </div>
                        <div style="display: flex; align-items: center;">
                            <span style="width: 80px; font-size: 11px; color: #666;">🟢 微调</span>
                            <div style="flex: 1; background: #e5e7eb; border-radius: 3px; height: 8px; overflow: hidden;">
                                <div style="background: #52c41a; height: 100%; width: ${afterScore}%;"></div>
                            </div>
                            <span style="width: 50px; text-align: right; font-size: 11px; font-weight: 600;">${afterScore.toFixed(1)}%</span>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
                        <div style="padding: 8px; background: #f0f7ff; border-radius: 6px;">
                            ${beforeMetrics ? `EM: ${((beforeMetrics.exact_match_rate||0)*100).toFixed(1)}% | F1: ${((beforeMetrics.avg_token_f1||0)*100).toFixed(1)}% | R-L: ${((beforeMetrics.avg_rouge_l||0)*100).toFixed(1)}%` : '无数据'}
                        </div>
                        <div style="padding: 8px; background: #f6ffed; border-radius: 6px;">
                            ${afterMetrics ? `EM: ${((afterMetrics.exact_match_rate||0)*100).toFixed(1)}% | F1: ${((afterMetrics.avg_token_f1||0)*100).toFixed(1)}% | R-L: ${((afterMetrics.avg_rouge_l||0)*100).toFixed(1)}%` : '无数据'}
                        </div>
                    </div>
                </div>
            `;
        }
        html += '</div>';
    }
    
    if (summary.best_agent || summary.most_improved_agent) {
        html += `<div style="margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">`;
        if (summary.best_agent) {
            const bestR = agentResults[summary.best_agent] || {};
            const bestScore = ((bestR.improvement || {}).after_score || 0) * 100;
            html += `<div style="padding: 12px; background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px;">
                <div style="font-size: 12px; color: #52c41a; font-weight: 600;">🏆 最佳 Agent</div>
                <div style="font-weight: 600; margin-top: 4px;">${summary.best_agent}</div>
                <div style="font-size: 13px; color: #666;">得分: ${bestScore.toFixed(1)}%</div>
            </div>`;
        }
        if (summary.most_improved_agent) {
            const impR = agentResults[summary.most_improved_agent] || {};
            const impVal = ((impR.improvement || {}).absolute || 0) * 100;
            html += `<div style="padding: 12px; background: #e6f7ff; border: 1px solid #91caff; border-radius: 8px;">
                <div style="font-size: 12px; color: #1890ff; font-weight: 600;">📈 最大提升</div>
                <div style="font-weight: 600; margin-top: 4px;">${summary.most_improved_agent}</div>
                <div style="font-size: 13px; color: #666;">提升: +${impVal.toFixed(1)}%</div>
            </div>`;
        }
        html += '</div>';
    }
    
    if (result?.report_file) {
        html += `<div style="margin-top: 16px; font-size: 13px; color: #666;">报告文件: <code>${result.report_file}</code></div>`;
    }
    
    content.innerHTML = html;
    if (section) section.scrollIntoView({ behavior: 'smooth' });
}
