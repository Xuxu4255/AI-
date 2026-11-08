from sqlalchemy import Column, Integer, String, Text, DateTime, DECIMAL, ForeignKey, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    uid = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(String(20), default="user", nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge = relationship("Knowledge", back_populates="creator")
    qa_pairs = relationship("QaPair", back_populates="creator")
    feedbacks = relationship("Feedback", back_populates="user")
    query_logs = relationship("QueryLog", back_populates="user")
    update_logs = relationship("UpdateLog", back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"
    session_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.uid"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)


class Category(Base):
    __tablename__ = "categories"

    cid = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge_list = relationship("Knowledge", back_populates="category")


class Knowledge(Base):
    __tablename__ = "knowledge"

    kid = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.cid"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.uid"), nullable=False)
    keyword = Column(String(255))
    status = Column(String(20), default="draft", nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    category = relationship("Category", back_populates="knowledge_list")
    creator = relationship("User", back_populates="knowledge")
    documents = relationship("Document", back_populates="knowledge")
    qa_pairs = relationship("QaPair", back_populates="knowledge")
    feedbacks = relationship("Feedback", back_populates="knowledge")
    knowledge_tags = relationship("KnowledgeTag", back_populates="knowledge")
    embeddings = relationship("KnowledgeEmbedding", back_populates="knowledge")
    related_current = relationship(
        "RelatedKnowledge",
        foreign_keys="[RelatedKnowledge.knowledge_id]",
        back_populates="knowledge",
    )
    related_target = relationship(
        "RelatedKnowledge",
        foreign_keys="[RelatedKnowledge.related_knowledge_id]",
        back_populates="related_knowledge",
    )
    update_logs = relationship("UpdateLog", back_populates="knowledge")


class Document(Base):
    __tablename__ = "documents"

    did = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.kid"), nullable=False)
    source_type = Column(String(50))
    source_name = Column(String(255))
    source_url = Column(String(500))
    file_name = Column(String(255))
    file_path = Column(String(500))
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge = relationship("Knowledge", back_populates="documents")


class QaPair(Base):
    __tablename__ = "qa_pairs"

    qid = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    knowledge_id = Column(Integer, ForeignKey("knowledge.kid"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.uid"), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)
    status = Column(String(20), default="pending", nullable=False)

    knowledge = relationship("Knowledge", back_populates="qa_pairs")
    creator = relationship("User", back_populates="qa_pairs")
    feedbacks = relationship("Feedback", back_populates="qa_pair")


class Feedback(Base):
    __tablename__ = "feedback"

    fid = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.kid"))
    qa_id = Column(Integer, ForeignKey("qa_pairs.qid"))
    user_id = Column(Integer, ForeignKey("users.uid"), nullable=False)
    feedback_type = Column(String(20), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge = relationship("Knowledge", back_populates="feedbacks")
    qa_pair = relationship("QaPair", back_populates="feedbacks")
    user = relationship("User", back_populates="feedbacks")


class QueryLog(Base):
    __tablename__ = "query_logs"

    lid = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.uid"))
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text)
    model_name = Column(String(100))
    retrieval_count = Column(Integer, default=0, nullable=False)
    feedback_status = Column(String(20), default="unrated", nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    user = relationship("User", back_populates="query_logs")


class SearchContext(Base):
    """记录搜索的用户、问题和来源快照，防止解释时替换他人的来源。"""
    __tablename__ = "search_contexts"
    search_id = Column(String(32), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.uid"), nullable=False)
    query_log_id = Column(Integer, ForeignKey("query_logs.lid"), nullable=False)
    sources_json = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class Tag(Base):
    __tablename__ = "tags"

    tid = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge_tags = relationship("KnowledgeTag", back_populates="tag")


class KnowledgeTag(Base):
    __tablename__ = "knowledge_tags"

    knowledge_id = Column(Integer, ForeignKey("knowledge.kid"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.tid"), primary_key=True)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge = relationship("Knowledge", back_populates="knowledge_tags")
    tag = relationship("Tag", back_populates="knowledge_tags")


class KnowledgeEmbedding(Base):
    __tablename__ = "knowledge_embedding"

    embedding_id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.kid"), nullable=False)
    embedding_model = Column(String(100), nullable=False)
    embedding_text = Column(Text)
    embedding_vector = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge = relationship("Knowledge", back_populates="embeddings")


class RelatedKnowledge(Base):
    __tablename__ = "related_knowledge"

    rid = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.kid"), nullable=False)
    related_knowledge_id = Column(Integer, ForeignKey("knowledge.kid"), nullable=False)
    relevance_score = Column(DECIMAL(5, 4), nullable=False, default=0.0000)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge = relationship(
        "Knowledge",
        foreign_keys=[knowledge_id],
        back_populates="related_current",
    )
    related_knowledge = relationship(
        "Knowledge",
        foreign_keys=[related_knowledge_id],
        back_populates="related_target",
    )


class UpdateLog(Base):
    __tablename__ = "update_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.kid"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.uid"), nullable=False)
    action_type = Column(String(20), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)

    knowledge = relationship("Knowledge", back_populates="update_logs")
    user = relationship("User", back_populates="update_logs")


# 知识星海：新增附属表，不改动原有知识、用户、向量和来源记录。
class PersonalCategory(Base):
    __tablename__ = 'personal_categories'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.uid'), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(7), nullable=False, default='#74DCFF')
    __table_args__ = (UniqueConstraint('user_id', 'name'),)


class PersonalEntry(Base):
    __tablename__ = 'personal_entries'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.uid'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('personal_categories.id'), nullable=False)
    knowledge_id = Column(Integer, ForeignKey('knowledge.kid'), nullable=False, index=True)
    __table_args__ = (UniqueConstraint('user_id', 'knowledge_id'),)


class PlanetSetting(Base):
    __tablename__ = 'planet_settings'
    category_id = Column(Integer, ForeignKey('categories.cid'), primary_key=True)
    visible = Column(Boolean, nullable=False, default=True)
    style = Column(String(20), nullable=False, default='jupiter')
    position = Column(Integer, nullable=False, default=0)


class Appearance(Base):
    __tablename__ = 'user_appearance'
    user_id = Column(Integer, ForeignKey('users.uid'), primary_key=True)
    exposure = Column(Float, nullable=False, default=1.0)
    theme = Column(String(20), nullable=False, default='blue')
    custom_color = Column(String(7), nullable=False, default='#102A48')
    paused = Column(Boolean, nullable=False, default=False)
    reduced_motion = Column(Boolean, nullable=False, default=False)


class Moderation(Base):
    __tablename__ = 'knowledge_moderation'
    knowledge_id = Column(Integer, ForeignKey('knowledge.kid'), primary_key=True)
    hidden = Column(Boolean, nullable=False, default=False)
    reason = Column(String(500), nullable=False, default='')


class PersonalLink(Base):
    __tablename__ = 'personal_links'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.uid'), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey('knowledge.kid'), nullable=False)
    target_id = Column(Integer, ForeignKey('knowledge.kid'), nullable=False)
    relation = Column(String(30), nullable=False, default='相关')
    __table_args__ = (UniqueConstraint('user_id', 'source_id', 'target_id'),)


class KnowledgeChunk(Base):
    __tablename__ = 'knowledge_chunks'
    id = Column(Integer, primary_key=True)
    knowledge_id = Column(Integer, ForeignKey('knowledge.kid'), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    model = Column(String(100), nullable=False)
    position = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    vector = Column(Text, nullable=False)


class SpaceEvent(Base):
    __tablename__ = 'space_events'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.uid'), nullable=False)
    action = Column(String(50), nullable=False)
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)


class AiConversation(Base):
    __tablename__ = 'ai_conversations'
    conversation_id = Column(String(32), primary_key=True)
    search_id = Column(String(32), ForeignKey('search_contexts.search_id'), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('users.uid'), nullable=False, index=True)
    turns = Column(Integer, nullable=False, default=0)
    messages_json = Column(Text, nullable=False, default='[]')


class LibraryShelfAppearance(Base):
    """分类样式；category_id 由 space 区分公共/个人分类，写入时验证归属。"""
    __tablename__ = 'library_shelf_appearance'
    id = Column(Integer, primary_key=True)
    space = Column(String(20), nullable=False)
    category_id = Column(Integer, nullable=False)
    style = Column(String(20), nullable=False, default='glass')
    __table_args__ = (UniqueConstraint('space', 'category_id'),)
