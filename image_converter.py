import os
import io
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import threading
import windnd
from concurrent.futures import ThreadPoolExecutor

class ImageConverterApp:
    def __init__(self, root, initial_dir=None):
        self.root = root
        self.root.title("Image_PixSwap - 图片格式转换工具 (多线程版)")
        self.root.geometry("700x600") # 增加高度以容纳文件列表
        
        # 变量
        self.folder_path = tk.StringVar()
        self.target_format = tk.StringVar(value="png")
        self.status_var = tk.StringVar(value="准备就绪: 请把文件夹拖入此处或点击浏览")
        self.file_list_count = 0
        
        self.supported_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}

        # UI 布局
        self.create_widgets()
        
        # 挂载拖拽功能
        try:
            windnd.hook_dropfiles(root, func=self.on_drop)
        except Exception as e:
            print(f"拖拽功能初始化失败: {e}")

        # 如果有初始路径，尝试加载
        if initial_dir and os.path.exists(initial_dir):
            self.folder_path.set(initial_dir)
            self.update_file_preview(initial_dir)
        
    def on_drop(self, filenames):
        if filenames:
            # Windows 拖拽返回的是 bytes，编码取决于系统设置 (GBK/UTF-8/MBCS)
            raw_bytes = filenames[0]
            folder_path = None
            
            # 尝试常见编码，以 "路径存在" 为判断成功的标准
            # mbcs 是 Windows 系统当前 ANSI 代码页，通常最稳妥
            candidates = ['mbcs', 'gbk', 'utf-8', 'shift_jis']
            
            for enc in candidates:
                try:
                    decoded = raw_bytes.decode(enc)
                    if os.path.exists(decoded):
                        folder_path = decoded
                        break
                except Exception:
                    continue
            
            if folder_path:
                if os.path.isdir(folder_path):
                    self.folder_path.set(folder_path)
                    self.log(f"已拖入文件夹: {folder_path}")
                    self.update_file_preview(folder_path)
                elif os.path.isfile(folder_path):
                    # 如果拖入的是文件，自动切换到其所在文件夹
                    parent_dir = os.path.dirname(folder_path)
                    self.folder_path.set(parent_dir)
                    self.log(f"检测到文件，已自动定位到所在文件夹: {parent_dir}")
                    self.update_file_preview(parent_dir)
            else:
                # 均失败，尝试强制解码以便显示错误日志
                try:
                    display_path = raw_bytes.decode('utf-8', errors='replace')
                except:
                    display_path = str(raw_bytes)
                self.log(f"无法识别拖入的路径 (解码失败): {display_path}")

    def create_widgets(self):
        # 0. 统一字体设置 (修复字体不一致问题，强制使用宋体)
        # "SimSun" 是 Windows 下标准的宋体英文名
        self.default_font = ("SimSun", 10)
        
        style = ttk.Style()
        # 配置所有 ttk 组件的默认字体
        style.configure(".", font=self.default_font)
        # 特别配置 Treeview (列表) 的字体和行高
        style.configure("Treeview", font=self.default_font, rowheight=25)
        style.configure("Treeview.Heading", font=self.default_font)
        
        # 1. 顶部区域：设置
        top_frame = ttk.LabelFrame(self.root, text="设置", padding="10")
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 文件夹路径
        path_frame = ttk.Frame(top_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_frame, text="文件夹路径:").pack(side=tk.LEFT)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.folder_path)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(path_frame, text="浏览...", command=self.browse_folder).pack(side=tk.LEFT)
        
        # 格式选择
        format_frame = ttk.Frame(top_frame)
        format_frame.pack(fill=tk.X, pady=5)
        ttk.Label(format_frame, text="目标格式:").pack(side=tk.LEFT)
        
        formats = [("PNG", "png"), ("JPG", "jpg"), ("WebP", "webp")]
        for text, val in formats:
            ttk.Radiobutton(format_frame, text=text, variable=self.target_format, value=val).pack(side=tk.LEFT, padx=10)

        # 2. 中间区域：文件预览 (新功能)
        preview_frame = ttk.LabelFrame(self.root, text="文件夹内容预览", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("filename", "size", "type", "status")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show='headings', selectmode='none')
        
        self.tree.heading("filename", text="文件名")
        self.tree.heading("size", text="大小")
        self.tree.heading("type", text="类型")
        self.tree.heading("status", text="转换进度情况")
        
        self.tree.column("filename", width=250)
        self.tree.column("size", width=80)
        self.tree.column("type", width=60)
        self.tree.column("status", width=100, anchor=tk.CENTER)
        
        # 配置颜色标枪
        self.tree.tag_configure('success', foreground='green')
        self.tree.tag_configure('error', foreground='red')
        self.tree.tag_configure('skip', foreground='gray')
        
        scrollbar_y = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
            
        # 3. 操作按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=5)
        self.convert_btn = ttk.Button(btn_frame, text="开始转换", command=self.start_conversion)
        self.convert_btn.pack(ipadx=20, ipady=5)
        
        # 4. 日志区域
        log_frame = ttk.LabelFrame(self.root, text="转换日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5) # expand=False 让它不要抢占太多预览空间
        
        # tk.Text 不是 ttk 组件，需要单独设置字体
        self.log_text = tk.Text(log_frame, height=6, state='disabled', font=self.default_font) 
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar_log = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar_log.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text['yscrollcommand'] = scrollbar_log.set

        # 5. 状态栏
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.update_file_preview(folder)

    def update_file_preview(self, folder_path):
        # 清空现有列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.file_item_map = {} # 重置映射
        
        if not os.path.isdir(folder_path):
            return

        count = 0
        try:
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if not os.path.isfile(file_path):
                    continue
                    
                base, ext = os.path.splitext(filename)
                if ext.lower() in self.supported_exts:
                    size_kb = os.path.getsize(file_path) / 1024
                    item_id = self.tree.insert("", tk.END, values=(filename, f"{size_kb:.1f} KB", ext.lower(), "等待..."))
                    self.file_item_map[filename] = item_id
                    count += 1
            
            self.file_list_count = count
            self.status_var.set(f"已加载文件夹，发现 {count} 张图片")
            if count == 0:
                 self.log(f"警告: 在 {folder_path} 中未找到支持的图片 (jpg/png/webp等)")
                 
        except Exception as e:
            self.log(f"读取文件列表失败: {e}")

    def log(self, message):
        def _log_action():
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        self.root.after(0, _log_action)
        
    def update_item_status(self, filename, status_text, tag=None):
        if filename in self.file_item_map:
            item_id = self.file_item_map[filename]
            # 获取当前values
            current_values = self.tree.item(item_id, "values")
            # 更新最后一个字段
            new_values = list(current_values)
            new_values[3] = status_text
            
            self.tree.item(item_id, values=new_values, tags=(tag,) if tag else ())

    def process_single_image(self, filename, source_dir, target_fmt, index, total):
        """士兵：专门负责处理单张图片的转换逻辑"""
        try:
            file_path = os.path.join(source_dir, filename)
            base, ext = os.path.splitext(filename)
            process_dir = os.path.join(source_dir, "process")
            
            if not os.path.exists(process_dir):
                os.makedirs(process_dir, exist_ok=True)

            output_filename = f"{base}.{target_fmt}"
            output_path = os.path.join(process_dir, output_filename)
            
            # 简单查重
            if os.path.abspath(file_path) == os.path.abspath(output_path):
                 self.log(f"跳过同名同格式: {filename}")
                 self.root.after(0, self.update_item_status, filename, "跳过", "skip")
                 return False

            # 转换逻辑
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            with io.BytesIO(file_data) as bio:
                with Image.open(bio) as img:
                    img.load()
                    if target_fmt in ['jpg', 'jpeg'] and 'A' in img.mode:
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif target_fmt in ['jpg', 'jpeg'] and img.mode == 'P':
                        img = img.convert('RGB')
                    
                    img.save(output_path, quality=95)

            # 通过 after 方法安全地更新 UI
            self.root.after(0, self.update_item_status, filename, "✔ 完成", "success")
            return True
        except Exception as e:
            self.log(f"失败 {filename}: {str(e)}")
            self.root.after(0, self.update_item_status, filename, "✘ 失败", "error")
            return False

    def convert_images_thread(self):
        """指挥官：负责多线程调度"""
        source_dir = self.folder_path.get()
        target_fmt = self.target_format.get().lower()
        
        if not source_dir or not os.path.isdir(source_dir):
            messagebox.showerror("错误", "无效的文件夹路径")
            self.reset_ui()
            return

        # 1. 自动计算最合适的线程数
        cpu_count = os.cpu_count() or 4
        worker_count = min(cpu_count + 4, 12) 
        
        # 筛选文件
        items = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f)) 
                 and os.path.splitext(f)[1].lower() in self.supported_exts]
        total = len(items)
        
        if total == 0:
            if not messagebox.askyesno("提示", "当前列表似乎没有图片，是否仍要尝试扫描并继续？"):
                self.reset_ui()
                return

        self.log(f"🚀 启动多线程引擎 (核心数: {cpu_count}, 线程数: {worker_count})...")
        self.log(f"目标格式: {target_fmt}")
        
        count = 0
        
        # 2. 使用线程池
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.process_single_image, f, source_dir, target_fmt, i, total): f 
                for i, f in enumerate(items)
            }
            
            # 统计成功数量
            for future in future_to_file:
                try:
                    if future.result(): 
                        count += 1
                except Exception as e:
                     self.log(f"线程执行异常: {e}")
        
        # 3. 完成后的 UI 操作（必须回到主线程）
        def on_finish():
            self.status_var.set(f"完成! 共转换 {count} 张图片")
            messagebox.showinfo("完成", f"处理完成\n共转换 {count} 张图片")
    
            # 自动打开输出文件夹
            try:
                process_dir = os.path.join(source_dir, "process")
                if os.path.exists(process_dir):
                    os.startfile(process_dir)
            except Exception as e:
                self.log(f"自动打开文件夹失败: {e}")
    
            self.reset_ui()

        self.root.after(0, on_finish)

    def start_conversion(self):
        self.convert_btn.config(state='disabled')
        threading.Thread(target=self.convert_images_thread, daemon=True).start()

    def reset_ui(self):
        self.convert_btn.config(state='normal')

if __name__ == "__main__":
    root = tk.Tk()
    
    # Check for arguments (drag and drop onto exe/bat)
    initial_path = None
    if len(sys.argv) > 1:
        potential_path = sys.argv[1]
        if os.path.isdir(potential_path):
            initial_path = potential_path
            
    app = ImageConverterApp(root, initial_path)
    root.mainloop()
