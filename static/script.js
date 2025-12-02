// 全局变量
let currentExperimentId = null;
// 分页状态
let paginationState = {
    incubator: { page: 1, per_page: 10 },
    experiments: { page: 1, per_page: 10 },
    archive: { page: 1, per_page: 10 }
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadIncubator();
    loadExperiments();
    loadArchive();
    
    // 定期刷新数据
    setInterval(() => {
        loadStats();
        loadExperiments();
    }, 30000); // 每30秒刷新一次
});

// 显示主页面
function showMainPage() {
    document.getElementById('detail-page').style.display = 'none';
    document.getElementById('main-container').style.display = 'block';
}

// 显示详情页面
function showDetailPage() {
    document.getElementById('main-container').style.display = 'none';
    document.getElementById('detail-page').style.display = 'block';
}

// 返回主页面
function goBack() {
    showMainPage();
}

// 标签页切换
function showTab(tabName) {
    // 确保显示主页面
    showMainPage();
    
    // 隐藏所有标签页
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 移除所有按钮的active状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 显示选中的标签页
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // 激活对应的按钮
    event.target.classList.add('active');
    
    // 刷新对应数据
    if (tabName === 'incubator') {
        loadIncubator();
    } else if (tabName === 'experiments') {
        loadExperiments();
    } else if (tabName === 'archive') {
        loadArchive();
    }
}

