// RSS2Pod 管理界面 JavaScript

const API_BASE = '/api';

// ============== API 客户端 ==============

async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const response = await fetch(url, { ...defaultOptions, ...options });
    const data = await response.json();
    
    if (!data.success) {
        throw new Error(data.error_message || 'Unknown error');
    }
    
    return data.data;
}

// ============== 页面加载 ==============

document.addEventListener('DOMContentLoaded', () => {
    loadGroups();
    
    // 刷新按钮
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadGroups();
    });
    
    // 模态框关闭
    const modal = document.getElementById('group-modal');
    const closeBtn = modal.querySelector('.close');
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
});

// ============== 加载 Groups ==============

async function loadGroups() {
    const loading = document.getElementById('loading');
    const errorMessage = document.getElementById('error-message');
    const groupsList = document.getElementById('groups-list');
    
    // 显示加载状态
    loading.style.display = 'block';
    errorMessage.style.display = 'none';
    groupsList.innerHTML = '';
    
    try {
        const groups = await fetchAPI('/groups');
        
        loading.style.display = 'none';
        
        if (!groups || groups.length === 0) {
            groupsList.innerHTML = `
                <div class="empty-state">
                    <h3>暂无播客组</h3>
                    <p>请使用 CLI 创建播客组: rss2pod group create</p>
                </div>
            `;
            return;
        }
        
        // 渲染 groups
        groupsList.innerHTML = groups.map(group => renderGroupCard(group)).join('');
        
        // 绑定事件
        groupsList.querySelectorAll('.btn-view').forEach(btn => {
            btn.addEventListener('click', () => showGroupDetail(btn.dataset.groupId));
        });
        
        groupsList.querySelectorAll('.btn-trigger').forEach(btn => {
            btn.addEventListener('click', () => triggerGroup(btn.dataset.groupId));
        });
        
        groupsList.querySelectorAll('.btn-rss').forEach(btn => {
            btn.addEventListener('click', () => openRSSFeed(btn.dataset.groupId));
        });
        
    } catch (error) {
        loading.style.display = 'none';
        errorMessage.style.display = 'block';
        errorMessage.querySelector('p').textContent = `加载失败: ${error.message}`;
    }
}

// ============== 渲染 Group Card ==============

function renderGroupCard(group) {
    const statusClass = group.enabled ? 'enabled' : 'disabled';
    const statusText = group.enabled ? '已启用' : '已禁用';
    
    return `
        <div class="group-card ${group.enabled ? '' : 'disabled'}">
            <div class="group-header">
                <span class="group-name">${escapeHtml(group.name)}</span>
                <span class="group-status ${statusClass}">${statusText}</span>
            </div>
            <div class="group-info">
                <div class="info-item">
                    <span class="info-label">描述</span>
                    <span class="info-value">${escapeHtml(group.description || '-')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">期数</span>
                    <span class="info-value">${group.episode_count || 0}</span>
                </div>
            </div>
            <div class="group-actions">
                <button class="btn btn-primary btn-view" data-group-id="${group.id}">查看详情</button>
                <button class="btn btn-success btn-trigger" data-group-id="${group.id}">触发生成</button>
                <button class="btn btn-secondary btn-rss" data-group-id="${group.id}">RSS 订阅</button>
            </div>
        </div>
    `;
}

// ============== 显示 Group 详情 ==============

async function showGroupDetail(groupId) {
    const modal = document.getElementById('group-modal');
    const detailDiv = document.getElementById('group-detail');
    
    modal.style.display = 'block';
    detailDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>加载中...</p></div>';
    
    try {
        const group = await fetchAPI(`/groups/${groupId}`);
        
        // 获取 RSS Feed URL
        const feedUrl = await fetchAPI(`/groups/${groupId}/feed-url`);
        
        detailDiv.innerHTML = `
            <h2>${escapeHtml(group.name)}</h2>
            <p><strong>描述:</strong> ${escapeHtml(group.description || '-')}</p>
            <p><strong>状态:</strong> ${group.enabled ? '已启用' : '已禁用'}</p>
            <p><strong>播客结构:</strong> ${group.podcast_structure === 'single' ? '单人' : '双人'}</p>
            <p><strong>英语学习:</strong> ${group.english_learning_mode === 'off' ? '关闭' : group.english_learning_mode}</p>
            <p><strong>音频速度:</strong> ${group.audio_speed}x</p>
            <p><strong>触发类型:</strong> ${group.trigger_type}</p>
            <p><strong>RSS 源数量:</strong> ${group.rss_sources ? group.rss_sources.length : 0}</p>
            <p><strong>期数:</strong> ${group.episode_count || 0}</p>
            <p><strong>RSS Feed:</strong> <a href="${feedUrl}" target="_blank">${escapeHtml(feedUrl)}</a></p>
            
            <h3>RSS 源列表</h3>
            ${group.rss_sources && group.rss_sources.length > 0 
                ? `<ul>${group.rss_sources.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>`
                : '<p>暂无 RSS 源</p>'}
            
            <h3>触发配置</h3>
            <pre>${JSON.stringify(group.trigger_config || {}, null, 2)}</pre>
        `;
        
    } catch (error) {
        detailDiv.innerHTML = `<p class="error-message">加载失败: ${error.message}</p>`;
    }
}

// ============== 触发生成 ==============

async function triggerGroup(groupId) {
    const btn = document.querySelector(`.btn-trigger[data-group-id="${groupId}"]`);
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '触发中...';
    
    try {
        const result = await fetchAPI(`/groups/${groupId}/trigger`, { method: 'POST' });
        showToast('已触发生成任务', 'success');
    } catch (error) {
        showToast(`触发失败: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// ============== 打开 RSS Feed ==============

function openRSSFeed(groupId) {
    window.open(`/feeds/${groupId}.xml`, '_blank');
}

// ============== Toast 通知 ==============

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// ============== 工具函数 ==============

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
