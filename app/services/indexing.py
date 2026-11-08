"""知识转向量的统一文本格式；搜索时也用它检查索引是否过期。"""
def build_embedding_text(knowledge):
    # 资料性质说明和来源链接用于展示，不参与概念语义编码。
    body = knowledge.content.split('\n\n资料性质：', 1)[0]
    return knowledge.title.strip() + '\n' + body.strip()


def refresh_index(db, knowledge):
    """发布或修改已发布正文后同步更新单条索引。主知识保存已独立提交。"""
    import json
    import hashlib
    from app.models import KnowledgeEmbedding, KnowledgeChunk
    from app.services.embedding import get_local_embeddings
    from sqlalchemy.exc import SQLAlchemyError
    try:
        text = build_embedding_text(knowledge)
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        # 220 字片段及 40 字重叠，按知识聚合；不截掉长文章尾部。
        body = knowledge.content.split('\n\n资料性质：', 1)[0].strip()
        pieces = [knowledge.title[:100] + '\n' + body[i:i+220] for i in range(0, max(1, len(body)), 180)]
        vectors = []
        for offset in range(0, len(pieces), 8):
            batch = get_local_embeddings(pieces[offset:offset+8], 'document')
            vectors.extend(batch['vectors'])
        result = batch
        db.query(KnowledgeChunk).filter_by(knowledge_id=knowledge.kid).delete()
        for position, (piece, vector) in enumerate(zip(pieces, vectors)):
            db.add(KnowledgeChunk(knowledge_id=knowledge.kid, content_hash=digest,
                model=result['model'], position=position, text=piece, vector=json.dumps(vector, allow_nan=False)))
        old = db.query(KnowledgeEmbedding).filter(KnowledgeEmbedding.knowledge_id == knowledge.kid,
            KnowledgeEmbedding.embedding_model == result['model']).order_by(KnowledgeEmbedding.embedding_id.desc()).first()
        if len(pieces) == 1 and (old is None or old.embedding_text != text):
            db.add(KnowledgeEmbedding(knowledge_id=knowledge.kid, embedding_model=result['model'],
                embedding_text=text,embedding_vector=json.dumps(vectors[0],allow_nan=False)))
        db.commit()
        return 'ready'
    except (OSError, ValueError, SQLAlchemyError):
        db.rollback()
        return 'pending'
