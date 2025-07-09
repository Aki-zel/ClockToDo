import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os
import time
from datetime import datetime
from stats import show_stats

DATA_FILE = 'todo.json'

# 全局统一 pastel_colors
PASTEL_COLORS = [
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94',
    '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
    '#b3e2cd', '#fdcdac', '#cbd5e8', '#f4cae4', '#e6f5c9', '#fff2ae',
    '#f1e2cc', '#cccccc'
]

class ClockToDoApp:
    def __init__(self, root):
        self.root = root
        self.root.title('ClockToDo')
        self.root.iconbitmap('clockToDo.ico')
        self.tasks = []
        self.load_data()
        self.current_task = None
        self.timer_running = False
        self.start_time = None
        self.stats_period = '今日'  # 新增：统计周期，默认今日
        self.build_ui()

    def build_ui(self):
        # 设置主窗口渐变背景色（通过Canvas绘制）
        self.root.update_idletasks()
        w, h = self.root.winfo_width() or 900, self.root.winfo_height() or 600
        bg_canvas = tk.Canvas(self.root, width=w, height=h, highlightthickness=0)
        bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        for i in range(h):
            color = f'#f7f7f7' if i < h//2 else f'#ffe4b2'
            bg_canvas.create_line(0, i, w, i, fill=color)
        self.root.lift()  # 保证控件在canvas之上
        self.root.resizable(True, True)  # 允许窗口拉伸
        main_frame = tk.Frame(self.root, highlightthickness=0)
        main_frame.grid(row=0, column=0, sticky='nsew')
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)
        # 左侧：任务与操作
        left_frame = tk.Frame(main_frame, highlightthickness=0)
        left_frame.grid(row=0, column=0, sticky='ns', padx=(20, 10), pady=10)
        title = tk.Label(left_frame, text='ClockToDo 任务管理', font=('微软雅黑', 18, 'bold'), fg='#d35400')
        title.pack(pady=(8, 8))
        # 日历区
        self.selected_calendar_date = None
        try:
            import tkcalendar
            cal_frame = tk.Frame(left_frame)
            cal_frame.pack(pady=(0, 8))
            from tkcalendar import Calendar
            self.calendar = Calendar(
                cal_frame,
                selectmode='day',
                date_pattern='yyyy-mm-dd',
                font=('微软雅黑', 10),
                background='#fff2cc',
                disabledbackground='#f7f7f7',
                bordercolor='#d35400',
                headersbackground='#f6b26b',
                normalbackground='#fff',
                weekendbackground='#ffe4b2',
                foreground='#333',
                headersforeground='#d35400',
                weekendforeground='#e06666',
                selectforeground='#fff',
            )
            self.calendar.pack()
            self.calendar.bind('<<CalendarSelected>>', self.on_calendar_select)
        except ImportError:
            tk.Label(left_frame, text='(可选)安装tkcalendar以显示日历', font=('微软雅黑', 9), fg='#aaa').pack(pady=(0, 8))
        tk.Label(left_frame, text='任务列表', font=('微软雅黑', 12), fg='#333').pack(anchor='w')
        # 用ttk.Treeview替换Listbox实现任务列表
        import tkinter.ttk as ttk
        task_style = ttk.Style()
        task_style.theme_use('default')
        task_style.configure('Task.Treeview',
            background='#fdf6e3',
            fieldbackground='#fdf6e3',
            borderwidth=0,
            relief='flat',
            rowheight=28,
            font=('微软雅黑', 12),
        )
        task_style.map('Task.Treeview',
            background=[('selected', '#ffd966')],
            foreground=[('selected', '#d35400')]
        )
        self.task_tree_frame = tk.Frame(left_frame, bg='#fdf6e3', highlightthickness=0, bd=0)
        self.task_tree_frame.pack(pady=4, fill='x')
        self.task_tree = ttk.Treeview(
            self.task_tree_frame,
            columns=(),
            show='tree',  # 只显示内容，不显示表头
            height=10,
            style='Task.Treeview',
            selectmode='browse'
        )
        self.task_tree.column('#0', anchor='center', width=220, stretch=True)  # 让内容居中
        self.task_tree.pack(fill='x', expand=True)
        self.refresh_task_list()
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text='添加任务', font=('微软雅黑', 10), bg='#f6b26b', fg='white', width=12, command=self.add_task, relief='flat', activebackground='#ffd966').pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='删除任务', font=('微软雅黑', 10), bg='#e06666', fg='white', width=12, command=self.delete_task, relief='flat', activebackground='#f4cccc').pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='开始计时', font=('微软雅黑', 10), bg='#6fa8dc', fg='white', width=12, command=self.start_timer, relief='flat', activebackground='#cfe2f3').pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='结束计时', font=('微软雅黑', 10), bg='#b4a7d6', fg='white', width=12, command=self.stop_timer, relief='flat', activebackground='#d9d2e9').pack(side=tk.LEFT, padx=6)
        self.timer_label = tk.Label(left_frame, text='计时: 00:00:00', font=('微软雅黑', 16, 'bold'), fg='#3d85c6')
        self.timer_label.pack(pady=12)
        # 右侧：统计
        right_frame = tk.Frame(main_frame, highlightthickness=0)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 20), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        stats_top = tk.Frame(right_frame)
        stats_top.pack(anchor='n', pady=(0, 8))
        tk.Label(stats_top, text='统计周期:', font=('微软雅黑', 11), fg='#333').pack(side=tk.LEFT, padx=8)
        for period, color in zip(['今日', '本周', '本月', '本年'], ['#f6b26b', '#6fa8dc', '#93c47d', '#e06666']):
            tk.Button(stats_top, text=period, font=('微软雅黑', 10), bg=color, fg='white', width=8, command=lambda p=period: self.set_stats_period_and_update(p, auto_update=True), relief='flat', activebackground='#ffe4b2').pack(side=tk.LEFT, padx=4)
        self.stats_label = tk.Label(stats_top, text=f'当前统计周期: {self.stats_period}', font=('微软雅黑', 10), fg='#666')
        self.stats_label.pack(side=tk.LEFT, padx=10)
        # 统计图显示区
        self.stats_canvas = None
        self.stats_fig = None
        self.stats_canvas_frame = tk.Frame(right_frame)
        self.stats_canvas_frame.pack(fill='both', expand=True)
        self.show_statistics()

    def refresh_task_list(self):
        # Treeview无表头版本
        for i in self.task_tree.get_children():
            self.task_tree.delete(i)
        n = len(self.tasks)
        pastel = PASTEL_COLORS
        while len(pastel) < n:
            pastel = pastel * 2
        for idx, task in enumerate(self.tasks):
            tag = f'taskcolor{idx}'
            self.task_tree.insert('', 'end', text=task['name'], tags=(tag,))
            self.task_tree.tag_configure(tag, background=pastel[idx])

    def add_task(self):
        name = simpledialog.askstring('添加任务', '请输入任务名称:')
        if name:
            self.tasks.append({'name': name, 'records': []})
            self.save_data()
            self.refresh_task_list()

    def delete_task(self):
        idxs = self.task_tree.selection()
        if not idxs:
            messagebox.showwarning('提示', '请先选择要删除的任务')
            return
        idx = self.task_tree.index(idxs[0])
        task_name = self.tasks[idx]['name']
        if not self.tasks[idx]['records']:
            if messagebox.askyesno('确认删除', f'确定要删除任务“{task_name}”？'):
                del self.tasks[idx]
                self.save_data()
                self.refresh_task_list()
        else:
            res = messagebox.askyesnocancel('删除任务', f'是否同时删除该任务的所有计时记录？\n是：删除任务及记录\n否：仅删除任务，保留记录到新任务“{task_name}_记录”\n取消：不删除')
            if res is None:
                return
            elif res:
                del self.tasks[idx]
            else:
                records = self.tasks[idx]['records']
                del self.tasks[idx]
                self.tasks.append({'name': f'{task_name}_记录', 'records': records})
            self.save_data()
            self.refresh_task_list()

    def start_timer(self):
        idxs = self.task_tree.selection()
        if not idxs:
            messagebox.showwarning('提示', '请先选择一个任务')
            return
        if self.timer_running:
            messagebox.showinfo('提示', '已有计时在进行')
            return
        self.current_task = self.task_tree.index(idxs[0])
        self.start_time = time.time()
        self.timer_running = True
        self.update_timer()

    def update_timer(self):
        if self.timer_running:
            elapsed = int(time.time() - self.start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.timer_label.config(text=f'计时: {h:02}:{m:02}:{s:02}')
            self.root.after(1000, self.update_timer)

    def stop_timer(self):
        if not self.timer_running:
            messagebox.showinfo('提示', '没有正在计时的任务')
            return
        end_time = time.time()
        elapsed = int(end_time - self.start_time)
        record = {
            'start': datetime.fromtimestamp(self.start_time).isoformat(),
            'end': datetime.fromtimestamp(end_time).isoformat(),
            'duration': elapsed
        }
        self.tasks[self.current_task]['records'].append(record)
        self.save_data()
        self.timer_running = False
        self.timer_label.config(text='计时: 00:00:00')
        messagebox.showinfo('完成', f'本次计时：{elapsed//60}分{elapsed%60}秒')

    def set_stats_period_and_update(self, period, auto_update=False):
        self.stats_period = period
        self.stats_label.config(text=f'当前统计周期: {self.stats_period}')
        if auto_update:
            self.show_statistics()

    def on_calendar_select(self, event):
        date_str = self.calendar.get_date()  # yyyy-mm-dd
        self.selected_calendar_date = date_str
        self.show_statistics(force_day=date_str)

    def show_statistics(self, force_day=None):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import matplotlib.pyplot as plt
        import numpy as np  # 新增
        from stats import PERIODS
        # 清理旧图
        for widget in self.stats_canvas_frame.winfo_children():
            widget.destroy()
        self.stats_fig = plt.Figure(figsize=(5, 5), dpi=100)
        ax = self.stats_fig.add_subplot(111)
        period_map = dict(PERIODS)
        period_type = period_map.get(self.stats_period, 'day')
        now = datetime.now()
        labels = []
        values = []
        for task in self.tasks:
            total = 0
            for rec in task.get('records', []):
                try:
                    start = datetime.fromisoformat(str(rec['start']))
                    duration = int(float(rec['duration']))
                except Exception:
                    continue
                if force_day:
                    # 只显示选中日期的记录
                    if start.strftime('%Y-%m-%d') == force_day:
                        total += duration
                else:
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
            if force_day:
                msg = f'{force_day} 暂无计时记录'
            else:
                msg = '该周期暂无计时记录'
            tk.Label(self.stats_canvas_frame, text=msg, font=('微软雅黑', 12), fg='#e06666').pack()
            return
        # 下移饼图本身，为标题和饼图留出更大间隔
        self.stats_fig.subplots_adjust(top=0.78, bottom=0.08)
        # 1. 生成高效浅色系配色
        pastel_colors = PASTEL_COLORS
        while len(pastel_colors) < len(labels):
            pastel_colors = pastel_colors * 2
        pastel_colors = pastel_colors[:len(labels)]
        # 2. 清理旧表格
        if hasattr(self, 'stats_table') and self.stats_table:
            self.stats_table.destroy()
        # 3. 绘制饼图，使用浅色系
        wedges, _ = ax.pie(
            values,
            labels=None,
            startangle=90,
            labeldistance=1.10,
            wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
            colors=pastel_colors[:len(labels)]
        )
        # 在饼图内部显示计划名称，字体大小自适应，过小不显示
        for i, wedge in enumerate(wedges):
            ang = (wedge.theta2 + wedge.theta1) / 2.
            angle_span = wedge.theta2 - wedge.theta1
            r = 0.6
            x = r * np.cos(np.deg2rad(ang))
            y = r * np.sin(np.deg2rad(ang))
            if angle_span < 15:
                continue  # 小扇形不显示名称，外部注释时处理
            fontsize = int(10 + 4 * min(angle_span, 60) / 60)
            # 修正：下半部分文字不倒置
            display_ang = ang
            if 90 < (ang % 360) < 270:
                display_ang += 180
            ax.text(
                x, y, labels[i],
                ha='center', va='center',
                fontsize=fontsize, color='#333', fontweight='bold',
                rotation=display_ang, rotation_mode='default'
            )
        # 在外部添加小时数注释（小扇形合并任务名，大扇形只显示小时）
        for i, (wedge, value) in enumerate(zip(wedges, values)):
            ang = (wedge.theta2 + wedge.theta1) / 2.
            angle_span = wedge.theta2 - wedge.theta1
            x = np.cos(np.deg2rad(ang))
            y = np.sin(np.deg2rad(ang))
            if angle_span < 15:
                label = f"{labels[i]} {value:.2f}小时"
            else:
                label = f"{value:.2f}小时"
            ax.annotate(
                label,
                xy=(x, y),
                xytext=(1.35 * x, 1.10 * y + (0.18 if y > 0.2 else -0.18)),
                ha='center', va='center',
                fontsize=11,
                arrowprops=dict(
                    arrowstyle='-', color='#888', lw=1,
                    connectionstyle="angle3,angleA=0,angleB=90"
                ),
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#ccc', lw=0.5, alpha=0.8)
            )
        if force_day:
            ax.set_title(f'{force_day} 各任务专注时间（小时）', fontsize=14, pad=30)
        else:
            ax.set_title(f'{self.stats_period}各任务累计专注时间（小时）', fontsize=14, pad=30)
        self.stats_canvas = FigureCanvasTkAgg(self.stats_fig, master=self.stats_canvas_frame)
        self.stats_canvas.draw()
        self.stats_canvas.get_tk_widget().pack()
        # 4. 在饼图下方添加美化表格
        import tkinter.ttk as ttk
        style = ttk.Style()
        style.theme_use('default')
        main_bg = pastel_colors[0]
        style.configure('Custom.Treeview',
            background=main_bg,
            fieldbackground=main_bg,
            borderwidth=0,
            relief='flat',
            rowheight=28,
            font=('微软雅黑', 11),
        )
        style.configure('Custom.Treeview.Heading',
            background='#fffbe6',
            foreground='#d35400',
            font=('微软雅黑', 11, 'bold'),
            borderwidth=0,
            relief='flat',
        )
        style.map('Custom.Treeview', background=[], foreground=[])
        for idx, color in enumerate(pastel_colors[:len(labels)]):
            tag_name = f'rowcolor{idx}'
            style.configure(f'{tag_name}.Custom.Treeview', background=color)
        # 只显示3行，支持下滑
        table_frame = tk.Frame(self.stats_canvas_frame)
        table_frame.pack(side=tk.BOTTOM, fill='x', pady=(10, 0))
        self.stats_table = ttk.Treeview(
            table_frame,
            columns=('计划1', '小时1', '计划2', '小时2'),
            show='headings',
            height=3,
            style='Custom.Treeview',
            selectmode='none'
        )
        self.stats_table.heading('计划1', text='计划')
        self.stats_table.heading('小时1', text='累计小时')
        self.stats_table.heading('计划2', text='计划')
        self.stats_table.heading('小时2', text='累计小时')
        self.stats_table.column('计划1', width=110, anchor='center')
        self.stats_table.column('小时1', width=70, anchor='center')
        self.stats_table.column('计划2', width=110, anchor='center')
        self.stats_table.column('小时2', width=70, anchor='center')
        # 插入数据：每行两个计划
        n = len(labels)
        for row in range(0, n, 2):
            name1 = labels[row]
            hour1 = f'{values[row]:.2f}'
            tag1 = f'rowcolor{row}'
            if row+1 < n:
                name2 = labels[row+1]
                hour2 = f'{values[row+1]:.2f}'
                tag2 = f'rowcolor{row+1}'
            else:
                name2 = ''
                hour2 = ''
                tag2 = ''
            tags = (tag1, tag2) if tag2 else (tag1,)
            self.stats_table.insert('', 'end', values=(name1, hour1, name2, hour2), tags=tags)
            self.stats_table.tag_configure(tag1, background=pastel_colors[row])
            if tag2:
                self.stats_table.tag_configure(tag2, background=pastel_colors[row+1])
        # 不添加垂直滚动条，只显示3行
        self.stats_table.pack(side=tk.LEFT, fill='x', expand=True)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                self.tasks = json.load(f)
        else:
            self.tasks = []

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

def main():
    root = tk.Tk()
    app = ClockToDoApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
