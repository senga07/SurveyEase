import React, { useState, useEffect } from 'react';
import './HostConfig.css';
import { Host } from '../types';
import { ApiService } from '../services/api';

interface HostConfigProps {
  onBack?: () => void;
}

const HostConfig: React.FC<HostConfigProps> = ({ onBack }) => {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingHost, setEditingHost] = useState<Host | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', role: '' });

  useEffect(() => {
    loadHosts();
  }, []);

  const loadHosts = async () => {
    try {
      const hostsList = await ApiService.getHosts();
      setHosts(hostsList);
    } catch (error) {
      console.error('加载主持人列表失败:', error);
    }
  };

  const handleAdd = () => {
    setEditingHost(null);
    setFormData({ name: '', role: '' });
    setShowForm(true);
  };

  const handleEdit = (host: Host) => {
    setEditingHost(host);
    setFormData({ name: host.name, role: host.role });
    setShowForm(true);
  };

  const handleDelete = async (hostId: string) => {
    if (window.confirm('确定要删除这个主持人配置吗？')) {
      try {
        const success = await ApiService.deleteHostById(hostId);
        if (success) {
          await loadHosts();
          alert('主持人配置删除成功！');
        } else {
          alert('删除失败，请重试');
        }
      } catch (error) {
        console.error('删除主持人配置失败:', error);
        alert('删除失败，请重试');
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.role.trim()) {
      alert('请填写完整信息');
      return;
    }

    setIsLoading(true);
    try {
      const hostData: Host = {
        id: editingHost?.id || '',
        name: formData.name.trim(),
        role: formData.role.trim()
      };

      let success = false;
      if (editingHost) {
        success = await ApiService.updateHostById(editingHost.id, hostData);
      } else {
        success = await ApiService.createHost(hostData);
      }

      if (success) {
        await loadHosts();
        setShowForm(false);
        setEditingHost(null);
        setFormData({ name: '', role: '' });
        alert(editingHost ? '主持人配置更新成功！' : '主持人配置创建成功！');
      } else {
        alert('保存失败，请重试');
      }
    } catch (error) {
      console.error('保存主持人配置失败:', error);
      alert('保存失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingHost(null);
    setFormData({ name: '', role: '' });
  };

  return (
    <div className="host-config">
      <div className="config-header">
        <h2>主持人配置管理</h2>
        <p>管理调研主持人的角色配置</p>
      </div>

      {!showForm ? (
        <div className="host-list">
          <div className="list-header">
            <h3>主持人列表</h3>
            <button className="add-button" onClick={handleAdd}>
              + 添加主持人
            </button>
          </div>

          {hosts.length === 0 ? (
            <div className="empty-state">
              <p>暂无主持人配置</p>
            </div>
          ) : (
            <div className="host-grid">
              {hosts.map((host) => (
                <div key={host.id} className="host-card">
                  <div className="host-info">
                    <h4>{host.name}</h4>
                    <p className="host-role">{host.role}</p>
                  </div>
                  <div className="host-actions">
                    <button
                      className="edit-button"
                      onClick={() => handleEdit(host)}
                    >
                      编辑
                    </button>
                    <button
                      className="delete-button"
                      onClick={() => handleDelete(host.id)}
                    >
                      删除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="host-form">
          <div className="form-header">
            <h3>{editingHost ? '编辑主持人' : '添加主持人'}</h3>
            <button className="back-button" onClick={handleCancel}>
              返回列表
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="name">主持人名称 *</label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="请输入主持人名称"
                maxLength={50}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="role">主持人角色 *</label>
              <textarea
                id="role"
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                placeholder="请输入主持人角色描述，这将作为系统提示的一部分"
                rows={10}
                maxLength={500}
                required
              />
              <div className="char-count">
                {formData.role.length}/500
              </div>
            </div>

            <div className="form-actions">
              <button
                type="button"
                className="cancel-button"
                onClick={handleCancel}
                disabled={isLoading}
              >
                取消
              </button>
              <button
                type="submit"
                className="save-button"
                disabled={isLoading}
              >
                {isLoading ? '保存中...' : (editingHost ? '更新' : '创建')}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="config-actions">
        {onBack && (
          <button className="back-button" onClick={onBack}>
            返回首页
          </button>
        )}
      </div>
    </div>
  );
};

export default HostConfig;
