import json
import argparse
import getpass
import httpx
from pathlib import Path
cases=[('最后放进去的东西为什么最先出来','栈'),('排队时先来先服务是什么结构','队列'),('二分查找为什么要求有序','二分查找'),('树怎么一层一层访问节点','层序'),('快速排序为什么会退化','快速排序'),('排序后同样的键保持原先顺序叫什么','稳定性'),('链表插入操作一定是常数时间吗','单链表插入'),('算法的辅助内存随规模怎么增长','空间复杂度')]
negatives=['今天天气怎么样','晚饭吃什么','推荐一部电影','股票明天会涨吗','北京到上海的机票多少钱','给我推荐一款手机']
parser=argparse.ArgumentParser();parser.add_argument('--username',default='admin');args=parser.parse_args()
password=getpass.getpass('Local account password: ')
reports=[]
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=40,trust_env=False) as c:
    c.post('/login',json={'username':args.username,'password':password}).raise_for_status()
    try:
        for question,expected in cases:
            r=c.post('/ai/search',json={'question':question});r.raise_for_status();data=r.json()
            titles=[s['title'] for s in data['sources']]
            reports.append({'question':question,'expected_keyword':expected,'titles':titles,'hit_at_3':any(expected in t for t in titles)})
        missing_key=c.post('/ai/explain',json={'question':cases[-1][0],'knowledge_ids':[s['knowledge_id'] for s in data['sources']],'search_id':data['search_id']})
        assert missing_key.status_code==503,missing_key.text
        assert 'API Key' in missing_key.json()['detail']
        for question in negatives:
            r=c.post('/ai/search',json={'question':question});r.raise_for_status()
            reports.append({'question':question,'expected_empty':True,'titles':[s['title'] for s in r.json()['sources']],'correct_rejection':not r.json()['sources']})
        info=c.get('/ai/status');info.raise_for_status()
        print('Service status:',info.json())
    finally:c.post('/logout')
Path('tests/live-search-evaluation.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
print('Positive hit@3:',sum(r.get('hit_at_3',False) for r in reports),'/',len(cases))
print('Unrelated rejected:',sum(r.get('correct_rejection',False) for r in reports),'/',len(negatives))
print('Missing DeepSeek Key: HTTP 503 verified')
