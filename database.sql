drop database if exists Db_km;
create database Db_km;#建库

Use Db_km;
#用户名
create table users (
    Uid int primary key auto_increment,
    Username varchar(50) not null unique,
    password_hash varchar(255) not null,
    email varchar(100) not null unique,
    role enum('admin', 'user') not null default 'user',
    created_at timestamp not null default current_timestamp  #创建的时间戳
);

#知识的关联
create table categories (
    Cid int primary key auto_increment,#主键，知识的编号
    name varchar(100) not null unique,
    description text,#知识相关的标签
    created_at timestamp not null default current_timestamp#建立的时间戳
);

#知识
create table knowledge (
    Kid int primary key auto_increment, #主键，知识的编号
    title varchar(255) not null,		#知识的标题
    content text not null,				#知识正文内容，不能为空
    summary text,						#知识的摘要
    category_id int not null,			#知识所属分类编号，外键关联 categories 表
    created_by int not null,			#创建该知识的用户编号，外键关联 users 表
    keyword varchar(255),				#关键词，用于检索和匹配知识
    status enum('draft', 'published', 'deleted') not null default 'draft',	-- 状态：草稿/已发布/已删除
    created_at timestamp not null default current_timestamp,-- 创建时间，默认当前时间
    updated_at timestamp not null default current_timestamp on update current_timestamp, -- 更新时间
    constraint fk_knowledge_category foreign key (category_id) references categories(Cid),-- 关联categories表
    constraint fk_knowledge_user foreign key (created_by) references users(Uid)  -- 关联用户表
);

create table documents (
    Did int primary key auto_increment, -- 文档编号，主键，自动增长
    knowledge_id int not null, -- 关联的知识编号
    source_type varchar(50), -- 文档来源类型，如 book / article / online / file
    source_name varchar(255), -- 来源名称
    source_url varchar(500), -- 来源链接
    file_name varchar(255), -- 文件名
    file_path varchar(500), -- 文件路径
    created_at timestamp not null default current_timestamp, -- 创建时间
    constraint fk_documents_knowledge foreign key (knowledge_id) references knowledge(Kid) -- 外键，关联 knowledge
);

create table qa_pairs (
    Qid int primary key auto_increment, -- 问答编号，主键，自动增长
    question_text text not null, -- 标准问题内容
    answer_text text not null, -- 标准答案内容
    knowledge_id int not null, -- 关联知识编号
    created_by int not null, -- 创建该问答对的用户编号
    created_at timestamp not null default current_timestamp, -- 创建时间
    status enum('pending', 'approved', 'rejected') not null default 'pending', -- 审核状态
    constraint fk_qa_knowledge foreign key (knowledge_id) references knowledge(Kid), -- 关联 knowledge
    constraint fk_qa_user foreign key (created_by) references users(Uid) -- 关联 users
);
create table feedback (
    Fid int primary key auto_increment, -- 反馈编号，主键，自动增长
    knowledge_id int, -- 关联知识编号，可为空
    qa_id int, -- 关联问答编号，可为空
    user_id int not null, -- 提交反馈的用户编号
    feedback_type enum('like', 'dislike', 'error', 'suggestion') not null, -- 反馈类型
    content text, -- 反馈内容
    created_at timestamp not null default current_timestamp, -- 创建时间
    constraint fk_feedback_knowledge foreign key (knowledge_id) references knowledge(Kid), -- 关联 knowledge
    constraint fk_feedback_qa foreign key (qa_id) references qa_pairs(Qid), -- 关联 qa_pairs
    constraint fk_feedback_user foreign key (user_id) references users(Uid) -- 关联 users
);

create table query_logs (
    Lid int primary key auto_increment, -- 查询日志编号，主键，自动增长
    user_id int, -- 提问用户编号，可为空
    question_text text not null, -- 用户实际提问内容
    answer_text text, -- AI 返回内容
    model_name varchar(100), -- 使用的模型名称
    retrieval_count int not null default 0, -- 检索命中的知识条数
    feedback_status enum('unrated', 'liked', 'disliked') not null default 'unrated', -- 用户对回答的评价
    created_at timestamp not null default current_timestamp, -- 创建时间
    constraint fk_query_user foreign key (user_id) references users(Uid) -- 关联 users
);

create table tags (
    Tid int primary key auto_increment, -- 标签编号，主键，自动增长
    name varchar(100) not null unique, -- 标签名称，唯一
    description text, -- 标签说明
    created_at timestamp not null default current_timestamp -- 创建时间
);

create table knowledge_tags (
    knowledge_id int not null, -- 知识编号
    tag_id int not null, -- 标签编号
    created_at timestamp not null default current_timestamp, -- 创建时间
    primary key (knowledge_id, tag_id), -- 组合主键
    constraint fk_knowledge_tags_knowledge foreign key (knowledge_id) references knowledge(Kid), -- 关联 knowledge
    constraint fk_knowledge_tags_tag foreign key (tag_id) references tags(Tid) -- 关联 tags
);

create table knowledge_embedding (
    embedding_id int primary key auto_increment, -- 向量编号，主键，自动增长
    knowledge_id int not null, -- 对应知识编号
    embedding_model varchar(100) not null, -- 使用的 embedding 模型
    embedding_text text, -- 原始文本内容
    embedding_vector text, -- 向量数据，适用于 MySQL 轻量实现
    created_at timestamp not null default current_timestamp, -- 创建时间
    constraint fk_embedding_knowledge foreign key (knowledge_id) references knowledge(Kid) -- 关联 knowledge
);

create table related_knowledge (
    Rid int primary key auto_increment, -- 关联编号，主键，自动增长
    knowledge_id int not null, -- 当前知识编号
    related_knowledge_id int not null, -- 相关知识编号
    relevance_score decimal(5,4) not null default 0.0000, -- 相关度分数
    created_at timestamp not null default current_timestamp, -- 创建时间
    constraint fk_related_current foreign key (knowledge_id) references knowledge(Kid), -- 关联当前知识
    constraint fk_related_target foreign key (related_knowledge_id) references knowledge(Kid) -- 关联目标知识
);

create table update_logs (
    log_id int primary key auto_increment, -- 更新日志编号，主键，自动增长
    knowledge_id int not null, -- 关联知识编号
    user_id int not null, -- 操作用户编号
    action_type enum('create', 'update', 'delete', 'publish', 'revert') not null, -- 操作类型
    old_value text, -- 修改前内容
    new_value text, -- 修改后内容
    created_at timestamp not null default current_timestamp, -- 创建时间
    constraint fk_update_knowledge foreign key (knowledge_id) references knowledge(Kid), -- 关联 knowledge
    constraint fk_update_user foreign key (user_id) references users(Uid) -- 关联 users
);