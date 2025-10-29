import React, { useState, useEffect } from 'react';
import './SurveyConfig.css';
import { SurveyStep, SurveyTemplate, SurveyBranch } from '../types';
import { ApiService } from '../services/api';

interface SurveyConfigProps {
  templateId?: string;
  onBack?: () => void;
  onTemplateSaved?: () => void;
}

const SurveyConfig: React.FC<SurveyConfigProps> = ({ templateId, onBack, onTemplateSaved }) => {
  const [theme, setTheme] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [maxTurns, setMaxTurns] = useState(5);
  const [welcomeMessage, setWelcomeMessage] = useState('');
  const [steps, setSteps] = useState<SurveyStep[]>([
    { id: '1', content: '' }
  ]);
  const [endMessage, setEndMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentTemplateId, setCurrentTemplateId] = useState<string | null>(null);

  // 加载现有配置
  useEffect(() => {
    loadTemplate();
  }, []);

  const loadTemplate = async () => {
    try {
      if (templateId === 'new') {
        // 新增模式，初始化空表单
        setCurrentTemplateId(null);
        setTheme('');
        setSystemPrompt('');
        setMaxTurns(5);
        setWelcomeMessage('');
        setSteps([{ id: '1', content: '' }]);
        setEndMessage('');
        return;
      }
      
      const templates = await ApiService.getTemplates();
      let template = null;
      
      if (templateId) {
        // 根据传入的ID查找模板
        template = templates.find(t => t.id === templateId);
      } else if (templates.length > 0) {
        // 如果没有传入ID，使用第一个模板
        template = templates[0];
      }
      
      if (template) {
        setCurrentTemplateId(template.id);
        setTheme(template.theme || '');
        setSystemPrompt(template.system_prompt || '');
        setMaxTurns(template.max_turns || 5);
        setWelcomeMessage(template.welcome_message || '');
        setSteps(template.steps || [{ id: '1', content: '' }]);
        setEndMessage(template.end_message || '');
      }
    } catch (error) {
      console.error('加载模板失败:', error);
    }
  };

  const addStep = () => {
    const newId = (steps.length + 1).toString();
    setSteps([...steps, { id: newId, content: '' }]);
  };

  const removeStep = (id: string) => {
    if (steps.length > 1) {
      setSteps(steps.filter(step => step.id !== id));
    }
  };

  const updateStep = (id: string, content: string) => {
    setSteps(steps.map(step => 
      step.id === id ? { ...step, content } : step
    ));
  };

  const updateStepType = (id: string, type: 'linear' | 'condition') => {
    setSteps(steps.map(step => 
      step.id === id ? { ...step, type } : step
    ));
  };


  const updateStepDefaultBranch = (id: string, default_branch: string) => {
    setSteps(steps.map(step => 
      step.id === id ? { ...step, default_branch } : step
    ));
  };

  const addBranch = (stepId: string) => {
    setSteps(steps.map(step => 
      step.id === stepId 
        ? { 
            ...step, 
            branches: [...(step.branches || []), { id: '', condition: '', next_step: '' }]
          } 
        : step
    ));
  };


  const updateBranch = (stepId: string, branchIndex: number, field: keyof SurveyBranch, value: string) => {
    setSteps(steps.map(step => 
      step.id === stepId 
        ? { 
            ...step, 
            branches: step.branches?.map((branch, index) => 
              index === branchIndex ? { ...branch, [field]: value } : branch
            ) || []
          } 
        : step
    ));
  };



  const saveTemplate = async () => {
    setIsLoading(true);
    try {
      // 生成临时ID用于新增模式
      const templateId = currentTemplateId || 'temp-' + Date.now();
      
      const template: SurveyTemplate = {
        id: templateId,
        theme: theme,
        system_prompt: systemPrompt,
        max_turns: maxTurns,
        welcome_message: welcomeMessage,
        steps: steps,
        end_message: endMessage
      };

      let success = false;
      if (currentTemplateId) {
        // 编辑模式
        success = await ApiService.updateTemplateById(currentTemplateId, template);
      } else {
        // 新增模式
        success = await ApiService.createTemplate(template);
      }
      
      if (success) {
        alert(currentTemplateId ? '调研模板更新成功！' : '调研模板创建成功！');
        // 通知父组件刷新模板列表
        if (onTemplateSaved) {
          onTemplateSaved();
        }
      } else {
        alert('保存失败，请重试');
      }
    } catch (error) {
      console.error('保存模板失败:', error);
      alert('保存失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="survey-config">
      <div className="config-header">
        <h2>{currentTemplateId ? '编辑调研模板' : '创建调研模板'}</h2>
        <p>{currentTemplateId ? '修改调研的开场白、步骤和结束语' : '配置新的调研模板'}</p>
      </div>

      <div className="config-content">
        {/* 基本信息配置 */}
        <div className="config-section basic-info-section">
          <h3>基本信息</h3>
          <div className="input-group">
            <label>调研主题 (最多50字符)</label>
            <input
              type="text"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="请输入调研主题..."
              maxLength={50}
            />
            <div className="char-count">
              {theme.length}/50
            </div>
          </div>
          <div className="input-group">
            <label>系统提示 (最多500字符)</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="请输入系统提示，用于给调研员创建角色..."
              maxLength={500}
              rows={4}
            />
            <div className="char-count">
              {systemPrompt.length}/500
            </div>
          </div>
          <div className="input-group">
            <label>最大轮数</label>
            <input
              type="number"
              value={maxTurns}
              onChange={(e) => setMaxTurns(parseInt(e.target.value) || 5)}
              min="1"
              max="20"
              placeholder="每个步骤最多可对话几轮"
            />
            <div className="input-hint">
              控制每个步骤最多可对话几轮
            </div>
          </div>
        </div>

        {/* 开场白配置 */}
        <div className="config-section steps-section">
          <h3>开场白配置</h3>
          <div className="input-group">
            <label>开场白内容 (最多100字符)</label>
            <textarea
              value={welcomeMessage}
              onChange={(e) => setWelcomeMessage(e.target.value)}
              placeholder="请输入调研开场白..."
              maxLength={100}
              rows={3}
            />
            <div className="char-count">
              {welcomeMessage.length}/100
            </div>
          </div>
        </div>

        {/* 步骤配置 */}
        <div className="config-section steps-section">
          <h3>调研步骤配置</h3>
          {steps.map((step, index) => (
            <div key={step.id} className="step-item">
              <div className="step-header">
                <span className="step-number">步骤 {index + 1}</span>
                <div className="step-type-selector">
                  <label>
                    <input
                      type="radio"
                      name={`step-type-${step.id}`}
                      value="linear"
                      checked={step.type === 'linear' || !step.type}
                      onChange={() => updateStepType(step.id, 'linear')}
                    />
                    顺序跳转
                  </label>
                  <label>
                    <input
                      type="radio"
                      name={`step-type-${step.id}`}
                      value="condition"
                      checked={step.type === 'condition'}
                      onChange={() => updateStepType(step.id, 'condition')}
                    />
                    条件跳转
                  </label>
                </div>
                {steps.length > 1 && (
                  <button 
                    type="button" 
                    className="remove-step"
                    onClick={() => removeStep(step.id)}
                  >
                    删除
                  </button>
                )}
              </div>
              <div className="input-group">
                <label>步骤内容 (最多500字符)</label>
                <textarea
                  value={step.content}
                  onChange={(e) => updateStep(step.id, e.target.value)}
                  placeholder="请输入调研步骤内容..."
                  maxLength={500}
                  rows={5}
                />
                <div className="char-count">
                  {step.content.length}/500
                </div>
              </div>


              {/* 条件跳转配置 */}
              {step.type === 'condition' && (
                <div className="condition-config">
                  <h4>跳转规则</h4>
                  
                  <div className="jump-rule-display">
                    <div className="rule-line condition-line">
                      <div className="condition-group">
                        <span className="rule-text">如果</span>
                        <input
                          type="text"
                          className="condition-input"
                          value={step.branches?.[0]?.condition || ''}
                          onChange={(e) => {
                            if (step.branches?.[0]) {
                              updateBranch(step.id, 0, 'condition', e.target.value);
                            } else {
                              addBranch(step.id);
                              setTimeout(() => {
                                updateBranch(step.id, 0, 'condition', e.target.value);
                              }, 100);
                            }
                          }}
                          placeholder="例如：用户提到了元气森林"
                        />
                      </div>
                    </div>
                    
                    <div className="rule-line jump-line">
                      <div className="jump-group">
                        <span className="rule-text">跳转到</span>
                        <select
                          className="step-select"
                          value={step.branches?.[0]?.next_step || ''}
                          onChange={(e) => {
                            if (step.branches?.[0]) {
                              updateBranch(step.id, 0, 'next_step', e.target.value);
                            } else {
                              addBranch(step.id);
                              setTimeout(() => {
                                updateBranch(step.id, 0, 'next_step', e.target.value);
                              }, 100);
                            }
                          }}
                        >
                          <option value="">请选择步骤</option>
                          {steps.map((s, index) => (
                            <option key={s.id} value={s.id}>
                              步骤{index + 1}
                            </option>
                          ))}
                        </select>
                      </div>
                      
                      <div className="jump-group">
                        <span className="rule-text">否则跳转到</span>
                        <select
                          className="step-select"
                          value={step.default_branch || ''}
                          onChange={(e) => updateStepDefaultBranch(step.id, e.target.value)}
                        >
                          <option value="">请选择步骤</option>
                          {steps.map((s, index) => (
                            <option key={s.id} value={s.id}>
                              步骤{index + 1}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
          <button 
            type="button" 
            className="add-step"
            onClick={addStep}
          >
            + 添加步骤
          </button>
        </div>


        {/* 结束语配置 */}
        <div className="config-section steps-section">
          <h3>结束语配置</h3>
          <div className="input-group">
            <label>结束语内容 (最多100字符)</label>
            <textarea
              value={endMessage}
              onChange={(e) => setEndMessage(e.target.value)}
              placeholder="请输入调研结束语..."
              maxLength={100}
              rows={3}
            />
            <div className="char-count">
              {endMessage.length}/100
            </div>
          </div>
        </div>
      </div>

      <div className="config-actions">
        {onBack && (
          <button 
            type="button" 
            className="back-button"
            onClick={onBack}
          >
            返回首页
          </button>
        )}
        <button 
          type="button" 
          className="save-button"
          onClick={saveTemplate}
          disabled={isLoading}
        >
          {isLoading ? '保存中...' : (currentTemplateId ? '更新配置' : '创建模板')}
        </button>
      </div>
    </div>
  );
};

export default SurveyConfig;
