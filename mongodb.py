# database.py
from pymongo import MongoClient

# 连接到 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["AI"]
# 用户集合
users_collection = db["users"]

def get_user(username):
    """根据用户名查询用户信息"""
    return users_collection.find_one({"username": username})

def add_user(username, hashed_password, email):
    """添加新用户"""
    users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "email": email
    })

def check_user_exists(username):
    """检查用户名是否存在"""
    return users_collection.find_one({"username": username}) is not None

# 其他可能的操作函数，比如更新用户信息、删除用户等
def update_user_email(username, new_email):
    """更新用户的邮箱"""
    users_collection.update_one({"username": username}, {"$set": {"email": new_email}})
