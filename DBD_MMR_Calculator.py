import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys

# --- 실행 파일 위치 찾기 (데이터 저장용) ---
def get_app_path():
    """실행 중인 .exe 파일이 위치한 실제 폴더 경로를 반환합니다."""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 .exe로 실행할 경우
        return os.path.dirname(sys.executable)
    else:
        # 일반 .py 스크립트로 실행할 경우
        return os.path.dirname(os.path.abspath(__file__))

# --- 이미지 경로 설정 함수 (내부 리소스용) ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 앱 실행 경로를 기준으로 저장 파일 위치 고정
DATA_FILE = os.path.join(get_app_path(), "mmr_data.json")

def load_data():
    default_data = {"survivor_mmr": 0, "killer_mmr": 0, "prev_survivor_mmr": 0, "prev_killer_mmr": 0}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for key in default_data:
                    if key not in loaded: loaded[key] = default_data[key]
                return loaded
        except Exception:
            pass
    return default_data

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print("데이터 저장 실패:", e)

# --- MMR 계산 로직 ---
def calculate_survivor_mmr(gen, unhook, heal, chase, stun, esc):
    score = 0
    if gen >= 300: score += 4
    elif gen >= 200: score += 2
    elif gen >= 150: score += 0
    else: score -= 4
    if unhook >= 4: score += 4
    elif unhook == 3: score += 2
    elif unhook == 2: score += 1
    elif unhook == 1: score += 0
    else: score -= 4
    if heal >= 200: score += 4
    elif heal >= 150: score += 3
    elif heal >= 100: score += 2
    elif heal >= 50: score += 1
    if chase > 180: score += 8
    elif chase >= 120: score += 8
    elif chase >= 90: score += 4
    elif chase >= 60: score += 2
    elif chase >= 30: score += 0
    else: score -= 8
    if stun >= 4: score += 4
    elif stun == 3: score += 3
    elif stun == 2: score += 2
    elif stun == 1: score += 1
    if esc == "탈출구 (Gate)": score += 8
    elif esc == "개구 (Hatch)": score += 0
    else: score -= 8
    return score

def calculate_killer_mmr(gen_reg, chase, tunnel, kills, hatch, gens_left, esc_count):
    score = 0
    if gen_reg >= 150: score += 4
    elif gen_reg >= 100: score += 3
    elif gen_reg >= 75: score += 2
    elif gen_reg >= 50: score += 1
    if tunnel: score -= 8
    else:
        if chase <= 30: score += 8
        elif chase <= 60: score += 4
        elif chase <= 90: score += 2
        elif chase <= 120: score += 0
    kill_scores = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8}
    score += kill_scores.get(kills, 0)
    if hatch: score += 1
    if gens_left in [1, 2, 3, 4, 5]: score += gens_left
    escape_penalties = {0: 0, 1: -2, 2: -4, 3: -6, 4: -8}
    score += escape_penalties.get(esc_count, 0)
    return score

class DBDMMRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("데드바이데이라이트 MMR 누적 계산기")
        self.root.geometry("450x700")
        self.root.resizable(False, False)

        try:
            self.root.iconbitmap(resource_path('icon.ico'))
        except Exception:
            pass

        try:
            self.logo_img = tk.PhotoImage(file=resource_path('logo.png'))
            ttk.Label(root, image=self.logo_img).pack(pady=5)
        except Exception:
            ttk.Label(root, text="[ 데바데 로고 이미지 없음 ]").pack(pady=5)

        self.data = load_data()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=5, expand=True, fill='both')

        self.survivor_frame = ttk.Frame(self.notebook, width=400, height=570)
        self.killer_frame = ttk.Frame(self.notebook, width=400, height=570)
        self.notebook.add(self.survivor_frame, text="생존자 (Survivor)")
        self.notebook.add(self.killer_frame, text="살인마 (Killer)")

        self.setup_survivor_tab()
        self.setup_killer_tab()

    def setup_survivor_tab(self):
        self.s_gen = tk.DoubleVar(value=0)
        self.s_unhooks = tk.IntVar(value=0)
        self.s_heal = tk.DoubleVar(value=0)
        self.s_chase = tk.DoubleVar(value=0)
        self.s_stun = tk.IntVar(value=0)
        self.s_escape = tk.StringVar(value="희생/사망 (Sacrificed)")

        top_frame = ttk.Frame(self.survivor_frame)
        top_frame.pack(pady=10)

        self.create_input_row(top_frame, "발전기 수리 진행도 (%):", self.s_gen, 0)
        self.create_input_row(top_frame, "갈고리 구출 (회):", self.s_unhooks, 1)
        self.create_input_row(top_frame, "타인 치료 진행도 (%):", self.s_heal, 2)
        self.create_input_row(top_frame, "어그로/피추격 시간 (초):", self.s_chase, 3)
        self.create_input_row(top_frame, "살인마 기절/실명 (회):", self.s_stun, 4)
        
        ttk.Label(top_frame, text="최종 결과:").grid(row=5, column=0, padx=10, pady=8, sticky="e")
        escape_cb = ttk.Combobox(top_frame, textvariable=self.s_escape, values=["탈출구 (Gate)", "개구 (Hatch)", "희생/사망 (Sacrificed)"], state="readonly")
        escape_cb.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        bottom_frame = ttk.Frame(self.survivor_frame)
        bottom_frame.pack(fill='x', pady=5)

        ttk.Button(bottom_frame, text="이번 매치 점수 반영하기", command=self.calc_survivor).pack(pady=5)
        self.s_result_label = ttk.Label(bottom_frame, text="이번 매치 변동: 0점", font=("Helvetica", 12))
        self.s_result_label.pack(pady=5)
        self.s_total_label = ttk.Label(bottom_frame, text=f"총 누적 MMR: {self.data['survivor_mmr']}점", font=("Helvetica", 16, "bold"), foreground="blue")
        self.s_total_label.pack(pady=10)
        
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="입력 취소 (되돌리기)", command=lambda: self.undo_score('survivor')).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="누적 점수 초기화", command=lambda: self.reset_score('survivor')).pack(side="left", padx=5)

    def setup_killer_tab(self):
        self.k_gen = tk.DoubleVar(value=0)
        self.k_chase = tk.DoubleVar(value=0)
        self.k_tunneling = tk.BooleanVar(value=False)
        self.k_kills = tk.IntVar(value=0)
        self.k_hatch = tk.BooleanVar(value=False)
        self.k_gens = tk.IntVar(value=0)
        self.k_escapes = tk.IntVar(value=0)

        top_frame = ttk.Frame(self.killer_frame)
        top_frame.pack(pady=10)

        self.create_input_row(top_frame, "발전기 퇴행 진행도 (%):", self.k_gen, 0)
        self.create_input_row(top_frame, "평균 추격 성공 시간 (초):", self.k_chase, 1)
        ttk.Checkbutton(top_frame, text="180초 이상 한 명만 추격(터널링)", variable=self.k_tunneling).grid(row=2, column=0, columnspan=2, pady=5)
        self.create_input_row(top_frame, "희생/처형 생존자 (명):", self.k_kills, 3)
        ttk.Checkbutton(top_frame, text="마지막 생존자 개구 탈출", variable=self.k_hatch).grid(row=4, column=0, columnspan=2, pady=5)
        self.create_input_row(top_frame, "매치 종료시 남은 발전기 (개):", self.k_gens, 5)
        self.create_input_row(top_frame, "최종 탈출한 생존자 (명):", self.k_escapes, 6)

        bottom_frame = ttk.Frame(self.killer_frame)
        bottom_frame.pack(fill='x', pady=5)

        ttk.Button(bottom_frame, text="이번 매치 점수 반영하기", command=self.calc_killer).pack(pady=5)
        self.k_result_label = ttk.Label(bottom_frame, text="이번 매치 변동: 0점", font=("Helvetica", 12))
        self.k_result_label.pack(pady=5)
        self.k_total_label = ttk.Label(bottom_frame, text=f"총 누적 MMR: {self.data['killer_mmr']}점", font=("Helvetica", 16, "bold"), foreground="purple")
        self.k_total_label.pack(pady=10)

        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="입력 취소 (되돌리기)", command=lambda: self.undo_score('killer')).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="누적 점수 초기화", command=lambda: self.reset_score('killer')).pack(side="left", padx=5)

    def create_input_row(self, parent, text, variable, row):
        ttk.Label(parent, text=text).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        ttk.Entry(parent, textvariable=variable, width=15).grid(row=row, column=1, padx=10, pady=8, sticky="w")

    def calc_survivor(self):
        try:
            score = calculate_survivor_mmr(self.s_gen.get(), self.s_unhooks.get(), self.s_heal.get(), self.s_chase.get(), self.s_stun.get(), self.s_escape.get())
            self.data["prev_survivor_mmr"] = self.data["survivor_mmr"]
            self.data["survivor_mmr"] += score
            save_data(self.data)
            
            prefix = "+" if score > 0 else ""
            self.s_result_label.config(text=f"이번 매치 변동: {prefix}{score}점")
            self.s_total_label.config(text=f"총 누적 MMR: {self.data['survivor_mmr']}점")
            
            self.s_gen.set(0); self.s_unhooks.set(0); self.s_heal.set(0)
            self.s_chase.set(0); self.s_stun.set(0); self.s_escape.set("희생/사망 (Sacrificed)")
        except Exception:
            messagebox.showerror("입력 오류", "숫자를 올바르게 입력해주세요.")

    def calc_killer(self):
        try:
            score = calculate_killer_mmr(self.k_gen.get(), self.k_chase.get(), self.k_tunneling.get(), self.k_kills.get(), self.k_hatch.get(), self.k_gens.get(), self.k_escapes.get())
            self.data["prev_killer_mmr"] = self.data["killer_mmr"]
            self.data["killer_mmr"] += score
            save_data(self.data)
            
            prefix = "+" if score > 0 else ""
            self.k_result_label.config(text=f"이번 매치 변동: {prefix}{score}점")
            self.k_total_label.config(text=f"총 누적 MMR: {self.data['killer_mmr']}점")
            
            self.k_gen.set(0); self.k_chase.set(0); self.k_tunneling.set(False)
            self.k_kills.set(0); self.k_hatch.set(False); self.k_gens.set(0); self.k_escapes.set(0)
        except Exception:
            messagebox.showerror("입력 오류", "숫자를 올바르게 입력해주세요.")

    def undo_score(self, role):
        if role == 'survivor':
            self.data["survivor_mmr"] = self.data["prev_survivor_mmr"]
            self.s_total_label.config(text=f"총 누적 MMR: {self.data['survivor_mmr']}점")
        else:
            self.data["killer_mmr"] = self.data["prev_killer_mmr"]
            self.k_total_label.config(text=f"총 누적 MMR: {self.data['killer_mmr']}점")
        save_data(self.data)

    def reset_score(self, role):
        if messagebox.askyesno("초기화", f"{'생존자' if role == 'survivor' else '살인마'} 누적 점수를 0으로 초기화하시겠습니까?"):
            if role == 'survivor':
                self.data["prev_survivor_mmr"] = self.data["survivor_mmr"] 
                self.data["survivor_mmr"] = 0
                self.s_total_label.config(text=f"총 누적 MMR: 0점")
            else:
                self.data["prev_killer_mmr"] = self.data["killer_mmr"]
                self.data["killer_mmr"] = 0
                self.k_total_label.config(text=f"총 누적 MMR: 0점")
            save_data(self.data)

if __name__ == '__main__':
    root = tk.Tk()
    app = DBDMMRApp(root)
    root.mainloop()