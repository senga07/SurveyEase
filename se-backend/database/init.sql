-- SurveyEase 数据库初始化脚本
-- 创建数据库表结构

-- ============================================
-- 1. 主持人表 (ai_hosts)
-- ============================================
CREATE TABLE IF NOT EXISTS `ai_hosts` (
    `id` VARCHAR(36) NOT NULL COMMENT '主持人ID（UUID）',
    `name` VARCHAR(32) NOT NULL COMMENT '主持人名称',
    `role` TEXT NOT NULL COMMENT '主持人角色描述（包含角色、职责、提问技巧等）',
    `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除：1 已删除，0 正常',
    `create_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='主持人表';

-- ============================================
-- 2. 调研模板表 (ai_survey_templates)
-- ============================================
CREATE TABLE IF NOT EXISTS `ai_survey_templates` (
    `id` VARCHAR(255) NOT NULL COMMENT '调研模板ID',
    `theme` VARCHAR(500) NOT NULL COMMENT '调研主题',
    `system_prompt` TEXT NULL COMMENT '系统提示词',
    `background_knowledge` TEXT NULL COMMENT '背景知识',
    `max_turns` INT NULL DEFAULT 5 COMMENT '最大对话轮次',
    `welcome_message` TEXT NULL COMMENT '欢迎消息',
    `end_message` TEXT NULL COMMENT '结束消息',
    `host_id` VARCHAR(36) NOT NULL COMMENT '关联的主持人ID',
    `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除：1 已删除，0 正常',
    `create_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='调研模板表';

-- ============================================
-- 3. 调研模板步骤表 (ai_survey_template_steps)
-- ============================================
CREATE TABLE IF NOT EXISTS `ai_survey_template_steps` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '步骤记录ID',
    `template_id` VARCHAR(255) NOT NULL COMMENT '关联的调研模板ID',
    `step_id` INT NOT NULL COMMENT '步骤ID（模板内的步骤编号）',
    `content` TEXT NOT NULL COMMENT '步骤内容（包含目标、示例、必须信息清单等）',
    `type` VARCHAR(20) NOT NULL DEFAULT 'linear' COMMENT '步骤类型：linear（线性）或condition（条件分支）',
    `condition_text` TEXT NULL COMMENT '条件文本（当type为condition时使用，用于判断分支）',
    `branches` JSON NULL COMMENT '分支列表（JSON数组，存储下一步步骤ID或"END"）',
    `step_order` INT NOT NULL COMMENT '步骤顺序（用于排序）',
    `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除：1 已删除，0 正常',
    `create_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_template_step` (`template_id`, `step_id`) COMMENT '模板步骤唯一约束',
    INDEX `idx_template_id` (`template_id`) COMMENT '模板ID索引',
    INDEX `idx_step_order` (`template_id`, `step_order`) COMMENT '步骤顺序索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='调研模板步骤表';

-- ============================================
-- 4. 调研模板变量表 (ai_survey_template_variables)
-- ============================================
CREATE TABLE IF NOT EXISTS `ai_survey_template_variables` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '变量记录ID',
    `template_id` VARCHAR(255) NOT NULL COMMENT '关联的调研模板ID',
    `variable_key` VARCHAR(100) NOT NULL COMMENT '变量键名（如product_name、category等）',
    `variable_value` VARCHAR(500) NOT NULL COMMENT '变量值（如"三得利乌龙茶"、"无糖茶"等）',
    `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除：1 已删除，0 正常',
    `create_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_template_variable` (`template_id`, `variable_key`) COMMENT '模板变量唯一约束',
    INDEX `idx_template_id` (`template_id`) COMMENT '模板ID索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='调研模板变量表';

-- ============================================
-- 5. 会话记录表 (ai_conversations)
-- ============================================
CREATE TABLE IF NOT EXISTS `ai_conversations` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '会话记录ID',
    `conversation_id` VARCHAR(255) NOT NULL COMMENT '会话ID',
    `template_id` VARCHAR(255) NOT NULL COMMENT '关联的调研模板ID',
    `timestamp` VARCHAR(14) NOT NULL COMMENT '时间戳（yyyymmddHHmmss格式）',
    `message_count` INT NULL DEFAULT 0 COMMENT '消息总数',
    `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除：1 已删除，0 正常',
    `create_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_conversation_id` (`conversation_id`) COMMENT '会话ID唯一',
    INDEX `idx_conversation_id` (`conversation_id`) COMMENT '会话ID索引',
    INDEX `idx_create_datetime` (`create_datetime`) COMMENT '创建时间索引',
    INDEX `idx_template_id` (`template_id`) COMMENT '模板ID索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话记录表';

-- ============================================
-- 6. 聊天消息表 (ai_chat_messages)
-- ============================================
CREATE TABLE IF NOT EXISTS `ai_chat_messages` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '消息记录ID',
    `conversation_id` VARCHAR(255) NOT NULL COMMENT '关联的会话ID',
    `message_type` VARCHAR(50) NOT NULL COMMENT '消息类型：HumanMessage, AIMessage, SystemMessage',
    `content` TEXT NOT NULL COMMENT '消息内容',
    `message_order` INT NOT NULL COMMENT '消息顺序（在会话中的顺序）',
    `additional_kwargs` JSON NULL COMMENT '额外参数（JSON格式）',
    `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除：1 已删除，0 正常',
    `create_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    INDEX `idx_conversation_id` (`conversation_id`) COMMENT '会话ID索引',
    INDEX `idx_create_datetime` (`create_datetime`) COMMENT '创建时间索引',
    INDEX `idx_message_order` (`conversation_id`, `message_order`) COMMENT '消息顺序索引（用于排序）',
    INDEX `idx_message_type` (`message_type`) COMMENT '消息类型索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';

-- ============================================
-- 脚本执行完成
-- ============================================

