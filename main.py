import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import sys
import os
import time
from datetime import datetime

DATA_FILE = 'todo.json'

# 全局统一 pastel_colors
PASTEL_COLORS = [
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94',
    '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
    '#b3e2cd', '#fdcdac', '#cbd5e8', '#f4cae4', '#e6f5c9', '#fff2ae',
    '#f1e2cc', '#cccccc'
]
def resource_path(relative_path):
    """获取资源文件绝对路径，兼容 PyInstaller 打包后运行环境"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ClockToDoApp:
    def __init__(self, root):
        self.root = root
        self.root.resizable(False, False)
        self.pastel_colors = PASTEL_COLORS
        self.root.title('ClockToDo')
        icon_path = resource_path("clockToDo.ico")
        self.root.iconbitmap(icon_path)
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
        pastel = self.pastel_colors
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
        import matplotlib
        import matplotlib.pyplot as plt
        import numpy as np
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif']
        matplotlib.rcParams['axes.unicode_minus'] = False
        PERIODS = [
            ('今日', 'day'),
            ('本周', 'week'),
            ('本月', 'month'),
            ('本年', 'year')
        ]

        # 清理旧图表控件
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
                    if start.strftime('%Y-%m-%d') == force_day:
                        total += duration
                else:
                    if period_type == 'day' and start.date() == now.date():
                        total += duration
                    elif period_type == 'week' and start.isocalendar()[:2] == now.isocalendar()[:2]:
                        total += duration
                    elif period_type == 'month' and start.month == now.month and start.year == now.year:
                        total += duration
                    elif period_type == 'year' and start.year == now.year:
                        total += duration

            hours = round(total / 3600, 4)
            if hours > 0:
                labels.append(task['name'])
                values.append(hours)

        if all(v == 0 for v in values):
            msg = f'{force_day} 暂无计时记录' if force_day else '该周期暂无计时记录'
            tk.Label(self.stats_canvas_frame, text=msg, font=('微软雅黑', 12), fg='#e06666').pack()
            return

        self.stats_fig.subplots_adjust(top=0.78, bottom=0.08)

        # --- 颜色映射字典（任务名→颜色） ---
        self.task_color_map = {}
        n_colors = len(self.pastel_colors)
        for i, task in enumerate(self.tasks):
            self.task_color_map[task['name']] = self.pastel_colors[i % n_colors]

        # 饼图颜色对应labels
        pie_colors = [self.task_color_map.get(name, '#cccccc') for name in labels]

        wedges, _ = ax.pie(
            values,
            labels=None,
            startangle=90,
            wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
            colors=pie_colors
        )

        import matplotlib.pyplot as plt
        for i, wedge in enumerate(wedges):
            ang = (wedge.theta2 + wedge.theta1) / 2.
            angle_span = wedge.theta2 - wedge.theta1
            r = 0.6
            x = r * np.cos(np.deg2rad(ang))
            y = r * np.sin(np.deg2rad(ang))
            if angle_span < 15:
                continue
            fontsize = int(10 + 4 * min(angle_span, 60) / 60)
            display_ang = ang
            if 90 < (ang % 360) < 270:
                display_ang += 180
            ax.text(
                x, y, labels[i],
                ha='center', va='center',
                fontsize=fontsize, color='#333', fontweight='bold',
                rotation=display_ang, rotation_mode='default'
            )

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

        title_text = f'{force_day} 各任务专注时间（小时）' if force_day else f'{self.stats_period}各任务累计专注时间（小时）'
        ax.set_title(title_text, fontsize=14, pad=30)

        self.stats_canvas = FigureCanvasTkAgg(self.stats_fig, master=self.stats_canvas_frame)
        self.stats_canvas.draw()
        self.stats_canvas.get_tk_widget().pack()

        # --- 统计表（示例为两个表格，带滚动条，3行可视） ---
        import tkinter.ttk as ttk
        style = ttk.Style()
        style.theme_use('default')
        main_bg = '#fffbe6'
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

        # 清理旧表格和滚动条（避免重复创建）
        for attr in ['stats_table_left', 'stats_table_right', 'scrollbar_left', 'scrollbar_right']:
            if hasattr(self, attr) and getattr(self, attr):
                getattr(self, attr).destroy()

        table_frame = tk.Frame(self.stats_canvas_frame)
        table_frame.pack(side=tk.BOTTOM, fill='x', pady=(10, 0))

        # 左侧框架
        left_frame = tk.Frame(table_frame)
        left_frame.pack(side=tk.LEFT, fill='y', expand=True, padx=(0,10))
        self.stats_table_left = ttk.Treeview(
            left_frame,
            columns=('计划', '累计小时'),
            show='headings',
            height=3,
            style='Custom.Treeview',
            selectmode='none'
        )
        self.stats_table_left.heading('计划', text='计划')
        self.stats_table_left.heading('累计小时', text='累计小时')
        self.stats_table_left.column('计划', width=150, anchor='center')
        self.stats_table_left.column('累计小时', width=100, anchor='center')
        self.stats_table_left.pack(side=tk.LEFT, fill='both', expand=True)


        # 右侧框架
        right_frame = tk.Frame(table_frame)
        right_frame.pack(side=tk.LEFT, fill='y', expand=True)
        self.stats_table_right = ttk.Treeview(
            right_frame,
            columns=('计划', '累计小时'),
            show='headings',
            height=3,
            style='Custom.Treeview',
            selectmode='none'
        )
        self.stats_table_right.heading('计划', text='计划')
        self.stats_table_right.heading('累计小时', text='累计小时')
        self.stats_table_right.column('计划', width=150, anchor='center')
        self.stats_table_right.column('累计小时', width=100, anchor='center')
        self.stats_table_right.pack(side=tk.LEFT, fill='both', expand=True)


        # 任务索引分配
        left_indices = [i for i in range(len(labels)) if i % 2 == 0]
        right_indices = [i for i in range(len(labels)) if i % 2 == 1]

        # 插入左表数据，颜色对应
        for i in left_indices:
            tag = f'rowcolor_left_{i}'
            color = self.task_color_map.get(labels[i], '#cccccc')
            self.stats_table_left.insert('', 'end', values=(labels[i], f'{values[i]:.2f}'), tags=(tag,))
            self.stats_table_left.tag_configure(tag, background=color)

        # 插入右表数据，颜色对应
        for i in right_indices:
            tag = f'rowcolor_right_{i}'
            color = self.task_color_map.get(labels[i], '#cccccc')
            self.stats_table_right.insert('', 'end', values=(labels[i], f'{values[i]:.2f}'), tags=(tag,))
            self.stats_table_right.tag_configure(tag, background=color)

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
