import tkinter as tk
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CoordinateFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("DBD 좌표 추출기")
        self.root.geometry("320x270")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # 파란색 아이콘 적용
        try:
            self.root.iconbitmap(resource_path('coord_icon.ico'))
        except Exception:
            pass

        self.top = tk.IntVar(value=0)
        self.left = tk.IntVar(value=0)
        self.width = tk.IntVar(value=0)
        self.height = tk.IntVar(value=0)

        tk.Label(root, text="1. 게임을 창 모드나 전체 창 모드로 켭니다.\n2. 아래 버튼을 누르고 원하는 영역을 드래그하세요.", pady=10).pack()

        snip_btn = tk.Button(root, text="영역 지정하기 (클릭)", command=self.start_snip, bg="#87CEFA", font=("Helvetica", 11, "bold"))
        snip_btn.pack(pady=5)

        frame = tk.Frame(root)
        frame.pack(pady=10)

        tk.Label(frame, text="Top (Y):").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        tk.Entry(frame, textvariable=self.top, width=10, state="readonly").grid(row=0, column=1, padx=5, pady=2)

        tk.Label(frame, text="Left (X):").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        tk.Entry(frame, textvariable=self.left, width=10, state="readonly").grid(row=1, column=1, padx=5, pady=2)

        tk.Label(frame, text="Width (너비):").grid(row=2, column=0, padx=5, pady=2, sticky="e")
        tk.Entry(frame, textvariable=self.width, width=10, state="readonly").grid(row=2, column=1, padx=5, pady=2)

        tk.Label(frame, text="Height (높이):").grid(row=3, column=0, padx=5, pady=2, sticky="e")
        tk.Entry(frame, textvariable=self.height, width=10, state="readonly").grid(row=3, column=1, padx=5, pady=2)

    def start_snip(self):
        self.snip_win = tk.Toplevel(self.root)
        self.snip_win.attributes("-fullscreen", True)
        self.snip_win.attributes("-alpha", 0.3)
        self.snip_win.config(cursor="cross")
        
        self.canvas = tk.Canvas(self.snip_win, cursor="cross", bg="gray")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.snip_win.bind("<Escape>", lambda e: self.snip_win.destroy())

        self.start_x = None
        self.start_y = None
        self.rect = None

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='blue', width=2, fill="black")

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        self.snip_win.destroy()

        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        width = abs(self.start_x - end_x)
        height = abs(self.start_y - end_y)

        self.top.set(top)
        self.left.set(left)
        self.width.set(width)
        self.height.set(height)

if __name__ == "__main__":
    root = tk.Tk()
    app = CoordinateFinder(root)
    root.mainloop()