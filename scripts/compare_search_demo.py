import json
import argparse
import getpass
import httpx
questions=['最后放进去的东西为什么最先出来','排队时先来先服务是什么结构','二分查找为什么要求有序','树怎么一层一层访问节点','今天天气怎么样']
parser=argparse.ArgumentParser();parser.add_argument('--username',default='admin');args=parser.parse_args()
password=getpass.getpass('Account password: ')
rows=[]
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30,trust_env=False) as c:
    c.post('/login',json={'username':args.username,'password':password}).raise_for_status()
    try:
        for q in questions:
            old=c.get('/search/knowledge',params={'keyword':q,'status':'published'});old.raise_for_status()
            new=c.post('/ai/search',json={'question':q});new.raise_for_status()
            rows.append({'question':q,'keyword_count':old.json()['count'],'semantic_titles':[s['title'] for s in new.json()['sources']]})
    finally:c.post('/logout')
print(json.dumps(rows,ensure_ascii=True,indent=2))
