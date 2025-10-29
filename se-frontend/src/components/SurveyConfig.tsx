import React, { useState, useEffect, useRef } from 'react';
import './SurveyConfig.css';
import { SurveyStep, SurveyTemplate, SurveyVariable } from '../types';
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
  const [maxTurns, setMaxTurns] = useState(5);
  const [welcomeMessage, setWelcomeMessage] = useState('');
  const [steps, setSteps] = useState<SurveyStep[]>([
    { id: '1', content: '' }
  ]);
  const [endMessage, setEndMessage] = useState('');
  const [variables, setVariables] = useState<SurveyVariable[]>([]);
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
        setVariables([]);
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
        setVariables(template.variables || []);
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

  const addVariable = () => {
    const newVariable: SurveyVariable = {
      key: '',
      value: ''
    };
    setVariables([...variables, newVariable]);
  };

  const removeVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
  };

  const updateVariable = (index: number, field: keyof SurveyVariable, value: string) => {
    const updatedVariables = [...variables];
    updatedVariables[index] = { ...updatedVariables[index], [field]: value };
    setVariables(updatedVariables);
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
        end_message: endMessage,
        variables: variables
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

      {/* 变量配置 */}
        <div className="config-section variables-section">
          <h3>变量配置</h3>
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
                >
                  删除
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
                  />
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
            + 添加变量
          </button>
        </div>


      <div className="config-content">
        {/* 基本信息配置 */}
        <div className="config-section basic-info-section">
          <h3>基本信息</h3>
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
              rows={10}
            />
            <CharCount current={systemPrompt.length} max={500} />
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
              className="max-turns-input"
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

        {/* 步骤配置 */}
        <div className="config-section steps-section">
          <h3>调研步骤配置</h3>
          {steps.map((step, index) => (
            <div key={step.id} className="step-item">
              <div className="step-header">
                <span className="step-number">步骤 {index + 1}</span>
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
