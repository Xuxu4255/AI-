"""启动容器网站，仅信任回环地址和 Docker 网关转发的代理头。"""
import os
import socket
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def trusted_proxies():
    configured = os.getenv('FORWARDED_ALLOW_IPS')
    if configured:
        return configured
    hosts = {'127.0.0.1', '::1'}
    # 从路由表读取网关，避免 Docker 重建网络后网段改变导致 HTTPS 登录失败。
    for line in Path('/proc/net/route').read_text().splitlines()[1:]:
        fields = line.split()
        if fields[1] == '00000000' and int(fields[3], 16) & 2:
            hosts.add(socket.inet_ntoa(bytes.fromhex(fields[2])[::-1]))
    return ','.join(sorted(hosts))


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000,
                proxy_headers=True, forwarded_allow_ips=trusted_proxies())
