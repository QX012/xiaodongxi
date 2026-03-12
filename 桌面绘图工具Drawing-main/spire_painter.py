import os
import time
import ctypes
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageGrab, ImageDraw, ImageFont, ImageEnhance
import cv2
import numpy as np
import keyboard

# ---------------------------------------------------------
# 全局控制变量
# ---------------------------------------------------------
abort_drawing = False

def trigger_abort():
    global abort_drawing
    abort_drawing = True
    print("\n[中断] 接收到 P 键指令，强制停止当前绘制！")

keyboard.on_press_key('p', lambda _: trigger_abort())
keyboard.on_press_key('P', lambda _: trigger_abort())

# ---------------------------------------------------------
# Windows 底层鼠标控制
# ---------------------------------------------------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    pass

MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

def move_mouse(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))

def right_click_down():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)

def right_click_up():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

# ---------------------------------------------------------
# 桌面绘制透明窗口
# ---------------------------------------------------------
class DesktopDrawingOverlay:
    def __init__(self, master, img_path, rx, ry, rw, rh, pen_color='black'):
        self.master = master
        self.img_path = img_path
        self.rx = rx
        self.ry = ry
        self.rw = rw
        self.rh = rh
        self.pen_color = pen_color
        
        self.top = tk.Toplevel(master)
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-topmost', True)
        self.top.attributes('-transparentcolor', 'white')
        self.top.config(cursor="crosshair")
        
        self.canvas = tk.Canvas(self.top, highlightthickness=0, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Key>", self.on_key)
        self.top.focus_set()
        
        # 绘制的线条标签
        self.line_tag = "lineart"
        # 拖动相关变量
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # 创建控制面板
        self.create_control_panel()
        
        # 绑定拖动事件
        self.canvas.bind("<ButtonPress-1>", self.start_canvas_drag)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_canvas_drag)
        
        self.start_drawing()

    def create_control_panel(self):
        """创建悬浮控制面板"""
        self.control_frame = tk.Frame(self.top, bg='#333333', bd=2, relief='raised')
        self.control_frame.place(x=10, y=10)
        
        # 标题
        title = tk.Label(self.control_frame, text="🎨 绘制控制面板", bg='#333333', fg='white', font=('Arial', 10, 'bold'))
        title.pack(pady=(5, 10), padx=10)
        
        # 关闭按钮
        close_btn = tk.Button(self.control_frame, text="❌ 关闭窗口", bg='#ff4444', fg='white',
                              command=self.close_window, width=15, height=1)
        close_btn.pack(pady=5, padx=10)
        
        # 最小化按钮
        minimize_btn = tk.Button(self.control_frame, text="🗕 最小化", bg='#2196F3', fg='white',
                                 command=self.minimize_window, width=15, height=1)
        minimize_btn.pack(pady=5, padx=10)
        
        # 置顶/取消置顶按钮
        self.topmost_var = tk.BooleanVar(value=True)
        topmost_btn = tk.Checkbutton(self.control_frame, text="窗口置顶", variable=self.topmost_var,
                                     bg='#333333', fg='white', selectcolor='#555555',
                                     command=self.toggle_topmost, font=('Arial', 9))
        topmost_btn.pack(pady=5, padx=10)
        
        # 提示文字
        hint = tk.Label(self.control_frame, text="快捷键: P=中断绘制\nESC=关闭窗口", 
                        bg='#333333', fg='#aaaaaa', font=('Arial', 8))
        hint.pack(pady=(10, 5), padx=10)
        
        # 让控制面板可以拖动
        self.control_frame.bind("<ButtonPress-1>", self.start_drag)
        self.control_frame.bind("<B1-Motion>", self.on_drag)
        title.bind("<ButtonPress-1>", self.start_drag)
        title.bind("<B1-Motion>", self.on_drag)

    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag(self, event):
        x = self.control_frame.winfo_x() - self.drag_start_x + event.x
        y = self.control_frame.winfo_y() - self.drag_start_y + event.y
        self.control_frame.place(x=x, y=y)

    def close_window(self):
        self.top.destroy()

    def minimize_window(self):
        self.top.iconify()

    def toggle_topmost(self):
        self.top.attributes('-topmost', self.topmost_var.get())

    def start_drawing(self):
        threading.Thread(target=self.draw_on_desktop, daemon=True).start()

    def draw_on_desktop(self):
        global abort_drawing
        abort_drawing = False
        
        time.sleep(0.5)
        
        img = cv2.imdecode(np.fromfile(self.img_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        edges = cv2.bitwise_not(img)
        
        img_h, img_w = edges.shape
        scale = min(self.rw / img_w, self.rh / img_h)
        
        offset_x = self.rx + (self.rw - img_w * scale) / 2
        offset_y = self.ry + (self.rh - img_h * scale) / 2

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        
        current_step = 3
        
        for contour in contours:
            if abort_drawing:
                break
                
            if len(contour) == 0:
                continue
            
            points = []
            for point in contour[::current_step]:
                if abort_drawing:
                    break
                    
                px = int(offset_x + point[0][0] * scale)
                py = int(offset_y + point[0][1] * scale)
                points.append(px)
                points.append(py)
            
            if len(points) >= 4:
                self.canvas.create_line(points, fill=self.pen_color, width=2, smooth=True, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=self.line_tag)
                time.sleep(0.001)
        
        if abort_drawing:
            print("桌面绘制已被中断！")
        else:
            print("桌面绘制完成！使用控制面板或按 ESC 关闭")

    def on_key(self, event):
        if event.keysym.lower() == 'p':
            global abort_drawing
            abort_drawing = True
        elif event.keysym == 'Escape':
            self.close_window()
    
    def start_canvas_drag(self, event):
        """开始拖动"""
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_canvas_drag(self, event):
        """拖动过程"""
        if self.is_dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            
            if abs(dx) > 1 or abs(dy) > 1:  # 减少频繁更新
                # 批量移动所有线条（使用标签）
                self.canvas.move(self.line_tag, dx, dy)
                
                self.drag_start_x = event.x
                self.drag_start_y = event.y
    
    def stop_canvas_drag(self, event):
        """停止拖动"""
        self.is_dragging = False

# ---------------------------------------------------------
# "数字琥珀" 全屏选区界面
# ---------------------------------------------------------
class DigitalAmberOverlay:
    def __init__(self, master, target_image_path, callback, mode='game'):
        self.master = master
        self.target_image_path = target_image_path
        self.callback = callback
        self.mode = mode
        
        self.top = tk.Toplevel(master)
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-topmost', True)
        self.top.config(cursor="crosshair")
        
        screen_img = ImageGrab.grab()
        enhancer = ImageEnhance.Brightness(screen_img)
        self.dimmed_img = enhancer.enhance(0.5)
        
        self.tk_img = ImageTk.PhotoImage(self.dimmed_img)
        
        self.canvas = tk.Canvas(self.top, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self.tk_img, anchor=tk.NW)
        
        self.rect_id = None
        self.start_x = None
        self.start_y = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_drag(self, event):
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        rx = min(self.start_x, end_x)
        ry = min(self.start_y, end_y)
        rw = abs(self.start_x - end_x)
        rh = abs(self.start_y - end_y)
        
        self.top.destroy()
        if rw > 10 and rh > 10:
            self.callback(rx, ry, rw, rh, self.target_image_path)

# ---------------------------------------------------------
# 主程序界面
# ---------------------------------------------------------
class SpirePainterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("杀戮尖塔2 - 数字琥珀画板")
        # 窗口大幅度加宽，为了容纳右侧的预览区
        self.root.geometry("950x650") 
        self.root.attributes('-topmost', True)
        
        self.current_lineart_path = None
        self.last_raw_image_path = None 
        self.tk_preview_image = None # 用于在内存中保持预览图不被回收
        self.output_dir = "output_lines"
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.font_map = {
            "微软雅黑 (默认)": "msyh.ttc",
            "黑体 (粗犷)": "simhei.ttf",
            "楷体 (毛笔)": "simkai.ttf",
            "宋体 (锋利)": "simsun.ttc",
            "仿宋 (清秀)": "simfang.ttf"
        }

        # ---------------------------------------------------------
        # 左右分栏布局
        # ---------------------------------------------------------
        self.left_panel = tk.Frame(root, width=420)
        self.left_panel.pack(side="left", fill="y", padx=10, pady=10)
        self.left_panel.pack_propagate(False) # 锁死左侧宽度

        self.right_panel = tk.Frame(root, bg="#E0E0E0", bd=2, relief="sunken")
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

        # ---------------------------------------------------------
        # 右侧：实时预览面板
        # ---------------------------------------------------------
        tk.Label(self.right_panel, text="实时线稿预览区", font=("Arial", 12, "bold"), bg="#E0E0E0", fg="#333333").pack(pady=10)
        
        # 预览图显示载体
        self.preview_label = tk.Label(self.right_panel, text="（暂无预览）\n请在左侧生成或选择线稿", bg="white", fg="gray")
        self.preview_label.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ---------------------------------------------------------
        # 左侧：操作控制台
        # ---------------------------------------------------------
        self.status_label = tk.Label(self.left_panel, text="请先准备线稿\n(随时按 P 键可紧急停止绘制)", pady=5, fg="blue")
        self.status_label.pack()

        # --- 区域1：图片转线稿 ---
        frame1 = tk.LabelFrame(self.left_panel, text="方案A：外部图片", padx=10, pady=5)
        frame1.pack(fill="x", padx=10, pady=5)
        
        detail_frame = tk.Frame(frame1)
        detail_frame.pack(fill="x")
        tk.Label(detail_frame, text="线稿精细度 (1低=快, 10高=慢):").pack(side="left")
        self.detail_slider = tk.Scale(detail_frame, from_=1, to=10, orient="horizontal", length=140)
        self.detail_slider.set(5) 
        self.detail_slider.pack(side="left", padx=5)

        btn_frame1 = tk.Frame(frame1)
        btn_frame1.pack(fill="x", pady=(5,0))
        self.btn_image = tk.Button(btn_frame1, text="1. 选择图片", command=self.select_image)
        self.btn_image.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.btn_reprocess = tk.Button(btn_frame1, text="2. 刷新线稿", command=self.generate_image_lineart, state=tk.DISABLED)
        self.btn_reprocess.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # --- 区域2：文字转线稿 ---
        frame2 = tk.LabelFrame(self.left_panel, text="方案B：输入文字", padx=10, pady=5)
        frame2.pack(fill="x", padx=10, pady=5)
        
        self.text_input = tk.Entry(frame2)
        self.text_input.insert(0, "输入想画的文字...")
        self.text_input.pack(fill="x", pady=(0, 5))
        
        font_frame = tk.Frame(frame2)
        font_frame.pack(fill="x", pady=2)
        tk.Label(font_frame, text="字体风格:").pack(side="left")
        
        self.font_combo = ttk.Combobox(font_frame, values=list(self.font_map.keys()), state="readonly", width=15)
        self.font_combo.current(0)
        self.font_combo.pack(side="left", padx=5)
        
        self.btn_text = tk.Button(frame2, text="生成文字自适应线稿", command=self.process_text)
        self.btn_text.pack(fill="x", pady=(5, 0))

        # --- 区域3：直接使用已有线稿 ---
        frame3 = tk.LabelFrame(self.left_panel, text="方案C：现成线稿", padx=10, pady=5)
        frame3.pack(fill="x", padx=10, pady=5)
        self.btn_load_existing = tk.Button(frame3, text="打开保存的线稿图进行绘制", command=self.load_existing_lineart)
        self.btn_load_existing.pack(fill="x")

        # --- 区域4：狂暴调速器 ---
        speed_frame = tk.Frame(self.left_panel)
        speed_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(speed_frame, text="绘制速度(跳帧步长):", font=("Arial", 9, "bold")).pack(side="left")
        self.speed_slider = tk.Scale(speed_frame, from_=1, to=15, orient="horizontal", length=200)
        self.speed_slider.set(3)
        self.speed_slider.pack(side="left", padx=5)

        # --- 区域5：笔颜色选择 ---
        color_frame = tk.LabelFrame(self.left_panel, text="笔颜色设置", padx=10, pady=5)
        color_frame.pack(fill="x", padx=10, pady=5)

        self.pen_color = tk.StringVar(value="黑色")
        self.color_map = {
            "黑色": "black",
            "红色": "red",
            "蓝色": "blue",
            "绿色": "green",
            "黄色": "yellow",
            "白色": "white",
            "紫色": "purple",
            "橙色": "orange",
            "粉色": "pink",
            "青色": "cyan"
        }

        color_select_frame = tk.Frame(color_frame)
        color_select_frame.pack(fill="x", pady=2)
        tk.Label(color_select_frame, text="选择颜色:").pack(side="left")
        self.color_combo = ttk.Combobox(color_select_frame, values=list(self.color_map.keys()), state="readonly", width=12)
        self.color_combo.current(0)
        self.color_combo.pack(side="left", padx=5)

        # 自定义颜色
        custom_color_frame = tk.Frame(color_frame)
        custom_color_frame.pack(fill="x", pady=2)
        tk.Label(custom_color_frame, text="自定义(HEX):").pack(side="left")
        self.custom_color_entry = tk.Entry(custom_color_frame, width=10)
        self.custom_color_entry.insert(0, "#000000")
        self.custom_color_entry.pack(side="left", padx=5)
        self.custom_color_btn = tk.Button(custom_color_frame, text="应用", command=self.apply_custom_color, width=6)
        self.custom_color_btn.pack(side="left", padx=2)

        # --- 启动按钮 ---
        self.btn_start_game = tk.Button(self.left_panel, text="🎮 ", bg="#4CAF50", fg="white", 
                                        font=("Arial", 10, "bold"), command=self.start_digital_amber, state=tk.DISABLED, height=2)
        self.btn_start_game.pack(fill="x", padx=10, pady=(10, 5))
        
        self.btn_start_desktop = tk.Button(self.left_panel, text="🖥️ 桌面直接绘制", bg="#2196F3", fg="white", 
                                           font=("Arial", 10, "bold"), command=self.start_desktop_drawing, state=tk.DISABLED, height=2)
        self.btn_start_desktop.pack(fill="x", padx=10, pady=(0, 10))

    # ---------------------------------------------------------
    # 新增：核心预览更新函数
    # ---------------------------------------------------------
    def update_preview_panel(self, image_path):
        if not image_path or not os.path.exists(image_path):
            return
            
        try:
            # 使用 PIL 读取最新生成的线稿图
            img = Image.open(image_path)
            
            # 获取右侧预览区的实际宽高，留一点边距 (设定最大上限为 500x500)
            max_size = (480, 520) 
            
            # thumbnail 会非常聪明地“等比例缩放”图片，绝对不会拉伸变形
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换为 Tkinter 格式并保持引用，防止闪退消失
            self.tk_preview_image = ImageTk.PhotoImage(img)
            
            # 更新面板显示
            self.preview_label.config(image=self.tk_preview_image, text="", bg="#E0E0E0")
        except Exception as e:
            print(f"预览加载失败: {e}")

    # ---------------------------------------------------------
    # 业务逻辑更新 (所有生成完毕的地方都加上 update_preview_panel)
    # ---------------------------------------------------------
    def select_image(self):
        file_path = filedialog.askopenfilename(title="选择原图片", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            self.last_raw_image_path = file_path
            self.btn_reprocess.config(state=tk.NORMAL)
            self.generate_image_lineart() 

    def generate_image_lineart(self):
        if not self.last_raw_image_path: return
        
        img = cv2.imdecode(np.fromfile(self.last_raw_image_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        detail = self.detail_slider.get() 

        k_size = int(max(1, (11 - detail) // 2 * 2 + 1))
        if k_size > 1:
            img = cv2.GaussianBlur(img, (k_size, k_size), 0)

        lower_thresh = int(180 - detail * 15)
        upper_thresh = int(250 - detail * 15)
        
        edges = cv2.Canny(img, lower_thresh, upper_thresh)
        inverted = cv2.bitwise_not(edges)
        
        save_path = os.path.join(self.output_dir, "last_image_lineart.png")
        cv2.imencode('.png', inverted)[1].tofile(save_path)
        
        self.current_lineart_path = save_path
        self.status_label.config(text=f"图片线稿已生成/刷新！\n(当前精细度: {detail})")
        self.btn_start_game.config(state=tk.NORMAL)
        self.btn_start_desktop.config(state=tk.NORMAL)
        
        # 触发预览刷新！
        self.update_preview_panel(save_path)

    def process_text(self):
        text = self.text_input.get()
        if not text or text == "输入想画的文字...":
            messagebox.showwarning("提示", "请先输入文字！")
            return
            
        selected_font_name = self.font_combo.get()
        actual_font_file = self.font_map.get(selected_font_name, "msyh.ttc")
        
        try:
            fnt = ImageFont.truetype(actual_font_file, 150) 
        except:
            fnt = ImageFont.load_default()
            messagebox.showwarning("提示", f"未能在系统中找到 {selected_font_name} 的文件，已使用默认英文字体。")
            
        dummy_img = Image.new('RGB', (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), text, font=fnt)
        
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        padding = 20
        canvas_w = int(text_w + padding * 2)
        canvas_h = int(text_h + padding * 2)
        
        img = Image.new('RGB', (canvas_w, canvas_h), color='white')
        d = ImageDraw.Draw(img)
        
        draw_x = padding - bbox[0]
        draw_y = padding - bbox[1]
        d.text((draw_x, draw_y), text, font=fnt, fill='black')
        
        open_cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(open_cv_image, 100, 200)
        inverted = cv2.bitwise_not(edges)
        
        save_path = os.path.join(self.output_dir, "last_text_lineart.png")
        cv2.imencode('.png', inverted)[1].tofile(save_path)
        
        self.current_lineart_path = save_path
        self.status_label.config(text=f"自适应文字线稿已生成！\n({selected_font_name})")
        self.btn_start_game.config(state=tk.NORMAL)
        self.btn_start_desktop.config(state=tk.NORMAL)
        
        # 触发预览刷新！
        self.update_preview_panel(save_path)

    def load_existing_lineart(self):
        initial_dir = os.path.abspath(self.output_dir)
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="选择已保存的线稿图",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")]
        )
        if file_path:
            self.current_lineart_path = file_path
            self.status_label.config(text=f"已加载线稿: {os.path.basename(file_path)}")
            self.btn_start_game.config(state=tk.NORMAL)
            self.btn_start_desktop.config(state=tk.NORMAL)
            
            # 触发预览刷新！
            self.update_preview_panel(file_path)

    def apply_custom_color(self):
        custom_hex = self.custom_color_entry.get().strip()
        if custom_hex.startswith('#') and len(custom_hex) == 7:
            try:
                int(custom_hex[1:], 16)
                self.status_label.config(text=f"自定义颜色已应用: {custom_hex}")
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的HEX颜色代码，如 #FF0000")
        else:
            messagebox.showwarning("提示", "请输入有效的HEX颜色代码，如 #FF0000")

    def get_pen_color(self):
        selected_color = self.color_combo.get()
        custom_hex = self.custom_color_entry.get().strip()

        # 优先使用下拉框选择的颜色（只要不是默认的黑色）
        mapped_color = self.color_map.get(selected_color, "black")
        if mapped_color != "black":
            return mapped_color

        # 如果下拉框选择的是黑色，再检查是否有有效的自定义颜色
        if custom_hex.startswith('#') and len(custom_hex) == 7:
            try:
                int(custom_hex[1:], 16)
                return custom_hex
            except ValueError:
                pass

        return "black"

    def start_digital_amber(self):
        self.root.iconify()
        self.root.after(200, self.launch_overlay)

    def start_desktop_drawing(self):
        self.root.iconify()
        self.root.after(200, self.launch_desktop_overlay)

    def launch_overlay(self):
        DigitalAmberOverlay(self.root, self.current_lineart_path, self.run_draw_thread)

    def launch_desktop_overlay(self):
        DigitalAmberOverlay(self.root, self.current_lineart_path, self.run_desktop_draw_thread)

    def run_draw_thread(self, rx, ry, rw, rh, img_path):
        threading.Thread(target=self.draw_logic, args=(rx, ry, rw, rh, img_path), daemon=True).start()

    def run_desktop_draw_thread(self, rx, ry, rw, rh, img_path):
        pen_color = self.get_pen_color()
        DesktopDrawingOverlay(self.root, img_path, rx, ry, rw, rh, pen_color)

    def draw_logic(self, rx, ry, rw, rh, img_path):
        global abort_drawing
        abort_drawing = False 
        
        time.sleep(1) 
        
        img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        edges = cv2.bitwise_not(img) 
        
        img_h, img_w = edges.shape
        scale = min(rw / img_w, rh / img_h)
        
        offset_x = rx + (rw - img_w * scale) / 2
        offset_y = ry + (rh - img_h * scale) / 2

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        
        current_step = self.speed_slider.get()
        
        for contour in contours:
            if abort_drawing:
                break
                
            if len(contour) == 0:
                continue
            
            start_x = int(offset_x + contour[0][0][0] * scale)
            start_y = int(offset_y + contour[0][0][1] * scale)
            move_mouse(start_x, start_y)
            time.sleep(0.005) 
            
            right_click_down()
            time.sleep(0.005) 
            
            for point in contour[1::current_step]:
                if abort_drawing:
                    break
                    
                px = int(offset_x + point[0][0] * scale)
                py = int(offset_y + point[0][1] * scale)
                move_mouse(px, py)
                time.sleep(0.002) 
            
            right_click_up()
            time.sleep(0.005) 
        
        if abort_drawing:
            print("绘图已被玩家强行中断！")
        else:
            print("绘制顺利完成！")

if __name__ == "__main__":
    root = tk.Tk()
    app = SpirePainterApp(root)
    root.mainloop()