// 加载统计信息
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        document.getElementById('incubator-count').textContent = data.incubator_count;
        document.getElementById('active-count').textContent = data.active_count;
        document.getElementById('archive-count').textContent = data.archive_count;
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 加载兴趣孵化池
async function loadIncubator(page = null) {
    try {
        const currentPage = page || paginationState.incubator.page;
        const perPage = paginationState.incubator.per_page;
        const response = await fetch(`/api/incubator?page=${currentPage}&per_page=${perPage}`);
        const data = await response.json();
        
        // 判断是分页结果还是列表结果（兼容旧接口）
        let ideas, pagination;
        if (data.items && data.total !== undefined) {
            ideas = data.items;
            pagination = data;
            paginationState.incubator.page = currentPage;
        } else {
            ideas = data;
            pagination = null;
        }
        
        const container = document.getElementById('incubator-list');
        
        if (ideas.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💡</div>
                    <div class="empty-state-text">兴趣孵化池是空的，快添加一些想法吧！</div>
                </div>
            `;
            document.getElementById('incubator-pagination').innerHTML = '';
            return;
        }
        
        container.innerHTML = ideas.map(idea => `
            <div class="idea-card">
                <h3>${escapeHtml(idea.idea)}</h3>
                <div class="meta">创建时间: ${idea.created_at}</div>
                ${idea.notes ? `<div class="notes">${escapeHtml(idea.notes)}</div>` : ''}
                <div class="actions">
                    <button class="btn btn-primary btn-small" onclick="startExperimentFromIdea(${idea.id})">启动实验</button>
                    <button class="btn btn-danger btn-small" onclick="removeIdea(${idea.id})">删除</button>
                </div>
            </div>
        `).join('');
        
        // 渲染分页控件
        if (pagination) {
            renderPagination('incubator-pagination', pagination, function(newPage) {
                loadIncubator(newPage);
            });
        } else {
            document.getElementById('incubator-pagination').innerHTML = '';
        }
    } catch (error) {
        console.error('加载孵化池失败:', error);
    }
}

// 加载进行中的实验
async function loadExperiments(page = null) {
    try {
        const currentPage = page || paginationState.experiments.page;
        const perPage = paginationState.experiments.per_page;
        const response = await fetch(`/api/experiments?page=${currentPage}&per_page=${perPage}`);
        
        // 检查HTTP状态
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 检查是否有错误
        if (data.error) {
            console.error('加载实验失败:', data.error);
            document.getElementById('experiments-list').innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <div class="empty-state-text">加载失败: ${escapeHtml(data.error)}</div>
                </div>
            `;
            document.getElementById('experiments-pagination').innerHTML = '';
            return;
        }
        
        // 判断是分页结果还是列表结果（兼容旧接口）
        let experiments, pagination;
        if (data.items && data.total !== undefined) {
            experiments = data.items;
            pagination = data;
            paginationState.experiments.page = currentPage;
        } else if (Array.isArray(data)) {
            experiments = data;
            pagination = null;
        } else {
            console.warn('API返回的数据格式不正确:', data);
            experiments = [];
            pagination = null;
        }
        
        const container = document.getElementById('experiments-list');
        
        if (!container) {
            console.error('找不到experiments-list容器');
            return;
        }
        
        if (experiments.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🚀</div>
                    <div class="empty-state-text">当前没有进行中的实验</div>
                </div>
            `;
            document.getElementById('experiments-pagination').innerHTML = '';
            return;
        }
        
        container.innerHTML = experiments.map(exp => {
            const daysLeft = exp.days_left || 0;
            const daysClass = daysLeft > 0 ? 'positive' : 'negative';
            const daysText = daysLeft > 0 ? `剩余 ${daysLeft} 天` : `已过期 ${Math.abs(daysLeft)} 天`;
            
            return `
                <div class="experiment-card">
                    <h3>${escapeHtml(exp.idea)}</h3>
                    ${exp.notes ? `<div class="notes">${escapeHtml(exp.notes)}</div>` : ''}
                    <div class="goal">目标: ${escapeHtml(exp.goal)}</div>
                    <div class="meta">
                        <div class="meta-item">
                            <span class="meta-item-label">开始日期</span>
                            <span class="meta-item-value">${exp.start_date}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-item-label">结束日期</span>
                            <span class="meta-item-value">${exp.end_date}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-item-label">状态</span>
                            <span class="days-left ${daysClass}">${daysText}</span>
                        </div>
                    </div>
                    <div class="actions">
                        <button class="btn btn-primary btn-small" onclick="showExperimentDetail(${exp.id})">查看详情</button>
                        <button class="btn btn-success btn-small" onclick="showCompleteModal(${exp.id})">完成实验</button>
                    </div>
                </div>
            `;
        }).join('');
        
        // 渲染分页控件
        if (pagination) {
            renderPagination('experiments-pagination', pagination, function(newPage) {
                loadExperiments(newPage);
            });
        } else {
            document.getElementById('experiments-pagination').innerHTML = '';
        }
    } catch (error) {
        console.error('加载实验失败:', error);
        const container = document.getElementById('experiments-list');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <div class="empty-state-text">加载失败: ${escapeHtml(error.message)}</div>
                </div>
            `;
        }
        document.getElementById('experiments-pagination').innerHTML = '';
    }
}

