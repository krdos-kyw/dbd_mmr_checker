import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

# --- 데이터 저장 파일 경로 ---
DATA_FILE = "mmr_data.json"

# --- 데이터 로드 및 저장 함수 ---
def load_data():
    default_data = {
        "survivor_mmr": 0, 
        "killer_mmr": 0,
        "prev_survivor_mmr": 0,
        "prev_killer_mmr": 0
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # 이전 버전 데이터 호환을 위해 키가 없으면 기본값 추가
                for key in default_data:
                    if key not in loaded:
                        loaded[key] = default_data[key]
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
def calculate_survivor_mmr(gen_progress, unhooks, heal_progress, chase_time_sec, stun_blind_count, escape_type):
    score = 0
    if gen_progress >= 300: score += 4
    elif gen_progress >= 200: score += 2
    elif gen_progress >= 150: score += 0
    else: score -= 4
        
    if unhooks >= 4: score += 4
    elif unhooks == 3: score += 2
    elif unhooks == 2: score += 1
    elif unhooks == 1: score += 0
    else: score -= 4
        
    if heal_progress >= 200: score += 4
    elif heal_progress >= 150: score += 3
    elif heal_progress >= 100: score += 2
    elif heal_progress >= 50: score += 1
    else: score += 0
        
    if chase_time_sec > 180: score += 8
    elif chase_time_sec >= 120: score += 8
    elif chase_time_sec >= 90: score += 4
    elif chase_time_sec >= 60: score += 2
    elif chase_time_sec >= 30: score += 0
    else: score -= 8
        
    if stun_blind_count >= 4: score += 4
    elif stun_blind_count == 3: score += 3
    elif stun_blind_count == 2: score += 2
    elif stun_blind_count == 1: score += 1
    else: score += 0
        
    if escape_type == "탈출구 (Gate)": score += 8
    elif escape_type == "개구 (Hatch)": score += 0
    else: score -= 8
        
    return score

def calculate_killer_mmr(gen_regression, chase_time_sec, is_tunneling, kills, hatch_escape, remaining_gens, escaped_count):
    score = 0
    if gen_regression >= 150: score += 4
    elif gen_regression >= 100: score += 3
    elif gen_regression >= 75: score += 2
    elif gen_regression >= 50: score += 1
    else: score += 0
        
    if is_tunneling: score -= 8
    else:
        if chase_time_sec <= 30: score += 8
        elif chase_time_sec <= 60: score += 4
        elif chase_time_sec <= 90: score += 2
        elif chase_time_sec <= 120: score += 0
        else: score += 0

    kill_scores = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8}
    score += kill_scores.get(kills, 0)
    if hatch_escape: score += 1

    if remaining_gens in [1, 2, 3, 4, 5]: score += remaining_gens
    else: score += 0

    escape_penalties = {0: 0, 1: -2, 2: -4, 3: -6, 4: -8}
    score += escape_penalties.get(escaped_count, 0)

    return score

