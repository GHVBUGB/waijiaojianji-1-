// 主要的前端JavaScript逻辑
// 这个文件包含了从index.html中提取的主要JavaScript代码

// 全局变量
let currentJobId = null;
let progressInterval = null;
let isProcessing = false;

// 初始化函数
function initializeApp() {
    // 页面加载完成后的初始化逻辑
    console.log('应用初始化完成');
    
    // 绑定事件监听器
    bindEventListeners();
    
    // 检查系统状态
    checkSystemStatus();
}

// 绑定事件监听器
function bindEventListeners() {
    // 文件上传相关事件
    const fileInput = document.getElementById('videoFile');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }
    
    // 处理按钮事件
    const processBtn = document.getElementById('processBtn');
    if (processBtn) {
        processBtn.addEventListener('click', handleProcessVideo);
    }
}

// 处理文件选择
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        console.log('选择的文件:', file.name);
        // 文件验证逻辑
        validateFile(file);
    }
}

// 文件验证
function validateFile(file) {
    const maxSize = 100 * 1024 * 1024; // 100MB
    const allowedTypes = ['video/mp4', 'video/mov', 'video/avi'];
    
    if (file.size > maxSize) {
        showError('文件大小不能超过100MB');
        return false;
    }
    
    if (!allowedTypes.includes(file.type)) {
        showError('只支持MP4、MOV、AVI格式的视频文件');
        return false;
    }
    
    return true;
}

// 处理视频
async function handleProcessVideo() {
    if (isProcessing) {
        showError('正在处理中，请稍候...');
        return;
    }
    
    const fileInput = document.getElementById('videoFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('请先选择视频文件');
        return;
    }
    
    if (!validateFile(file)) {
        return;
    }
    
    try {
        isProcessing = true;
        updateProcessButton(true);
        
        // 上传并处理视频
        await uploadAndProcessVideo(file);
        
    } catch (error) {
        console.error('处理失败:', error);
        showError('处理失败: ' + error.message);
    } finally {
        isProcessing = false;
        updateProcessButton(false);
    }
}

// 上传并处理视频
async function uploadAndProcessVideo(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // 获取配置参数
    const config = getProcessingConfig();
    Object.keys(config).forEach(key => {
        formData.append(key, config[key]);
    });
    
    const response = await fetch('/api/v1/video/process', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    if (result.success) {
        currentJobId = result.job_id;
        showSuccess('视频上传成功，开始处理...');
        startProgressMonitoring();
    } else {
        throw new Error(result.message || '处理失败');
    }
}

// 获取处理配置
function getProcessingConfig() {
    return {
        speech_service: document.getElementById('speechService')?.value || 'xunfei',
        video_service: document.getElementById('videoService')?.value || 'tencent',
        language_hint: document.getElementById('languageHint')?.value || 'zh-CN',
        subtitle_enabled: document.getElementById('subtitleEnabled')?.checked || false
    };
}

// 开始进度监控
function startProgressMonitoring() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    progressInterval = setInterval(async () => {
        try {
            await updateProgress();
        } catch (error) {
            console.error('进度更新失败:', error);
        }
    }, 2000);
}

// 更新进度
async function updateProgress() {
    if (!currentJobId) return;
    
    const response = await fetch(`/api/v1/video/progress/${currentJobId}`);
    const result = await response.json();
    
    if (result.success) {
        const progress = result.data;
        updateProgressBar(progress.progress, progress.message);
        
        if (progress.status === 'completed') {
            handleProcessingComplete(progress);
        } else if (progress.status === 'failed') {
            handleProcessingFailed(progress);
        }
    }
}

// 处理完成
function handleProcessingComplete(progress) {
    clearInterval(progressInterval);
    progressInterval = null;
    
    showSuccess('处理完成！');
    updateProgressBar(100, '处理完成');
    
    if (progress.output_url) {
        showDownloadLink(progress.output_url);
    }
    
    currentJobId = null;
}

// 处理失败
function handleProcessingFailed(progress) {
    clearInterval(progressInterval);
    progressInterval = null;
    
    showError('处理失败: ' + (progress.error || '未知错误'));
    updateProgressBar(0, '处理失败');
    
    currentJobId = null;
}

// 更新进度条
function updateProgressBar(percent, message) {
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text');
    
    if (progressBar) {
        progressBar.style.width = percent + '%';
    }
    
    if (progressText) {
        progressText.textContent = message || `${percent}%`;
    }
}

// 更新处理按钮状态
function updateProcessButton(processing) {
    const btn = document.getElementById('processBtn');
    if (btn) {
        btn.disabled = processing;
        btn.textContent = processing ? '处理中...' : '开始处理';
    }
}

// 显示下载链接
function showDownloadLink(url) {
    const container = document.getElementById('downloadContainer');
    if (container) {
        container.innerHTML = `
            <div class="download-section">
                <h3>✅ 处理完成</h3>
                <a href="${url}" class="download-btn" download>
                    📥 下载处理后的视频
                </a>
            </div>
        `;
        container.style.display = 'block';
    }
}

// 显示成功消息
function showSuccess(message) {
    showMessage(message, 'success');
}

// 显示错误消息
function showError(message) {
    showMessage(message, 'error');
}

// 显示消息
function showMessage(message, type) {
    const container = document.getElementById('messageContainer') || createMessageContainer();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    
    container.appendChild(messageDiv);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 3000);
}

// 创建消息容器
function createMessageContainer() {
    const container = document.createElement('div');
    container.id = 'messageContainer';
    container.className = 'message-container';
    document.body.appendChild(container);
    return container;
}

// 检查系统状态
async function checkSystemStatus() {
    try {
        const response = await fetch('/api/v1/health/');
        const result = await response.json();
        
        if (result.success) {
            console.log('系统状态正常');
        } else {
            console.warn('系统状态异常:', result.message);
        }
    } catch (error) {
        console.error('无法获取系统状态:', error);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initializeApp);