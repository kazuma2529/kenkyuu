import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from threading import Thread

def process_logic(input_path, output_path, sigma=2.5, min_brightness=120, trim_pixels=0):
    """前回の成功したロジックをそのまま使用"""
    img = cv2.imread(str(input_path), -1)
    if img is None: return False
    
    _, mask = cv2.threshold(img, 1, 255, cv2.THRESH_BINARY)
    mask = mask.astype(np.uint8)
    img_float = img.astype(np.float32)
    valid_pixels = img_float[mask > 0]
    
    if len(valid_pixels) == 0: return False

    mu, std = np.mean(valid_pixels), np.std(valid_pixels)
    min_val, max_val = mu - (sigma * std), mu + (sigma * std)
    
    normalized = np.clip((img_float - min_val) / (max_val - min_val), 0, 1)
    output_float = normalized * (255 - min_brightness) + min_brightness
    final_result = cv2.bitwise_and(output_float.astype(np.uint8), output_float.astype(np.uint8), mask=mask)
    
    cv2.imwrite(str(output_path), final_result)
    return True

class CTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CT画像コントラスト一括変換ツール")
        self.root.geometry("500x300")

        # 画面のパーツ作成
        tk.Label(root, text="1. 元画像が入ったフォルダを選択", font=("MS Gothic", 10, "bold")).pack(pady=5)
        self.in_entry = tk.Entry(root, width=60)
        self.in_entry.pack(padx=20)
        tk.Button(root, text="参照", command=self.select_in).pack(pady=5)

        tk.Label(root, text="2. 保存先フォルダを選択", font=("MS Gothic", 10, "bold")).pack(pady=5)
        self.out_entry = tk.Entry(root, width=60)
        self.out_entry.pack(padx=20)
        tk.Button(root, text="参照", command=self.select_out).pack(pady=5)

        self.btn_run = tk.Button(root, text="変換を開始する", command=self.start_thread, bg="#4CAF50", fg="white", font=("MS Gothic", 12, "bold"), height=2)
        self.btn_run.pack(pady=20)

        self.status_label = tk.Label(root, text="待機中", fg="blue")
        self.status_label.pack()

    def select_in(self):
        path = filedialog.askdirectory()
        if path: self.in_entry.delete(0, tk.END); self.in_entry.insert(0, path)

    def select_out(self):
        path = filedialog.askdirectory()
        if path: self.out_entry.delete(0, tk.END); self.out_entry.insert(0, path)

    def start_thread(self):
        # 処理中に画面が固まらないように別スレッドで実行
        Thread(target=self.run_process).start()

    def run_process(self):
        in_dir = Path(self.in_entry.get())
        out_dir = Path(self.out_entry.get())

        if not in_dir.exists() or self.in_entry.get() == "":
            messagebox.showerror("エラー", "入力フォルダを選んでください")
            return

        out_dir.mkdir(parents=True, exist_ok=True)
        files = list(in_dir.glob("*.tif*")) + list(in_dir.glob("*.TIF*"))

        self.btn_run.config(state=tk.DISABLED)
        for i, f in enumerate(files):
            self.status_label.config(text=f"処理中... ({i+1}/{len(files)})")
            process_logic(f, out_dir / f.name)
        
        self.status_label.config(text="完了しました！", fg="green")
        self.btn_run.config(state=tk.NORMAL)
        messagebox.showinfo("成功", f"全 {len(files)} 枚の処理が完了しました。")

if __name__ == "__main__":
    root = tk.Tk()
    app = CTApp(root)
    root.mainloop()