# 数据库连接配置
MYSQL_HOST = "localhost" #主机
MYSQL_PORT = 3306   #端口
MYSQL_USER = "root"   #用户
MYSQL_PASSWORD = "123456"#密码
MYSQL_DATABASE = "Db_km" #数据库名

#“描述 MySQL 数据库位置和连接方式的字符串
DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
    f"{MYSQL_DATABASE}?charset=utf8mb4"
)#它是在把“数据库配置”拼接成一个完整的数据库连接字符串。

# 应用基础配置
APP_TITLE = "知识库管理系统"
APP_VERSION = "1.0.0"
