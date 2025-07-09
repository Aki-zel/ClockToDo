import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

# 统计周期常量
PERIODS = [
    ('今日', 'day'),
    ('本周', 'week'),
    ('本月', 'month'),
    ('本年', 'year')
]

def show_stats(tasks, period='今日'):
    period_map = dict(PERIODS)
    period_type = period_map.get(period, 'day')
    now = datetime.now()
    labels = []
    values = []
    for task in tasks:
        total = 0
        for rec in task.get('records', []):
            try:
                start = datetime.fromisoformat(str(rec['start']))
                duration = int(float(rec['duration']))
            except Exception:
                continue
            if period_type == 'day':
                if start.date() == now.date():
                    total += duration
            elif period_type == 'week':
                if start.isocalendar()[1] == now.isocalendar()[1] and start.isocalendar()[0] == now.isocalendar()[0]:
                    total += duration
            elif period_type == 'month':
                if start.month == now.month and start.year == now.year:
                    total += duration
            elif period_type == 'year':
                if start.year == now.year:
                    total += duration
        labels.append(task['name'])
        values.append(round(total/3600, 4))
    if all(v == 0 for v in values):
        messagebox.showinfo('统计', '该周期暂无计时记录')
        return
    try:
        plt.figure(figsize=(7,7))
        patches, texts, autotexts = plt.pie(values, labels=labels, autopct=lambda pct: f'{pct:.1f}%\n({pct*sum(values)/100:.4f}小时)', startangle=90, textprops={'fontsize': 14})
        plt.title(f'{period}各任务累计专注时间（小时）', fontsize=16)
        plt.tight_layout()
        plt.show()
    except Exception as e:
        plt.close()
        messagebox.showerror('统计错误', f'绘图失败：{e}')
