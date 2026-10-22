drop database if exists Db_km;
create database Db_km;#建库


#用户名
create table users (
    Uid int primary key not null,
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
    constraint fk_knowledge_user foreign key (created_by) references users(id)  -- 关联用户表
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
    question_text text not null, -- 用户提问内容
    answer_text text not null, -- 对应回答内容
    knowledge_id int not null, -- 关联知识编号
    created_by int not null, -- 创建该问答对的用户编号
    created_at timestamp not null default current_timestamp, -- 创建时间
    status enum('pending', 'approved', 'rejected') not null default 'pending', -- 审核状态
    constraint fk_qa_knowledge foreign key (knowledge_id) references knowledge(Kid), -- 外键，关联 knowledge
    constraint fk_qa_user foreign key (created_by) references users(Uid) -- 外键，关联 users
);










