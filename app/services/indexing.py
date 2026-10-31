"""知识转向量的统一文本格式；搜索时也用它检查索引是否过期。"""
def build_embedding_text(knowledge):
    # 资料性质说明和来源链接用于展示，不参与概念语义编码。
    body = knowledge.content.split('\n\n资料性质：', 1)[0]
    return knowledge.title.strip() + '\n' + body.strip()


def refresh_index(db, knowledge):
    """发布或修改已发布正文后同步更新单条索引。主知识保存已独立提交。"""
    import json
    from app.models import KnowledgeEmbedding
    from app.services.embedding import get_local_embeddings
    from sqlalchemy.exc import SQLAlchemyError
    try:
        text = build_embedding_text(knowledge)
        result = get_local_embeddings([text], 'document')
        old = db.query(KnowledgeEmbedding).filter(KnowledgeEmbedding.knowledge_id == knowledge.kid,
            KnowledgeEmbedding.embedding_model == result['model']).order_by(KnowledgeEmbedding.embedding_id.desc()).first()
        if old is None or old.embedding_text != text:
            db.add(KnowledgeEmbedding(knowledge_id=knowledge.kid, embedding_model=result['model'],
                embedding_text=text,embedding_vector=json.dumps(result['vectors'][0],allow_nan=False)))
            db.commit()
        return 'ready'
    except (OSError, ValueError, SQLAlchemyError):
        db.rollback()
        return 'pending'
