"""生成独立 Docker 配置，并用 mysqldump 只读导出现有数据库。已有文件不覆盖。"""
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import set_key
from sqlalchemy import text
from app import config
from app.database import engine


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    model = ROOT / '.models' / 'bge-small-zh-v1.5'
    for name in ('model.safetensors', 'MODEL_INFO.json', 'config.json', 'tokenizer.json'):
        if not (model / name).is_file():
            raise RuntimeError('缺少本地模型文件：' + name)

    env_path = ROOT / '.env.docker'
    if not env_path.exists():
        values = {
            'MYSQL_DATABASE': config.MYSQL_DATABASE,
            'MYSQL_USER': 'library',
            'MYSQL_PASSWORD': secrets.token_hex(24),
            'MYSQL_ROOT_PASSWORD': secrets.token_hex(24),
            'APP_PORT': '8080',
            'DEEPSEEK_API_KEY': config.DEEPSEEK_API_KEY,
            'DEEPSEEK_BASE_URL': config.DEEPSEEK_BASE_URL,
            'DEEPSEEK_MODEL': config.DEEPSEEK_MODEL,
            'AI_TIMEOUT': str(config.AI_TIMEOUT),
            'SEMANTIC_MIN_SCORE': str(config.SEMANTIC_MIN_SCORE),
        }
        env_path.touch(mode=0o600)
        for key, value in values.items():
            set_key(str(env_path), key, value)
        print('已生成 .env.docker：新数据库使用独立密码，DeepSeek 配置已复制。')
    else:
        print('保留已有 .env.docker。')

    folder = ROOT / 'data' / 'docker-init'
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = folder / '10-existing.sql'
    if snapshot.exists():
        print('保留已有数据库迁移快照：data/docker-init/10-existing.sql')
        return

    dump_tool = shutil.which('mysqldump')
    if not dump_tool and os.name == 'nt':
        candidate = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'MySQL/MySQL Server 8.0/bin/mysqldump.exe'
        if candidate.is_file():
            dump_tool = str(candidate)
    if not dump_tool:
        raise RuntimeError('请安装 MySQL 客户端，并让 mysqldump 命令可用。')

    with engine.connect() as connection:
        count = connection.execute(text('SELECT COUNT(*) FROM knowledge')).scalar_one()

    command = [dump_tool, '--host=' + config.MYSQL_HOST, '--port=' + str(config.MYSQL_PORT),
               '--user=' + config.MYSQL_USER, '--single-transaction', '--skip-lock-tables',
               '--no-tablespaces', '--set-gtid-purged=OFF', '--column-statistics=0',
               '--hex-blob', '--default-character-set=utf8mb4', config.MYSQL_DATABASE]
    child_env = dict(os.environ, MYSQL_PWD=config.MYSQL_PASSWORD)
    temporary = folder / '10-existing.sql.partial'
    with temporary.open('wb') as output:
        subprocess.run(command, env=child_env, stdout=output, check=True)
    temporary.replace(snapshot)
    print('已导出数据库，知识条目：' + str(count))
    print('原数据库未修改；快照只在新的 MySQL 数据卷首次初始化时导入。')


if __name__ == '__main__':
    main()