// 加载项目档案馆
async function loadArchive(page = null) {
    try {
        const currentPage = page || paginationState.archive.page;
        const perPage = paginationState.archive.per_page;
        const response = await fetch(`/api/archive?page=${currentPage}&per_page=${perPage}`);
        const data = await response.json();
        
        // 判断是分页结果还是列表结果（兼容旧接口）
        let archive, pagination;
        if (data.items && data.total !== undefined) {
            archive = data.items;
            pagination = data;
            paginationState.archive.page = currentPage;
        } else {
            archive = data;
            pagination = null;
        }
        
        const container = document.getElementById('archive-list');
        
        if (archive.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📦</div>
                    <div class="empty-state-text">项目档案馆是空的</div>
                </div>
            `;
            document.getElementById('archive-pagination').innerHTML = '';
            return;
        }
        
        container.innerHTML = archive.map(entry => `
            <div class="archive-card">
                <h3>${escapeHtml(entry.idea)}</h3>
                <div class="time-range">${entry.start_date} → ${entry.end_date} | 完成于: ${entry.completed_at}</div>
                ${entry.notes ? `<div class="notes">${escapeHtml(entry.notes)}</div>` : ''}
                <div class="goal">目标: ${escapeHtml(entry.goal)}</div>
                ${entry.skill_learned || entry.experience || entry.connection ? `
                    <div class="review">
                        ${entry.skill_learned ? `
                            <div class="review-item">
                                <div class="review-item-label">💡 技能收获</div>
                                <div class="review-item-content">${escapeHtml(entry.skill_learned)}</div>
                            </div>
                        ` : ''}
                        ${entry.experience ? `
                            <div class="review-item">
                                <div class="review-item-label">😊 过程体验</div>
                                <div class="review-item-content">${escapeHtml(entry.experience)}</div>
                            </div>
                        ` : ''}
                        ${entry.connection ? `
                            <div class="review-item">
                                <div class="review-item-label">🔗 连接可能性</div>
                                <div class="review-item-content">${escapeHtml(entry.connection)}</div>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                <div class="actions" style="margin-top: 15px;">
                    <button class="btn btn-primary btn-small" onclick="showArchiveDetail(${entry.id})">查看详情</button>
                    <button class="btn btn-danger btn-small" onclick="deleteArchiveItem(${entry.id}, '${escapeHtml(entry.idea)}')">删除</button>
                </div>
            </div>
        `).join('');
        
        // 渲染分页控件
        if (pagination) {
            renderPagination('archive-pagination', pagination, function(newPage) {
                loadArchive(newPage);
            });
        } else {
            document.getElementById('archive-pagination').innerHTML = '';
        }
    } catch (error) {
        console.error('加载档案馆失败:', error);
    }
}

// 显示添加想法模态框
function showAddIdeaModal() {
    document.getElementById('add-idea-modal').classList.add('active');
    document.getElementById('idea-input').value = '';
    document.getElementById('idea-notes').value = '';
}

// 添加想法
async function addIdea(event) {
    event.preventDefault();
    
    const idea = document.getElementById('idea-input').value.trim();
    const notes = document.getElementById('idea-notes').value.trim();
    
    if (!idea) {
        alert('想法描述不能为空');
        return;
    }
    
    try {
        const response = await fetch('/api/incubator', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ idea, notes })
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeModal('add-idea-modal');
            loadIncubator();
            loadStats();
        } else {
            alert('添加失败: ' + result.error);
        }
    } catch (error) {
        alert('添加失败: ' + error.message);
    }
}

// 删除想法
async function removeIdea(ideaId) {
    if (!confirm('确定要删除这个想法吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/incubator/${ideaId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            loadIncubator();
            loadStats();
        }
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// 从想法启动实验
function startExperimentFromIdea(ideaId) {
    // 先加载想法列表到选择框
    loadIdeasToSelect().then(() => {
        document.getElementById('idea-select').value = ideaId;
        onIdeaSelectChange();
        showStartExperimentModal();
    });
}

// 显示启动实验模态框
async function showStartExperimentModal() {
    await loadIdeasToSelect();
    document.getElementById('start-experiment-modal').classList.add('active');
    document.getElementById('experiment-idea').value = '';
    document.getElementById('experiment-goal').value = '';
    document.getElementById('experiment-days').value = '21';
    document.getElementById('idea-select').value = '';
}

// 加载想法到选择框
async function loadIdeasToSelect() {
    try {
        // 获取所有想法（不分页），用于下拉选择
        const response = await fetch('/api/incubator?per_page=1000');
        const data = await response.json();
        
        // 判断是分页结果还是列表结果（兼容旧接口）
        let ideas;
        if (data.items && data.total !== undefined) {
            ideas = data.items;
        } else {
            ideas = data;
        }
        
        const select = document.getElementById('idea-select');
        select.innerHTML = '<option value="">-- 或直接输入新想法 --</option>';
        
        ideas.forEach(idea => {
            const option = document.createElement('option');
            option.value = idea.id;
            option.textContent = idea.idea;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('加载想法列表失败:', error);
    }
}

// 想法选择变化
function onIdeaSelectChange() {
    const select = document.getElementById('idea-select');
    const ideaInput = document.getElementById('experiment-idea');
    
    if (select.value) {
        // 从API获取想法详情
        fetch('/api/incubator?per_page=1000')
            .then(res => res.json())
            .then(data => {
                // 判断是分页结果还是列表结果
                let ideas;
                if (data.items && data.total !== undefined) {
                    ideas = data.items;
                } else {
                    ideas = data;
                }
                
                const idea = ideas.find(i => i.id == select.value);
                if (idea) {
                    ideaInput.value = idea.idea;
                }
            });
    }
}

// 启动实验
async function startExperiment(event) {
    event.preventDefault();
    
    const ideaSelect = document.getElementById('idea-select').value;
    const idea = document.getElementById('experiment-idea').value.trim();
    const goal = document.getElementById('experiment-goal').value.trim();
    const days = parseInt(document.getElementById('experiment-days').value) || 21;
    
    if (!idea || !goal) {
        alert('想法和目标不能为空');
        return;
    }
    
    try {
        const response = await fetch('/api/experiments', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                idea_id: ideaSelect || null,
                idea: idea,
                goal: goal,
                budget: 0,
                days: days
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeModal('start-experiment-modal');
            loadExperiments();
            loadIncubator();
            loadStats();
            alert('实验已启动！');
        } else {
            alert('启动失败: ' + result.error);
        }
    } catch (error) {
        alert('启动失败: ' + error.message);
    }
}

// 显示实验详情
async function showExperimentDetail(expId) {
    try {
        const response = await fetch(`/api/experiments/${expId}`);
        const exp = await response.json();
        
        if (exp.error) {
            alert(exp.error);
            return;
        }
        
        const daysLeft = exp.days_left || 0;
        const daysClass = daysLeft > 0 ? 'positive' : 'negative';
        const daysText = daysLeft > 0 ? `剩余 ${daysLeft} 天` : `已过期 ${Math.abs(daysLeft)} 天`;
        
        let progressHtml = '';
        if (exp.progress_notes && exp.progress_notes.length > 0) {
            progressHtml = '<div class="progress-notes-section"><h3>📝 进度记录</h3>';
            exp.progress_notes.forEach(note => {
                progressHtml += `
                    <div class="progress-note">
                        <div class="progress-note-date">${note.date}</div>
                        <div class="progress-note-content">${escapeHtml(note.note)}</div>
                    </div>
                `;
            });
            progressHtml += '</div>';
        } else {
            progressHtml = '<div class="progress-notes-section"><p class="empty-note">暂无进度记录</p></div>';
        }
        
        document.getElementById('detail-page-title').textContent = exp.idea;
        document.getElementById('detail-page-content').innerHTML = `
            <div class="detail-card">
                ${exp.notes ? `
                <div class="detail-section">
                    <h3>📝 备注</h3>
                    <p class="detail-text">${escapeHtml(exp.notes)}</p>
                </div>
                ` : ''}
                <div class="detail-section">
                    <h3>🎯 实验目标</h3>
                    <p class="detail-text">${escapeHtml(exp.goal)}</p>
                </div>
                
                <div class="detail-section">
                    <h3>📊 基本信息</h3>
                    <div class="meta-grid">
                        <div class="meta-item">
                            <span class="meta-item-label">开始日期</span>
                            <span class="meta-item-value">${exp.start_date}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-item-label">结束日期</span>
                            <span class="meta-item-value">${exp.end_date}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-item-label">状态</span>
                            <span class="days-left ${daysClass}">${daysText}</span>
                        </div>
                    </div>
                </div>
                
                ${progressHtml}
                
                <div class="detail-actions">
                    <button class="btn btn-primary" onclick="showAddProgressModal(${exp.id})">添加进度记录</button>
                    <button class="btn btn-success" onclick="showCompleteModal(${exp.id})">完成实验</button>
                </div>
            </div>
        `;
        
        currentExperimentId = expId;
        showDetailPage();
    } catch (error) {
        alert('加载详情失败: ' + error.message);
    }
}

// 显示归档项目详情
async function showArchiveDetail(archiveId) {
    try {
        const response = await fetch(`/api/archive/${archiveId}`);
        const entry = await response.json();
        
        if (entry.error) {
            alert(entry.error);
            return;
        }
        
        let progressHtml = '';
        if (entry.progress_notes && entry.progress_notes.length > 0) {
            progressHtml = '<div class="progress-notes-section"><h3>📝 进度记录</h3>';
            entry.progress_notes.forEach(note => {
                progressHtml += `
                    <div class="progress-note">
                        <div class="progress-note-date">${note.date}</div>
                        <div class="progress-note-content">${escapeHtml(note.note)}</div>
                    </div>
                `;
            });
            progressHtml += '</div>';
        } else {
            progressHtml = '<div class="progress-notes-section"><p class="empty-note">暂无进度记录</p></div>';
        }
        
        document.getElementById('detail-page-title').textContent = entry.idea;
        document.getElementById('detail-page-content').innerHTML = `
            <div class="detail-card">
                ${entry.notes ? `
                <div class="detail-section">
                    <h3>📝 备注</h3>
                    <p class="detail-text">${escapeHtml(entry.notes)}</p>
                </div>
                ` : ''}
                <div class="detail-section">
                    <h3>🎯 实验目标</h3>
                    <p class="detail-text">${escapeHtml(entry.goal)}</p>
                </div>
                
                <div class="detail-section">
                    <h3>📅 时间信息</h3>
                    <div class="meta-grid">
                        <div class="meta-item">
                            <span class="meta-item-label">开始日期</span>
                            <span class="meta-item-value">${entry.start_date}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-item-label">结束日期</span>
                            <span class="meta-item-value">${entry.end_date}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-item-label">完成时间</span>
                            <span class="meta-item-value">${entry.completed_at}</span>
                        </div>
                    </div>
                </div>
                
                ${progressHtml}
                
                ${entry.skill_learned || entry.experience || entry.connection ? `
                    <div class="detail-section">
                        <h3>📋 复盘总结</h3>
                        ${entry.skill_learned ? `
                            <div class="review-item-full">
                                <div class="review-item-label">💡 技能收获</div>
                                <div class="review-item-content">${escapeHtml(entry.skill_learned)}</div>
                            </div>
                        ` : ''}
                        ${entry.experience ? `
                            <div class="review-item-full">
                                <div class="review-item-label">😊 过程体验</div>
                                <div class="review-item-content">${escapeHtml(entry.experience)}</div>
                            </div>
                        ` : ''}
                        ${entry.connection ? `
                            <div class="review-item-full">
                                <div class="review-item-label">🔗 连接可能性</div>
                                <div class="review-item-content">${escapeHtml(entry.connection)}</div>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                
                <div class="detail-actions">
                    <button class="btn btn-danger" onclick="deleteArchiveItem(${entry.id}, '${escapeHtml(entry.idea)}')">删除项目</button>
                </div>
            </div>
        `;
        
        showDetailPage();
    } catch (error) {
        alert('加载详情失败: ' + error.message);
    }
}

// 删除归档项目
async function deleteArchiveItem(archiveId, ideaName) {
    if (!confirm(`确定要删除项目"${ideaName}"吗？\n\n此操作不可恢复！`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/archive/${archiveId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 如果当前在详情页面，返回主页面
            if (document.getElementById('detail-page').style.display !== 'none') {
                showMainPage();
            }
            loadArchive();
            loadStats();
            alert('项目已删除');
        } else {
            alert('删除失败: ' + result.error);
        }
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// 显示添加进度记录模态框
function showAddProgressModal(expId) {
    currentExperimentId = expId;
    document.getElementById('progress-exp-id').value = expId;
    document.getElementById('progress-note-input').value = '';
    document.getElementById('add-progress-modal').classList.add('active');
    // 聚焦到输入框
    setTimeout(() => {
        document.getElementById('progress-note-input').focus();
    }, 100);
}

// 提交进度记录
async function submitProgress(event) {
    event.preventDefault();
    
    const expId = parseInt(document.getElementById('progress-exp-id').value);
    const note = document.getElementById('progress-note-input').value.trim();
    
    if (!note) {
        alert('进度记录不能为空');
        return;
    }
    
    closeModal('add-progress-modal');
    await addProgress(expId, note);
}

// 添加进度记录
async function addProgress(expId, note) {
    try {
        const response = await fetch(`/api/experiments/${expId}/progress`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ note })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 如果当前在详情页面，刷新详情
            if (document.getElementById('detail-page').style.display !== 'none') {
                showExperimentDetail(expId);
            } else {
                loadExperiments();
            }
        } else {
            alert('添加失败: ' + result.error);
        }
    } catch (error) {
        alert('添加失败: ' + error.message);
    }
}

// 显示完成实验模态框
function showCompleteModal(expId) {
    currentExperimentId = expId;
    document.getElementById('complete-exp-id').value = expId;
    document.getElementById('complete-skill').value = '';
    document.getElementById('complete-experience').value = '';
    document.getElementById('complete-connection').value = '';
    document.getElementById('complete-experiment-modal').classList.add('active');
}

// 完成实验
async function completeExperiment(event) {
    event.preventDefault();
    
    const expId = parseInt(document.getElementById('complete-exp-id').value);
    const skill = document.getElementById('complete-skill').value.trim();
    const experience = document.getElementById('complete-experience').value.trim();
    const connection = document.getElementById('complete-connection').value.trim();
    
    try {
        const response = await fetch(`/api/experiments/${expId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                skill,
                experience,
                connection
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeModal('complete-experiment-modal');
            showMainPage(); // 返回主页面
            loadExperiments();
            loadArchive();
            loadStats();
            alert('实验已归档！');
        } else {
            alert('归档失败: ' + result.error);
        }
    } catch (error) {
        alert('归档失败: ' + error.message);
    }
}

// 关闭模态框
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 点击模态框外部关闭
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
    }
}

// 渲染分页控件
function renderPagination(containerId, pagination, onPageChange) {
    const container = document.getElementById(containerId);
    if (!container || pagination.pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    const { page, pages, total } = pagination;
    let html = '<div class="pagination-info">';
    html += `共 ${total} 条，第 ${page}/${pages} 页`;
    html += '</div><div class="pagination-buttons">';
    
    // 创建唯一的事件处理函数名
    const handlerName = `paginationHandler_${containerId.replace('-', '_')}`;
    window[handlerName] = onPageChange;
    
    // 上一页按钮
    if (page > 1) {
        html += `<button class="pagination-btn" onclick="${handlerName}(${page - 1})">上一页</button>`;
    } else {
        html += '<button class="pagination-btn disabled" disabled>上一页</button>';
    }
    
    // 页码按钮（显示当前页前后各2页）
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(pages, page + 2);
    
    if (startPage > 1) {
        html += `<button class="pagination-btn" onclick="${handlerName}(1)">1</button>`;
        if (startPage > 2) {
            html += '<span class="pagination-ellipsis">...</span>';
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        if (i === page) {
            html += `<button class="pagination-btn active">${i}</button>`;
        } else {
            html += `<button class="pagination-btn" onclick="${handlerName}(${i})">${i}</button>`;
        }
    }
    
    if (endPage < pages) {
        if (endPage < pages - 1) {
            html += '<span class="pagination-ellipsis">...</span>';
        }
        html += `<button class="pagination-btn" onclick="${handlerName}(${pages})">${pages}</button>`;
    }
    
    // 下一页按钮
    if (page < pages) {
        html += `<button class="pagination-btn" onclick="${handlerName}(${page + 1})">下一页</button>`;
    } else {
        html += '<button class="pagination-btn disabled" disabled>下一页</button>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

