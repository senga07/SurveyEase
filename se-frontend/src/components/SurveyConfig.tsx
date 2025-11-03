import React, { useState, useEffect, useRef } from 'react';
import './SurveyConfig.css';
import { SurveyStep, SurveyTemplate, SurveyVariable, Host } from '../types';
import { ApiService } from '../services/api';
import { highlightVariables } from '../utils';

// 字符计数组件
interface CharCountProps {
  current: number;
  max: number;
}

const CharCount: React.FC<CharCountProps> = ({ current, max }) => (
  <div className="char-count">
    {current}/{max}
  </div>
);

// 高亮输入框组件
interface HighlightInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
  type?: 'input' | 'textarea';
  rows?: number;
  className?: string;
}

const HighlightInput: React.FC<HighlightInputProps> = ({
  value,
  onChange,
  placeholder,
  maxLength,
  type = 'input',
  rows = 10,
  className = ''
}) => {
  const divRef = useRef<HTMLDivElement>(null);
  const isComposingRef = useRef(false);

  const handleInput = (e: React.FormEvent<HTMLDivElement>) => {
    if (isComposingRef.current) return;
    
    // 获取纯文本内容，保持换行符
    const text = e.currentTarget.innerText || '';
    if (maxLength && text.length > maxLength) {
      return;
    }
    onChange(text);
  };

  const handleCompositionStart = () => {
    isComposingRef.current = true;
  };

  const handleCompositionEnd = (e: React.CompositionEvent<HTMLDivElement>) => {
    isComposingRef.current = false;
    const text = e.currentTarget.innerText || '';
    if (maxLength && text.length > maxLength) {
      return;
    }
    onChange(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // 处理回车键
    if (e.key === 'Enter' && type === 'input') {
      e.preventDefault();
    }
    // 对于textarea类型，允许回车键创建换行
    if (e.key === 'Enter' && type === 'textarea') {
      // 让浏览器自然处理换行
    }
  };

  // 只在值真正改变时才更新内容，避免光标跳动
  const updateContent = () => {
    if (!divRef.current) return;
    
    const currentText = divRef.current.innerText || '';
    if (currentText !== value) {
      // 将换行符转换为HTML的<br>标签
      const textWithBreaks = value ? value.replace(/\n/g, '<br>') : '';
      const highlightedText = textWithBreaks ? highlightVariables(textWithBreaks) : '';
      divRef.current.innerHTML = highlightedText || '';
    }
  };

  // 使用 useEffect 来更新内容，避免在输入过程中重新渲染
  React.useEffect(() => {
    updateContent();
  }, [value]);

  return (
    <div className={`highlight-input-wrapper ${className}`}>
      <div
        ref={divRef}
        className={`highlight-editable ${type === 'textarea' ? 'highlight-textarea' : ''}`}
        contentEditable
        onInput={handleInput}
        onCompositionStart={handleCompositionStart}
        onCompositionEnd={handleCompositionEnd}
        onKeyDown={handleKeyDown}
        data-placeholder={placeholder}
        suppressContentEditableWarning={true}
        style={{
          minHeight: type === 'textarea' ? `${rows * 1.5}em` : 'auto',
          maxHeight: type === 'textarea' ? '200px' : 'none',
          overflowY: type === 'textarea' ? 'auto' : 'visible'
        }}
      />
    </div>
  );
};

interface SurveyConfigProps {
  templateId?: string;
  onBack?: () => void;
  onTemplateSaved?: () => void;
}

const SurveyConfig: React.FC<SurveyConfigProps> = ({ templateId, onBack, onTemplateSaved }) => {
  const [theme, setTheme] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [backgroundKnowledge, setBackgroundKnowledge] = useState('');
  const [maxTurns, setMaxTurns] = useState(5);
  const [welcomeMessage, setWelcomeMessage] = useState('');
  const [steps, setSteps] = useState<SurveyStep[]>([
    { id: '1', content: '' }
  ]);
  const [endMessage, setEndMessage] = useState('');
  const [variables, setVariables] = useState<SurveyVariable[]>([]);
  const [variableErrors, setVariableErrors] = useState<Record<number, string>>({});
  const [hosts, setHosts] = useState<Host[]>([]);
  const [selectedHostId, setSelectedHostId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentTemplateId, setCurrentTemplateId] = useState<string | null>(null);

  // 加载现有配置
  useEffect(() => {
    loadTemplate();
    loadHosts();
  }, []);

  const loadTemplate = async () => {
    try {
      if (templateId === 'new') {
        // 新增模式，初始化空表单
        setCurrentTemplateId(null);
        setTheme('');
        setSystemPrompt('');
        setBackgroundKnowledge('');
        setMaxTurns(5);
        setWelcomeMessage('');
        setSteps([{ id: '1', content: '' }]);
        setEndMessage('');
        setVariables([]);
        setVariableErrors({});
        setSelectedHostId('');
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
        setBackgroundKnowledge(template.background_knowledge || '');
        setMaxTurns(template.max_turns || 5);
        setWelcomeMessage(template.welcome_message || '');
        setSteps(template.steps || [{ id: '1', content: '' }]);
        setEndMessage(template.end_message || '');
        setVariables(template.variables || []);
        setVariableErrors({});
        setSelectedHostId(template.host_id || '');
      }
    } catch (error) {
      console.error('加载模板失败:', error);
    }
  };

  const loadHosts = async () => {
    try {
      const hostsList = await ApiService.getHosts();
      setHosts(hostsList);
    } catch (error) {
      console.error('加载主持人列表失败:', error);
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

  const addVariable = () => {
    const newVariable: SurveyVariable = {
      key: '',
      value: ''
    };
    setVariables([...variables, newVariable]);
  };

  const removeVariable = (index: number) => {
    const newVariables = variables.filter((_, i) => i !== index);
    setVariables(newVariables);
    
    // 更新错误状态，重新检查剩余的变量
    const updatedErrors: Record<number, string> = {};
    const keySet = new Set<string>();
    
    newVariables.forEach((variable, i) => {
      const trimmedKey = variable.key.trim();
      if (!trimmedKey) {
        return;
      }
      
      if (keySet.has(trimmedKey)) {
        updatedErrors[i] = '变量名称不能重复';
      } else {
        keySet.add(trimmedKey);
      }
    });
    
    setVariableErrors(updatedErrors);
  };

  const updateVariable = (index: number, field: keyof SurveyVariable, value: string) => {
    const updatedVariables = [...variables];
    updatedVariables[index] = { ...updatedVariables[index], [field]: value };
    setVariables(updatedVariables);

    // 如果更新的是key字段，检查是否重复
    if (field === 'key') {
      // 重新检查所有变量的重复性
      const updatedErrors: Record<number, string> = {};
      const keyMap = new Map<string, number[]>();
      
      // 收集所有非空的key及其索引
      updatedVariables.forEach((variable, i) => {
        const trimmedKey = variable.key.trim();
        if (trimmedKey) {
          if (!keyMap.has(trimmedKey)) {
            keyMap.set(trimmedKey, []);
          }
          keyMap.get(trimmedKey)!.push(i);
        }
      });
      
      // 标记重复的变量
      keyMap.forEach((indices) => {
        if (indices.length > 1) {
          indices.forEach(i => {
            updatedErrors[i] = '变量名称不能重复';
          });
        }
      });
      
      setVariableErrors(updatedErrors);
    }
  };

  const updateStepType = (id: string, type: 'linear' | 'condition') => {
    setSteps(steps.map(step => {
      if (step.id === id) {
        // 如果切换到顺序跳转，清空条件跳转相关的配置（条件和跳转步骤）
        if (type === 'linear') {
          return { 
            ...step, 
            type, 
            condition: undefined, 
            branches: undefined 
          };
        }
        // 如果切换到条件跳转，确保有默认的branches数组（两个空字符串表示未选择跳转步骤）
        return { 
          ...step, 
          type, 
          branches: step.branches || ['', ''] 
        };
      }
      return step;
    }));
  };


  const updateStepCondition = (id: string, condition: string) => {
    setSteps(steps.map(step =>
      step.id === id ? { ...step, condition } : step
    ));
  };

  const updateStepBranches = (id: string, branches: string[]) => {
    setSteps(steps.map(step =>
      step.id === id ? { ...step, branches } : step
    ));
  };



  const saveTemplate = async () => {
    // 保存前进行最终校验
    const errors: Record<number, string> = {};
    const keySet = new Set<string>();
    
    variables.forEach((variable, index) => {
      const trimmedKey = variable.key.trim();
      if (!trimmedKey) {
        // 跳过空key的变量
        return;
      }
      
      if (keySet.has(trimmedKey)) {
        errors[index] = '变量名称不能重复';
      } else {
        keySet.add(trimmedKey);
      }
    });
    
    // 如果有错误，更新错误状态并提示用户
    if (Object.keys(errors).length > 0) {
      setVariableErrors(errors);
      alert('存在重复的变量名称，请检查并修改后再保存');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      // 生成临时ID用于新增模式
      const templateId = currentTemplateId || 'temp-' + Date.now();
      
      const template: SurveyTemplate = {
        id: templateId,
        theme: theme,
        system_prompt: systemPrompt,
        background_knowledge: backgroundKnowledge,
        max_turns: maxTurns,
        welcome_message: welcomeMessage,
        steps: steps,
        end_message: endMessage,
        variables: variables,
        host_id: selectedHostId || undefined
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
        {/* 变量配置 */}
        <div className="config-section variables-section">
          <div className="section-header">
            <h3>
              <span className="section-icon">📝</span>
              变量配置
            </h3>
          </div>
          <p className="section-description">
            定义变量后，可以在主题、系统提示和步骤内容中使用 {`{{变量key}}`} 的格式进行引用
          </p>
          {variables.map((variable, index) => (
            <div key={index} className="variable-item">
              <div className="variable-header">
                <span className="variable-number">变量 {index + 1}</span>
                <button
                  type="button"
                  className="remove-variable"
                  onClick={() => removeVariable(index)}
                  title="删除变量"
                >
                  <span className="icon-trash">🗑️</span>
                </button>
              </div>
              <div className="variable-fields">
                <div className="input-group">
                  <label>变量Key (用于引用)</label>
                  <input
                    type="text"
                    value={variable.key}
                    onChange={(e) => updateVariable(index, 'key', e.target.value)}
                    placeholder="例如: product_name"
                    maxLength={50}
                    className={variableErrors[index] ? 'input-error' : ''}
                  />
                  {variableErrors[index] && (
                    <span className="error-message">{variableErrors[index]}</span>
                  )}
                </div>
                <div className="input-group">
                  <label>变量值</label>
                  <input
                    type="text"
                    value={variable.value}
                    onChange={(e) => updateVariable(index, 'value', e.target.value)}
                    placeholder="例如: 元气森林"
                    maxLength={100}
                  />
                </div>
              </div>
            </div>
          ))}
          <button
            type="button"
            className="add-variable"
            onClick={addVariable}
          >
            <span className="icon-plus">+</span>
            添加变量
          </button>
        </div>

        {/* 基本信息配置 */}
        <div className="config-section basic-info-section">
          <div className="section-header">
            <h3>
              <span className="section-icon">⚙️</span>
              基本信息
            </h3>
          </div>
           <div className="input-group">
             <label>调研主题 (最多50字符)</label>
             <HighlightInput
               type="input"
               value={theme}
               onChange={setTheme}
               placeholder="请输入调研主题..."
               maxLength={50}
             />
             <CharCount current={theme.length} max={50} />
           </div>
          <div className="input-group">
            <label>系统提示 (最多500字符)</label>
            <HighlightInput
              type="textarea"
              value={systemPrompt}
              onChange={setSystemPrompt}
              placeholder="请输入系统提示，用于给调研员创建角色..."
              maxLength={500}
              rows={4}
            />
            <CharCount current={systemPrompt.length} max={500} />
          </div>
          <div className="input-group">
            <label>背景知识 (最多500字符)</label>
            <HighlightInput
              type="textarea"
              value={backgroundKnowledge}
              onChange={setBackgroundKnowledge}
              placeholder="请输入背景知识，将自动拼接到系统提示后面..."
              maxLength={500}
              rows={4}
            />
            <CharCount current={backgroundKnowledge.length} max={500} />
          </div>
          <div className="input-group">
            <label>选择主持人</label>
            <div className="section-description">
              选择主持人后，其角色信息将自动追加到系统提示中
              </div>
            <select
              value={selectedHostId}
              onChange={(e) => setSelectedHostId(e.target.value)}
              className="host-select"
            >
              <option value="">请选择主持人</option>
              {hosts.map((host) => (
                <option key={host.id} value={host.id}>
                  {host.name}
                </option>
              ))}
            </select>

          </div>
          
          <div className="input-group">
            <label>最大轮数</label>
            <div className="section-description">
              控制每个步骤最多可对话几轮
            </div>
            <input
              type="number"
              value={maxTurns}
              onChange={(e) => setMaxTurns(parseInt(e.target.value) || 5)}
              min="1"
              max="20"
              placeholder="每个步骤最多可对话几轮"
              className="max-turns-input"
            />
          </div>
        </div>


         {/* 开场白和结束语配置 */}
         <div className="welcome-end-wrapper">
           {/* 开场白配置 */}
           <div className="config-section welcome-section">
             <div className="section-header">
               <h3>
                 <span className="section-icon">👋</span>
                 开场白配置
               </h3>
             </div>
             <div className="input-group">
               <label>开场白内容 (最多50字符)</label>
               <HighlightInput
                 type="textarea"
                 value={welcomeMessage}
                 onChange={setWelcomeMessage}
                 placeholder="请输入调研开场白..."
                 maxLength={50}
                 rows={1}
               />
               <CharCount current={welcomeMessage.length} max={50} />
             </div>
           </div>

           {/* 结束语配置 */}
           <div className="config-section end-section">
             <div className="section-header">
               <h3>
                 <span className="section-icon">🏁</span>
                 结束语配置
               </h3>
             </div>
             <div className="input-group">
               <label>结束语内容 (最多50字符)</label>
               <HighlightInput
                 type="textarea"
                 value={endMessage}
                 onChange={setEndMessage}
                 placeholder="请输入调研结束语..."
                 maxLength={50}
                 rows={1}
               />
               <CharCount current={endMessage.length} max={50} />
             </div>
           </div>
         </div>

        {/* 步骤配置 */}
        <div className="config-section steps-section">
          <div className="section-header">
            <h3>
              <span className="section-icon">📋</span>
              调研步骤配置
            </h3>
          </div>
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
                    title="删除步骤"
                  >
                    <span className="icon-trash">🗑️</span>
                  </button>
                )}
              </div>
              <div className="input-group">
                <label>步骤内容 (最多500字符)</label>
                <HighlightInput
                  type="textarea"
                  value={step.content}
                  onChange={(value) => updateStep(step.id, value)}
                  placeholder="请输入调研步骤内容..."
                  maxLength={500}
                  rows={10}
                />
                <CharCount current={step.content.length} max={500} />
              </div>


              {/* 条件跳转配置 */}
              {step.type === 'condition' && (
                <div className="condition-config">
                  <div className="condition-header">
                    <h4>
                      <span className="condition-icon">🔀</span>
                      跳转规则
                    </h4>
                  </div>

                  <div className="jump-rule-display">
                    <div className="rule-line condition-line">
                      <div className="condition-group">
                        <span className="rule-label">
                          <span className="rule-icon">⚡</span>
                          条件
                        </span>
                        <div className="condition-input-wrapper">
                          <HighlightInput
                            type="input"
                            value={step.condition || ''}
                            onChange={(value) => updateStepCondition(step.id, value)}
                            placeholder="输入跳转逻辑，支持 {{变量key}} 格式"
                            className="condition-highlight-input"
                          />
                        </div>
                      </div>
                    </div>

                    <div className="rule-line jump-line">
                      {(() => {
                        // 计算当前步骤的索引，只计算一次
                        const currentStepIndex = steps.findIndex(st => st.id === step.id);
                        // 过滤出当前步骤之后的步骤及其索引信息
                        const nextStepsWithIndex = steps
                          .map((s, idx) => ({ step: s, index: idx }))
                          .filter(({ index }) => index > currentStepIndex);
                        
                        return (
                          <>
                            <div className="jump-group jump-group-true">
                              <span className="rule-label">
                                <span className="rule-icon">✅</span>
                                是，跳转到
                              </span>
                              <select
                                className="step-select"
                                value={step.branches?.[0] || ''}
                                onChange={(e) => {
                                  const newBranches = [...(step.branches || ['', ''])];
                                  newBranches[0] = e.target.value;
                                  updateStepBranches(step.id, newBranches);
                                }}
                              >
                                <option value="">请选择步骤</option>
                                {nextStepsWithIndex.map(({ step: s, index }) => (
                                  <option key={s.id} value={s.id}>
                                    步骤{index + 1}
                                  </option>
                                ))}
                                <option value="END">结束流程</option>
                              </select>
                            </div>

                            <div className="jump-group jump-group-false">
                              <span className="rule-label">
                                <span className="rule-icon">❌</span>
                                否，跳转到
                              </span>
                              <select
                                className="step-select"
                                value={step.branches?.[1] || ''}
                                onChange={(e) => {
                                  const newBranches = [...(step.branches || ['', ''])];
                                  newBranches[1] = e.target.value;
                                  updateStepBranches(step.id, newBranches);
                                }}
                              >
                                <option value="">请选择步骤</option>
                                {nextStepsWithIndex.map(({ step: s, index }) => (
                                  <option key={s.id} value={s.id}>
                                    步骤{index + 1}
                                  </option>
                                ))}
                                <option value="END">结束流程</option>
                              </select>
                            </div>
                          </>
                        );
                      })()}
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
            <span className="icon-plus">+</span>
            添加步骤
          </button>
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
