import { useState, useEffect } from 'react';
import ChatWindow from './components/ChatWindow';
import SurveyConfig from './components/SurveyConfig';
import { useSurvey } from './hooks/useSurvey';
import { SurveyTemplate } from './types';
import { ApiService } from './services/api';
import './App.css';

function App() {
  const {
    messages,
    isLoading,
    conversationId,
    startSurvey,
    sendMessage,
    resetSurvey
  } = useSurvey();

  const [showConfig, setShowConfig] = useState(false);
  const [templates, setTemplates] = useState<SurveyTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<SurveyTemplate | null>(null);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [configTemplateId, setConfigTemplateId] = useState<string | undefined>(undefined);

  // 加载模板列表
  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true);
      const templatesList = await ApiService.getTemplates();
      console.log('加载到的模板列表:', templatesList);
      setTemplates(templatesList);
      // 移除自动选择第一个模板的逻辑，让用户手动选择
    } catch (error) {
      console.error('加载模板列表失败:', error);
    } finally {
      setLoadingTemplates(false);
    }
  };

  const handleStartSurvey = () => {
    if (selectedTemplate) {
      startSurvey(selectedTemplate);
    }
  };

  const handleConfigClick = () => {
    if (selectedTemplate) {
      // 有选中主题时，进入编辑模式
      setConfigTemplateId(selectedTemplate.id);
    } else {
      // 没有选中主题时，进入新增模式
      setConfigTemplateId('new');
    }
    setShowConfig(true);
  };

  const handleTemplateSaved = () => {
    // 刷新模板列表
    loadTemplates();
    // 返回首页
    setShowConfig(false);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>SurveyEase - 智能调研助手</h1>
        <p>通过聊天的方式进行用户调研</p>
      </header>
      
      <main className="App-main">
        {showConfig ? (
          <SurveyConfig 
            templateId={configTemplateId}
            onBack={() => setShowConfig(false)}
            onTemplateSaved={handleTemplateSaved}
          />
        ) : !conversationId ? (
          <div className="welcome-section">
            <h2>选择调研主题</h2>
            <p>请选择一个调研主题开始对话</p>
            
            {loadingTemplates ? (
              <div className="loading-section">
                <p>正在加载调研主题...</p>
              </div>
            ) : templates.length === 0 ? (
              <div className="no-templates">
                <p>暂无可用调研主题</p>
                <button 
                  onClick={() => setShowConfig(true)}
                  className="config-button"
                >
                  创建调研主题
                </button>
              </div>
            ) : (
              <div className="template-selection">
                <div className="template-dropdown">
                  <label htmlFor="template-select">选择调研主题：</label>
                  <select 
                    id="template-select"
                    value={selectedTemplate?.id || ''}
                    onChange={(e) => {
                      const templateId = e.target.value;
                      const template = templates.find(t => t.id === templateId);
                      setSelectedTemplate(template || null);
                    }}
                    className="template-select"
                  >
                    <option value="">请选择调研主题...</option>
                    {templates.map((template, index) => (
                      <option key={template.id || index} value={template.id}>
                        {template.theme}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="welcome-actions">
                  <button 
                    onClick={handleStartSurvey} 
                    disabled={isLoading || !selectedTemplate}
                    className="start-button"
                  >
                    {isLoading ? '初始化中...' : '开始调研'}
                  </button>
                  <button 
                    onClick={handleConfigClick}
                    className="config-button"
                  >
                    调研配置
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <ChatWindow
            messages={messages}
            onSendMessage={sendMessage}
            isLoading={isLoading}
            onReset={resetSurvey}
          />
        )}
      </main>
    </div>
  );
}

export default App;
