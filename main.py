import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import sys
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict
from matplotlib import pyplot as plt
import tkinter.ttk as ttk # 统一导入ttk

# 数据文件路径
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'todo.json')

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
        try:
            icon_path = resource_path("clockToDo.ico")
            self.root.iconbitmap(icon_path)
        except tk.TclError:
            print("图标 'clockToDo.ico' 未找到，将使用默认图标。")

        self.tasks = []
        self.load_data()
        self.current_task = None
        self.timer_running = False
        self.start_time = None
        
        self.stats_period = '今日'
        self.chart_type_var = tk.StringVar(value='饼图')
        self.sub_period_var = tk.StringVar(value='按天')

        self.build_ui()

    def build_ui(self):
        # 设置主窗口渐变背景色
        self.root.update_idletasks()
        w, h = self.root.winfo_width() or 900, self.root.winfo_height() or 600
        bg_canvas = tk.Canvas(self.root, width=w, height=h, highlightthickness=0)
        bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        for i in range(h):
            color = f'#f7f7f7' if i < h//2 else f'#ffe4b2'
            bg_canvas.create_line(0, i, w, i, fill=color)
        
        main_frame = tk.Frame(self.root, highlightthickness=0, bg='#f7f7f7')
        main_frame.grid(row=0, column=0, sticky='nsew')
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)
        
        # 左侧：任务与操作
        left_frame = tk.Frame(main_frame, highlightthickness=0, bg='#f7f7f7')
        left_frame.grid(row=0, column=0, sticky='ns', padx=(20, 10), pady=10)
        
        title = tk.Label(left_frame, text='ClockToDo 任务管理',
                         font=('微软雅黑', 18, 'bold'), fg='#d35400', bg='#f7f7f7')
        title.pack(pady=(8, 8))
        
        # 日历区
        self.selected_calendar_date = None
        try:
            import tkcalendar
            cal_frame = tk.Frame(left_frame)
            cal_frame.pack(pady=(0, 8))
            from tkcalendar import Calendar
            self.calendar = Calendar(
                cal_frame, selectmode='day', date_pattern='yyyy-mm-dd',
                font=('微软雅黑', 10), background='#fff2cc', disabledbackground='#f7f7f7',
                bordercolor='#d35400', headersbackground='#f6b26b',
                normalbackground='#fff', weekendbackground='#ffe4b2',
                foreground='#333', headersforeground='#d35400',
                weekendforeground='#e06666', selectforeground='#fff'
            )
            self.calendar.pack()
            self.calendar.bind('<<CalendarSelected>>', self.on_calendar_select)
        except ImportError:
            tk.Label(left_frame, text='(可选)安装tkcalendar以显示日历',
                     font=('微软雅黑', 9), fg='#aaa', bg='#f7f7f7').pack(pady=(0, 8))
            
        tk.Label(left_frame, text='任务列表', font=('微软雅黑', 12), fg='#333', bg='#f7f7f7').pack(anchor='w')
        
        # 任务列表 Treeview
        task_style = ttk.Style()
        task_style.theme_use('default')
        task_style.configure('Task.Treeview', background='#fdf6e3', fieldbackground='#fdf6e3',
                             borderwidth=0, relief='flat', rowheight=28, font=('微软雅黑', 12))
        task_style.map('Task.Treeview', background=[('selected', "#000000")], foreground=[('selected', "#ffffff")])
        self.task_tree_frame = tk.Frame(left_frame, bg='#fdf6e3', highlightthickness=0, bd=0)
        self.task_tree_frame.pack(pady=4, fill='x')
        self.task_tree = ttk.Treeview(
            self.task_tree_frame, columns=(), show='tree', height=10,
            style='Task.Treeview', selectmode='browse'
        )
        self.task_tree.column('#0', anchor='center', width=220, stretch=True)
        self.task_tree.pack(fill='x', expand=True, padx=5, pady=5)
        self.refresh_task_list()
        
        btn_frame = tk.Frame(left_frame, bg='#f7f7f7')
        btn_frame.pack(pady=8)
        
        # 操作按钮
        tk.Button(btn_frame, text='添加任务', font=('微软雅黑', 10), bg='#f6b26b', fg='white', width=12, command=self.add_task, relief='flat', activebackground='#ffd966').pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='删除任务', font=('微软雅黑', 10), bg='#e06666', fg='white', width=12, command=self.delete_task, relief='flat', activebackground='#f4cccc').pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='开始计时', font=('微软雅黑', 10), bg='#6fa8dc', fg='white', width=12, command=self.start_timer, relief='flat', activebackground='#cfe2f3').pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text='结束计时', font=('微软雅黑', 10), bg='#b4a7d6', fg='white', width=12, command=self.stop_timer, relief='flat', activebackground='#d9d2e9').pack(side=tk.LEFT, padx=6)

        self.timer_label = tk.Label(left_frame, text='计时: 00:00:00', font=('微软雅黑', 16, 'bold'), fg='#3d85c6', bg='#f7f7f7')
        self.timer_label.pack(pady=12)

        # 右侧：统计
        right_frame = tk.Frame(main_frame, highlightthickness=0, bg='#ffe4b2')
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 20), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        settings_frame = tk.Frame(right_frame, bg='#ffe4b2')
        settings_frame.pack(fill='x', pady=(5, 8))

        # 统计周期选择
        period_frame = tk.Frame(settings_frame, bg='#ffe4b2')
        period_frame.pack(pady=2)
        tk.Label(period_frame, text='统计周期:', font=('微软雅黑', 11), fg='#333', bg='#ffe4b2').pack(side=tk.LEFT, padx=8)
        for period, color in zip(['今日', '本周', '本月', '本年'], ['#f6b26b', '#6fa8dc', '#93c47d', '#e06666']):
            tk.Button(period_frame, text=period, font=('微软雅黑', 10), bg=color, fg='white', width=8,
                      command=lambda p=period: self.set_stats_period_and_update(p, auto_update=True),
                      relief='flat', activebackground='#fff2ae').pack(side=tk.LEFT, padx=4)

        # 图表类型选择
        chart_type_frame = tk.Frame(settings_frame, bg='#ffe4b2')
        chart_type_frame.pack(pady=2)
        tk.Label(chart_type_frame, text='图表类型:', font=('微软雅黑', 11), fg='#333', bg='#ffe4b2').pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(chart_type_frame, text='饼图', variable=self.chart_type_var, value='饼图', command=self.show_statistics).pack(side=tk.LEFT)
        ttk.Radiobutton(chart_type_frame, text='折线图', variable=self.chart_type_var, value='折线图', command=self.show_statistics).pack(side=tk.LEFT, padx=10)

        # 子周期选择器 (默认隐藏)
        self.sub_period_frame = tk.Frame(settings_frame, bg='#ffe4b2')
        tk.Label(self.sub_period_frame, text='粒度:', font=('微软雅黑', 10), fg='#333', bg='#ffe4b2').pack(side=tk.LEFT, padx=8)
        self.sub_day_rb = ttk.Radiobutton(self.sub_period_frame, text='按天', variable=self.sub_period_var, value='按天', command=self.show_statistics)
        self.sub_week_rb = ttk.Radiobutton(self.sub_period_frame, text='按周', variable=self.sub_period_var, value='按周', command=self.show_statistics)
        self.sub_month_rb = ttk.Radiobutton(self.sub_period_frame, text='按月', variable=self.sub_period_var, value='按月', command=self.show_statistics)

        self.stats_label = tk.Label(settings_frame, text=f'当前统计: {self.stats_period}', font=('微软雅黑', 10), fg='#666', bg='#ffe4b2')
        self.stats_label.pack(pady=2)
        
        self.stats_canvas_frame = tk.Frame(right_frame, bg="#fffbe6")
        self.stats_canvas_frame.pack(fill='both', expand=True)

        self.set_stats_period_and_update(self.stats_period, auto_update=True)

    def refresh_task_list(self):
        for i in self.task_tree.get_children():
            self.task_tree.delete(i)
        
        self.task_color_map = {}
        n_colors = len(self.pastel_colors)
        for i, task in enumerate(self.tasks):
            self.task_color_map[task['name']] = self.pastel_colors[i % n_colors]

        for idx, task in enumerate(self.tasks):
            tag = f'taskcolor{idx}'
            color = self.task_color_map.get(task['name'])
            self.task_tree.insert('', 'end', text=f" {task['name']}", tags=(tag,))
            self.task_tree.tag_configure(tag, background=color)

    def add_task(self):
        name = simpledialog.askstring('添加任务', '请输入任务名称:')
        if name:
            if any(t['name'] == name for t in self.tasks):
                messagebox.showwarning('错误', '任务名称已存在！')
                return
            self.tasks.append({'name': name, 'records': []})
            self.save_data()
            self.refresh_task_list()
            self.show_statistics()

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
        else:
            res = messagebox.askyesnocancel(
                '删除任务', f'是否同时删除该任务的所有计时记录？\n是：删除任务及记录\n否：仅删除任务，保留记录到新任务“{task_name}_记录”\n取消：不删除')
            if res is None: return
            elif res:
                del self.tasks[idx]
            else:
                records = self.tasks[idx]['records']
                del self.tasks[idx]
                self.tasks.append({'name': f'{task_name}_记录', 'records': records})
        
        self.save_data()
        self.refresh_task_list()
        self.show_statistics()

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
        self.show_statistics()

    def set_stats_period_and_update(self, period, auto_update=False):
        self.stats_period = period
        
        # **BUG修复**: 仅在切换主周期时设置默认子周期，而不是每次刷新都设置
        if period == '本月':
            self.sub_period_var.set('按天')
        elif period == '本年':
            self.sub_period_var.set('按月')
        
        if auto_update:
            self.show_statistics()

    def on_calendar_select(self, event):
        date_str = self.calendar.get_date()
        self.selected_calendar_date = date_str
        self.show_statistics(force_day=date_str)

    def show_statistics(self, force_day=None):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import matplotlib
        import matplotlib.pyplot as plt
        import numpy as np
        
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif']
        matplotlib.rcParams['axes.unicode_minus'] = False
        
        for widget in self.stats_canvas_frame.winfo_children():
            widget.destroy()

        # **BUG修复**: 将子周期选择器的UI更新逻辑移到这里
        # 这样每次刷新都会根据当前状态决定是否显示，并且不会重置用户的选择
        self.sub_period_frame.pack_forget()
        self.sub_day_rb.pack_forget()
        self.sub_week_rb.pack_forget()
        self.sub_month_rb.pack_forget()
        if self.chart_type_var.get() == '折线图' and not force_day:
            if self.stats_period == '本月':
                self.sub_period_frame.pack(pady=2)
                self.sub_day_rb.pack(side=tk.LEFT)
                self.sub_week_rb.pack(side=tk.LEFT, padx=10)
            elif self.stats_period == '本年':
                self.sub_period_frame.pack(pady=2)
                self.sub_day_rb.pack(side=tk.LEFT)
                self.sub_week_rb.pack(side=tk.LEFT, padx=10)
                self.sub_month_rb.pack(side=tk.LEFT)

        now = datetime.now()
        filtered_records = []
        for task in self.tasks:
            for rec in task.get('records', []):
                try:
                    start = datetime.fromisoformat(str(rec['start']))
                    duration = int(float(rec['duration']))
                except (ValueError, TypeError):
                    continue
                
                is_in_period = False
                if force_day:
                    if start.strftime('%Y-%m-%d') == force_day: is_in_period = True
                else:
                    period_type = {'今日': 'day', '本周': 'week', '本月': 'month', '本年': 'year'}.get(self.stats_period)
                    if period_type == 'day' and start.date() == now.date(): is_in_period = True
                    elif period_type == 'week' and start.isocalendar()[:2] == now.isocalendar()[:2]: is_in_period = True
                    elif period_type == 'month' and start.month == now.month and start.year == now.year: is_in_period = True
                    elif period_type == 'year' and start.year == now.year: is_in_period = True
                
                if is_in_period:
                    filtered_records.append({'start': start, 'duration': duration, 'task_name': task['name']})

        if not filtered_records:
            msg = f'{force_day} 暂无计时记录' if force_day else f'“{self.stats_period}”暂无计时记录'
            tk.Label(self.stats_canvas_frame, text=msg, font=('微软雅黑', 16), fg='#e06666', bg='#fffbe6').pack(pady=50)
            return

        self.stats_fig = plt.Figure(figsize=(5, 5), dpi=100, facecolor='#fffbe6')
        ax = self.stats_fig.add_subplot(111)
        ax.set_facecolor('#fffbe6')
        
        chart_type = self.chart_type_var.get()
        title_prefix = f'{force_day}' if force_day else f'{self.stats_period}'

        # 传递 force_day=force_day
        if chart_type == '饼图':
            self.stats_label.config(text=f'当前统计: {title_prefix}')
            self._draw_pie_chart(ax, filtered_records, title_prefix)
        else: # 折线图
            self._draw_line_chart(ax, filtered_records, title_prefix, force_day=force_day)
        
        self.stats_canvas = FigureCanvasTkAgg(self.stats_fig, master=self.stats_canvas_frame)
        self.stats_canvas.draw()
        self.stats_canvas.get_tk_widget().pack(fill='both', expand=True)

    def _draw_pie_chart(self, ax, records, title_prefix):
        data = defaultdict(float)
        for rec in records:
            data[rec['task_name']] += rec['duration'] / 3600
        
        labels = list(data.keys())
        values = list(data.values())

        pie_colors = [self.task_color_map.get(name, '#cccccc') for name in labels]
        wedges, _ = ax.pie(values, startangle=90, wedgeprops={'linewidth': 1, 'edgecolor': 'white'}, colors=pie_colors)
        
        import numpy as np
        for i, wedge in enumerate(wedges):
             ang = (wedge.theta2 + wedge.theta1) / 2.
             angle_span = wedge.theta2 - wedge.theta1
             r = 0.6
             x, y = r * np.cos(np.deg2rad(ang)), r * np.sin(np.deg2rad(ang))
             if angle_span < 15: continue
             fontsize = int(8 + 4 * min(angle_span, 60) / 60)
             display_ang = ang if not (90 < (ang % 360) < 270) else ang + 180
             ax.text(x, y, labels[i], ha='center', va='center', fontsize=fontsize, color='#333', fontweight='bold', rotation=display_ang, rotation_mode='default')

        for i, (wedge, value) in enumerate(zip(wedges, values)):
            ang = (wedge.theta2 + wedge.theta1) / 2.
            angle_span = wedge.theta2 - wedge.theta1
            x, y = np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))
            hours, minutes = int(value), int(round((value - int(value)) * 60))
            time_str = f"{hours}h" + (f" {minutes}m" if minutes > 0 else "")
            label = f"{labels[i]}\n{time_str}" if angle_span < 15 else time_str
            ax.annotate(label, xy=(x, y), xytext=(1.35 * x, 1.10 * y), ha='center', va='center', fontsize=9,
                        arrowprops=dict(arrowstyle='-', color='#888', lw=1, connectionstyle="angle3,angleA=0,angleB=90"),
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#ccc', lw=0.5, alpha=0.8))

        ax.set_title(f'{title_prefix} 各任务专注时间占比', fontsize=14, pad=20)
        
        self._draw_summary_tables(labels, values)

    def _draw_line_chart(self, ax, records, title_prefix, force_day=None):
        data = defaultdict(float)
        now = datetime.now()
        sub_period_type = self.sub_period_var.get()
        x_labels, y_values = [], []
        title = f'{title_prefix} '

        if self.stats_period == '今日' or force_day:
            title += '各任务用时分布'
            for rec in records:
                data[rec['task_name']] += rec['duration'] / 3600
            sorted_tasks = sorted(data.keys(), key=lambda t: list(self.task_color_map.keys()).index(t) if t in self.task_color_map else -1)
            x_labels = sorted_tasks
            y_values = [data[t] for t in x_labels]
            colors = [self.task_color_map.get(t, '#cccccc') for t in x_labels]
            bars = ax.bar(x_labels, y_values, color=colors)
            plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
            # **功能增强**: 添加数据注释
            for bar in bars:
                yval = bar.get_height()
                if yval > 0:
                    hours,minutes = int(yval), int(round((yval - int(yval)) * 60))
                    ax.text(bar.get_x() + bar.get_width()/2.0, yval, f'{hours}h{minutes}m', va='bottom', ha='center', fontsize=9)
        
        else: # 非'今日'且非force_day的周期性图表
            plot_color = '#6fa8dc' # 默认颜色
            if self.stats_period == '本周':
                title += '每日专注时长'
                plot_color = '#6fa8dc'
                start_of_week = now - timedelta(days=now.weekday())
                for i in range(7): data[(start_of_week + timedelta(days=i)).strftime('%a(%d)')] = 0
                for rec in records: data[rec['start'].strftime('%a(%d)')] += rec['duration'] / 3600
            
            elif self.stats_period == '本月':
                plot_color = '#93c47d'
                if sub_period_type == '按天':
                    title += '每日专注时长 (按天)'
                    days_in_month = (datetime(now.year, now.month + 1, 1) - timedelta(days=1)).day if now.month < 12 else 31
                    for day in range(1, days_in_month + 1): data[day] = 0
                    for rec in records: data[rec['start'].day] += rec['duration'] / 3600
                elif sub_period_type == '按周':
                    title += '每周专注时长'
                    weeks_in_month = sorted(list(set(rec['start'].isocalendar()[1] for rec in records)))
                    for week in weeks_in_month: data[f'W{week}'] = 0
                    for rec in records: data[f'W{rec["start"].isocalendar()[1]}'] += rec['duration'] / 3600
            
            elif self.stats_period == '本年':
                plot_color = '#e06666'
                if sub_period_type == '按月':
                    title += '每月专注时长'
                    for month in range(1, 13): data[datetime(now.year, month, 1).strftime('%b')] = 0
                    for rec in records: data[rec['start'].strftime('%b')] += rec['duration'] / 3600
                elif sub_period_type == '按周':
                    title += '每周专注时长'
                    for week in range(1, 54): data[week] = 0
                    for rec in records: data[rec['start'].isocalendar()[1]] += rec['duration'] / 3600
                    data = {f'W{k}':v for k,v in data.items() if v > 0}
                elif sub_period_type == '按天':
                    title += '每日专注时长'
                    for rec in records: data[rec['start'].strftime('%m-%d')] += rec['duration'] / 3600
                    data = {k:v for k,v in sorted(data.items())}

            x_labels = list(data.keys())
            y_values = list(data.values())
            ax.plot(x_labels, y_values, marker='o', linestyle='-', color=plot_color)
            offset = max(y_values) * 0.01
            # **功能增强**: 添加数据注释
            for x, y in zip(x_labels, y_values):
                if y > 0:
                    hours,minutes = int(y), int(round((y - int(y)) * 60))
                    ax.text(x, y+offset, f' {hours}h{minutes}m', va='bottom', ha='left' if str(x)[0] != 'W' else 'center', fontsize=9)
            
            if self.stats_period == '本年' and sub_period_type == '按天':
                ax.xaxis.set_major_locator(plt.MaxNLocator(8))
                plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        
        ax.set_title(title, fontsize=14, pad=20)
        ax.set_ylabel('时长 (小时)')
        ax.grid(True, linestyle='--', alpha=0.6)
        self.stats_fig.tight_layout(pad=2.0)
        self.stats_label.config(text=f'当前图表: {title.replace(" ", "")}')

    def _draw_summary_tables(self, labels, values):
        style = ttk.Style()
        style.theme_use('default')
        main_bg = '#fffbe6'
        style.configure('Custom.Treeview', background=main_bg, fieldbackground=main_bg, borderwidth=0, relief='flat', rowheight=28, font=('微软雅黑', 11))
        style.configure('Custom.Treeview.Heading', background='#fff2cc', foreground='#d35400', font=('微软雅黑', 11, 'bold'), borderwidth=0, relief='flat')
        style.map('Custom.Treeview', background=[], foreground=[])
        
        table_frame = tk.Frame(self.stats_canvas_frame, bg=main_bg)
        table_frame.pack(side=tk.BOTTOM, fill='x', pady=(10, 0), padx=10)

        mid_index = (len(labels) + 1) // 2
        left_data = list(zip(labels[:mid_index], values[:mid_index]))
        right_data = list(zip(labels[mid_index:], values[mid_index:]))
        
        self._create_table_in_frame(table_frame, left_data, 'left')
        if right_data:
            self._create_table_in_frame(table_frame, right_data, 'right')

    def _create_table_in_frame(self, parent_frame, data, side):
        frame = tk.Frame(parent_frame, bg='#fffbe6')
        frame.pack(side=tk.LEFT if side == 'left' else tk.RIGHT, fill='x', expand=True, padx=(0, 5 if side == 'left' else 0))
        
        table = ttk.Treeview(
            frame, columns=('计划', '累计时长'), show='headings',
            height= 3,
            style='Custom.Treeview', selectmode='none'
        )
        table.heading('计划', text='计划')
        table.heading('累计时长', text='累计时长')
        table.column('计划', width=120, anchor='center')
        table.column('累计时长', width=100, anchor='center')
        table.pack(side=tk.LEFT, fill='both', expand=True)

        for label, value in data:
            tag = f'rowcolor_{label.replace(" ", "_")}'
            color = self.task_color_map.get(label, '#cccccc')
            hours, minutes = int(value), int(round((value - int(value)) * 60))
            time_str = f"{hours}h" + (f" {minutes}m" if minutes > 0 else "")
            table.insert('', 'end', values=(label, time_str), tags=(tag,))
            table.tag_configure(tag, background=color)

    def verify_data_file(self):
        """验证数据文件的完整性和安全性"""
        if not os.path.exists(DATA_FILE):
            return True
            
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return False
                if "tasks" not in data or "daily_records" not in data:
                    return False
                return True
        except Exception:
            return False

    def save_data(self):
        try:
            # 重构为按天记录的格式
            daily_records = {}
            task_list = []
            
            # 收集所有任务名称
            for task in self.tasks:
                task_list.append({"name": task["name"]})
                for record in task.get("records", []):
                    date = datetime.fromisoformat(record["start"]).strftime("%Y-%m-%d")
                    if date not in daily_records:
                        daily_records[date] = []
                        
                    daily_records[date].append({
                        "task": task["name"],
                        "start": datetime.fromisoformat(record["start"]).strftime("%H:%M:%S"),
                        "end": datetime.fromisoformat(record["end"]).strftime("%H:%M:%S"),
                        "duration": record["duration"]
                    })
            
            # 按日期排序
            sorted_data = {
                "tasks": task_list,
                "daily_records": dict(sorted(daily_records.items(), reverse=True))
            }
            
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(sorted_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror('保存错误', f'保存数据失败：{e}')

    def load_data(self):
        # 确保数据目录存在
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        if os.path.exists(DATA_FILE):
            if not self.verify_data_file():
                messagebox.showerror('错误', '数据文件可能已损坏或被篡改')
                self.tasks = []
                return
                
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 加载任务列表
                self.tasks = []
                for task in data.get('tasks', []):
                    self.tasks.append({
                        'name': task['name'],
                        'records': []
                    })
                    
                # 加载每日记录
                for date, records in data.get('daily_records', {}).items():
                    for record in records:
                        # 找到对应任务并添加记录
                        for task in self.tasks:
                            if task['name'] == record['task']:
                                # 转换时间格式
                                date_str = date
                                start_time = datetime.strptime(f"{date_str} {record['start']}", "%Y-%m-%d %H:%M:%S")
                                end_time = datetime.strptime(f"{date_str} {record['end']}", "%Y-%m-%d %H:%M:%S")
                                
                                task['records'].append({
                                    'start': start_time.isoformat(),
                                    'end': end_time.isoformat(),
                                    'duration': record['duration']
                                })
                                break
            except Exception as e:
                messagebox.showerror('错误', f'加载数据文件时出错: {str(e)}')
                self.tasks = []
                return
                
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 初始化任务列表
                self.tasks = []
                task_dict = {}
                
                # 创建任务
                for task in data.get("tasks", []):
                    task_dict[task["name"]] = {"name": task["name"], "records": []}
                    self.tasks.append(task_dict[task["name"]])
                
                # 加载每日记录
                for date, records in data.get("daily_records", {}).items():
                    for record in records:
                        task_name = record["task"]
                        if task_name in task_dict:
                            # 转换回程序内部格式
                            start_time = f"{date}T{record['start']}"
                            end_time = f"{date}T{record['end']}"
                            
                            task_dict[task_name]["records"].append({
                                "start": start_time,
                                "end": end_time,
                                "duration": record["duration"]
                            })
                            
            except (json.JSONDecodeError, TypeError) as e:
                messagebox.showerror('读取错误', f'读取数据文件失败，文件可能已损坏：{e}')
                self.tasks = []
            except Exception as e:
                messagebox.showerror('读取错误', f'读取数据时发生未知错误：{e}')
                self.tasks = []
        else:
            # 如果文件不存在，则初始化为空列表
            self.tasks = []



def main():
    root = tk.Tk()
    app = ClockToDoApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()