# --- GUI 애플리케이션 ---
class DBDMMRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("데드바이데이라이트 MMR 누적 계산기")
        self.root.geometry("450x620")
        self.root.resizable(False, False)

        self.data = load_data()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True, fill='both')

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

        self.create_input_row(self.survivor_frame, "발전기 수리 진행도 (%):", self.s_gen, 0)
        self.create_input_row(self.survivor_frame, "갈고리 구출 (회):", self.s_unhooks, 1)
        self.create_input_row(self.survivor_frame, "타인 치료 진행도 (%):", self.s_heal, 2)
        self.create_input_row(self.survivor_frame, "어그로/피추격 시간 (초):", self.s_chase, 3)
        self.create_input_row(self.survivor_frame, "살인마 기절/실명 (회):", self.s_stun, 4)

        ttk.Label(self.survivor_frame, text="최종 결과:").grid(row=5, column=0, padx=15, pady=10, sticky="w")
        escape_cb = ttk.Combobox(self.survivor_frame, textvariable=self.s_escape, values=["탈출구 (Gate)", "개구 (Hatch)", "희생/사망 (Sacrificed)"], state="readonly")
        escape_cb.grid(row=5, column=1, padx=15, pady=10)

        calc_btn = ttk.Button(self.survivor_frame, text="이번 매치 점수 반영하기", command=self.calc_survivor)
        calc_btn.grid(row=6, column=0, columnspan=2, pady=10)

        self.s_result_label = ttk.Label(self.survivor_frame, text="이번 매치 변동: 0점", font=("Helvetica", 12))
        self.s_result_label.grid(row=7, column=0, columnspan=2, pady=5)

        self.s_total_label = ttk.Label(self.survivor_frame, text=f"총 누적 MMR: {self.data['survivor_mmr']}점", font=("Helvetica", 16, "bold"), foreground="blue")
        self.s_total_label.grid(row=8, column=0, columnspan=2, pady=10)
        
        btn_frame = ttk.Frame(self.survivor_frame)
        btn_frame.grid(row=9, column=0, columnspan=2, pady=5)

        undo_btn = ttk.Button(btn_frame, text="입력 취소 (되돌리기)", command=lambda: self.undo_score('survivor'))
        undo_btn.pack(side="left", padx=5)

        reset_btn = ttk.Button(btn_frame, text="누적 점수 초기화", command=lambda: self.reset_score('survivor'))
        reset_btn.pack(side="left", padx=5)

    def setup_killer_tab(self):
        self.k_gen = tk.DoubleVar(value=0)
        self.k_chase = tk.DoubleVar(value=0)
        self.k_tunneling = tk.BooleanVar(value=False)
        self.k_kills = tk.IntVar(value=0)
        self.k_hatch = tk.BooleanVar(value=False)
        self.k_gens = tk.IntVar(value=0)
        self.k_escapes = tk.IntVar(value=0)

        self.create_input_row(self.killer_frame, "발전기 퇴행 진행도 (%):", self.k_gen, 0)
        self.create_input_row(self.killer_frame, "평균 추격 성공 시간 (초):", self.k_chase, 1)
        ttk.Checkbutton(self.killer_frame, text="180초 이상 한 명만 추격(터널링)", variable=self.k_tunneling).grid(row=2, column=0, columnspan=2, pady=5)
        self.create_input_row(self.killer_frame, "희생/처형 생존자 (명):", self.k_kills, 3)
        ttk.Checkbutton(self.killer_frame, text="마지막 생존자 개구 탈출", variable=self.k_hatch).grid(row=4, column=0, columnspan=2, pady=5)
        self.create_input_row(self.killer_frame, "매치 종료시 남은 발전기 (개):", self.k_gens, 5)
        self.create_input_row(self.killer_frame, "최종 탈출한 생존자 (명):", self.k_escapes, 6)

        calc_btn = ttk.Button(self.killer_frame, text="이번 매치 점수 반영하기", command=self.calc_killer)
        calc_btn.grid(row=7, column=0, columnspan=2, pady=10)

        self.k_result_label = ttk.Label(self.killer_frame, text="이번 매치 변동: 0점", font=("Helvetica", 12))
        self.k_result_label.grid(row=8, column=0, columnspan=2, pady=5)

        self.k_total_label = ttk.Label(self.killer_frame, text=f"총 누적 MMR: {self.data['killer_mmr']}점", font=("Helvetica", 16, "bold"), foreground="purple")
        self.k_total_label.grid(row=9, column=0, columnspan=2, pady=10)

        btn_frame = ttk.Frame(self.killer_frame)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=5)

        undo_btn = ttk.Button(btn_frame, text="입력 취소 (되돌리기)", command=lambda: self.undo_score('killer'))
        undo_btn.pack(side="left", padx=5)

        reset_btn = ttk.Button(btn_frame, text="누적 점수 초기화", command=lambda: self.reset_score('killer'))
        reset_btn.pack(side="left", padx=5)

    def create_input_row(self, parent, text, variable, row):
        ttk.Label(parent, text=text).grid(row=row, column=0, padx=15, pady=10, sticky="w")
        ttk.Entry(parent, textvariable=variable, width=15).grid(row=row, column=1, padx=15, pady=10)

    def calc_survivor(self):
        try:
            score = calculate_survivor_mmr(
                self.s_gen.get(), self.s_unhooks.get(), self.s_heal.get(), 
                self.s_chase.get(), self.s_stun.get(), self.s_escape.get()
            )
            # 현재 점수를 이전 점수로 백업
            self.data["prev_survivor_mmr"] = self.data["survivor_mmr"]
            
            self.data["survivor_mmr"] += score
            save_data(self.data)
            
            prefix = "+" if score > 0 else ""
            self.s_result_label.config(text=f"이번 매치 변동: {prefix}{score}점")
            self.s_total_label.config(text=f"총 누적 MMR: {self.data['survivor_mmr']}점")
        except Exception:
            messagebox.showerror("입력 오류", "숫자를 올바르게 입력해주세요.")

    def calc_killer(self):
        try:
            score = calculate_killer_mmr(
                self.k_gen.get(), self.k_chase.get(), self.k_tunneling.get(), 
                self.k_kills.get(), self.k_hatch.get(), self.k_gens.get(), self.k_escapes.get()
            )
            # 현재 점수를 이전 점수로 백업
            self.data["prev_killer_mmr"] = self.data["killer_mmr"]
            
            self.data["killer_mmr"] += score
            save_data(self.data)
            
            prefix = "+" if score > 0 else ""
            self.k_result_label.config(text=f"이번 매치 변동: {prefix}{score}점")
            self.k_total_label.config(text=f"총 누적 MMR: {self.data['killer_mmr']}점")
        except Exception:
            messagebox.showerror("입력 오류", "숫자를 올바르게 입력해주세요.")

    def undo_score(self, role):
        if role == 'survivor':
            # 백업된 점수로 복구
            self.data["survivor_mmr"] = self.data["prev_survivor_mmr"]
            self.s_total_label.config(text=f"총 누적 MMR: {self.data['survivor_mmr']}점")
            self.s_result_label.config(text="되돌리기 완료")
        else:
            self.data["killer_mmr"] = self.data["prev_killer_mmr"]
            self.k_total_label.config(text=f"총 누적 MMR: {self.data['killer_mmr']}점")
            self.k_result_label.config(text="되돌리기 완료")
        save_data(self.data)

    def reset_score(self, role):
        if messagebox.askyesno("초기화", f"{'생존자' if role == 'survivor' else '살인마'} 누적 점수를 0으로 초기화하시겠습니까?"):
            if role == 'survivor':
                self.data["prev_survivor_mmr"] = self.data["survivor_mmr"] # 초기화도 되돌리기 가능하도록 백업
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