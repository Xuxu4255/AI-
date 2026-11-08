"""独立测试本地 BGE-small，不修改当前 Python 3.8 后端。
首次运行传 --download 从官方 Hugging Face 下载；以后直接离线运行。
"""
import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = 'BAAI/bge-small-zh-v1.5'
MODEL_DIR = ROOT / '.models' / 'bge-small-zh-v1.5'
QUERY_INSTRUCTION = '为这个句子生成表示以用于检索相关文章：'


def download_model():
    from huggingface_hub import HfApi, snapshot_download
    revision = HfApi().model_info(MODEL_ID).sha
    snapshot_download(
        MODEL_ID, revision=revision, local_dir=str(MODEL_DIR),
        allow_patterns=['config.json', 'model.safetensors', 'tokenizer.json',
                        'tokenizer_config.json', 'special_tokens_map.json', 'vocab.txt', 'README.md'],
        max_workers=3,
    )
    if not (MODEL_DIR / 'model.safetensors').is_file():
        raise RuntimeError('没有下载到 safetensors 权重，请检查官方模型文件。')
    (MODEL_DIR / 'MODEL_INFO.json').write_text(json.dumps({'model':MODEL_ID,'revision':revision,'pooling':'CLS','normalize':True},indent=2),encoding='utf-8')
    print('Model saved:',MODEL_DIR,flush=True)


class LocalEmbedder:
    def __init__(self):
        import torch
        from transformers import AutoTokenizer, AutoModel
        self.torch = torch
        torch.set_num_threads(min(4,os.cpu_count() or 1))
        self.tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR),local_files_only=True)
        self.model = AutoModel.from_pretrained(str(MODEL_DIR),local_files_only=True,use_safetensors=True)
        self.model.eval()  # 先使用 CPU 做可复现的小规模实验。

    def encode(self,texts,query=False):
        if not texts or any(not isinstance(t,str) or not t.strip() for t in texts):
            raise ValueError('texts 必须是非空文本列表')
        if query:
            texts=[QUERY_INSTRUCTION+t for t in texts]
        tokens=self.tokenizer(texts,padding=True,truncation=True,max_length=512,return_tensors='pt')
        with self.torch.inference_mode():
            vectors=self.model(**tokens).last_hidden_state[:,0]
            vectors=self.torch.nn.functional.normalize(vectors,p=2,dim=1)
        return vectors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true')
    args=parser.parse_args()
    if args.download:
        download_model()
    start=time.perf_counter()
    embedder=LocalEmbedder()
    passages=['栈在同一端插入和删除元素，最后放入的元素最先被取出。',
              '队列在队尾插入、队首删除，先进入的元素先离开。',
              '二叉树每个节点最多有两个子节点，可以进行前序、中序和后序遍历。']
    question='最后放进去的东西为什么最先出来？'
    docs=embedder.encode(passages)
    query=embedder.encode([question],query=True)
    scores=(query @ docs.T)[0]
    order=scores.argsort(descending=True).tolist()
    assert docs.shape[1]==512,docs.shape
    assert order[0]==0, '示例问题没有把栈排在第一，需要检查编码和模型。'
    result={'model':MODEL_ID,'device':'cpu','dimension':docs.shape[1],
            'question':question,'ranking':[{'text':passages[i],'score':round(float(scores[i]),6)} for i in order],
            'load_and_infer_seconds':round(time.perf_counter()-start,3)}
    report_dir=ROOT/'data'/'reports'
    report_dir.mkdir(parents=True,exist_ok=True)
    (report_dir/'local-embedding-smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2),flush=True)
    print('PASS: local inference and semantic ranking; no API Key required.',flush=True)


if __name__=='__main__':main()
