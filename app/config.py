# 配置统一从 .env 读取，代码里不再写死密码 / 密钥
import os
from pathlib import Path

from dotenv import load_dotenv

# .env 在项目根目录（app/ 的上一层），用绝对路径，避免从别的目录启动时读不到
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# 数据库连接配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")      # 主机
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))      # 端口
MYSQL_USER = os.getenv("MYSQL_USER", "root")           # 用户
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")       # 密码
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "Db_km")  # 数据库名

# “描述 MySQL 数据库位置和连接方式的字符串
DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
    f"{MYSQL_DATABASE}?charset=utf8mb4"
)

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "30"))

# 应用基础配置
APP_TITLE = "知识库管理系统"
APP_VERSION = "1.0.0"
