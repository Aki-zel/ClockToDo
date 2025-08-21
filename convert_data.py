import json
from datetime import datetime

# 读取现有数据
with open('todo.json', 'r', encoding='utf-8') as f:
    old_data = json.load(f)

# 创建新的数据结构
new_data = {
    "tasks": [],
    "daily_records": {}
}

# 转换任务列表
for task in old_data:
    new_data["tasks"].append({"name": task["name"]})
    
    # 转换记录
    for record in task.get("records", []):
        try:
            # 获取日期
            start_time = datetime.fromisoformat(record["start"])
            date = start_time.strftime("%Y-%m-%d")
            
            # 创建日期记录
            if date not in new_data["daily_records"]:
                new_data["daily_records"][date] = []
            
            # 添加记录
            new_data["daily_records"][date].append({
                "task": task["name"],
                "start": start_time.strftime("%H:%M:%S"),
                "end": datetime.fromisoformat(record["end"]).strftime("%H:%M:%S"),
                "duration": record["duration"]
            })
        except (ValueError, TypeError) as e:
            print(f"跳过无效记录: {e}")

# 对日期进行排序（倒序）
new_data["daily_records"] = dict(sorted(new_data["daily_records"].items(), reverse=True))

# 保存新数据
with open('todo.json', 'w', encoding='utf-8') as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print("数据转换完成！")
