import tkinter as tk
from tkinter import ttk, messagebox

def calculate_survivor_mmr(gen_progress, unhooks, heal_progress, chase_time_sec, stun_blind_count, escape_type):
    score = 0
    # 1. 발전기 수리 진행도
    if gen_progress >= 300: score += 4
    elif gen_progress >= 200: score += 2
    elif gen_progress >= 150: score += 0
    else: score -= 4
        
    # 2. 갈고리 구출
    if unhooks >= 4: score += 4
    elif unhooks == 3: score += 2
    elif unhooks == 2: score += 1
    elif unhooks == 1: score += 0
    else: score -= 4
        
    # 3. 타인 치료
    if heal_progress >= 200: score += 4
    elif heal_progress >= 150: score += 3
    elif heal_progress >= 100: score += 2
    elif heal_progress >= 50: score += 1
    else: score += 0
        
    # 4. 피추격 시간
    if chase_time_sec > 180: score += 8  # 터널링 피해자 판정
    elif chase_time_sec >= 120: score += 8
    elif chase_time_sec >= 90: score += 4
    elif chase_time_sec >= 60: score += 2
    elif chase_time_sec >= 30: score += 0
    else: score -= 8
        
    # 5. 기절 / 실명
    if stun_blind_count >= 4: score += 4
    elif stun_blind_count == 3: score += 3
    elif stun_blind_count == 2: score += 2
    elif stun_blind_count == 1: score += 1
    else: score += 0
        
    # 6. 탈출 여부
    if escape_type == "탈출구 (Gate)": score += 8
    elif escape_type == "개구 (Hatch)": score += 0
    else: score -= 8 # 희생 (Sacrificed)
        
    return score

def calculate_killer_mmr(gen_regression, chase_time_sec, is_tunneling, kills, hatch_escape, remaining_gens, escaped_count):
    score = 0
    # 1. 발전기 손상(퇴행)
    if gen_regression >= 150: score += 4
    elif gen_regression >= 100: score += 3
    elif gen_regression >= 75: score += 2
    elif gen_regression >= 50: score += 1
    else: score += 0
        
    # 2. 추격 시간
    if is_tunneling:
        score -= 8
    else:
        if chase_time_sec <= 30: score += 8
        elif chase_time_sec <= 60: score += 4
        elif chase_time_sec <= 90: score += 2
        elif chase_time_sec <= 120: score += 0
        else: score += 0

    # 3. 희생 및 처형
    kill_scores = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8}
    score += kill_scores.get(kills, 0)
    
    if hatch_escape: score += 1

    # 4. 남은 발전기 수
    if remaining_gens in [1, 2, 3, 4, 5]:
        score += remaining_gens
    else:
        score += 0

    # 5. 생존자 탈출 패널티
    escape_penalties = {0: 0, 1: -2, 2: -4, 3: -6, 4: -8}
    score += escape_penalties.get(escaped_count, 0)

    return score

class DBDMMRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("데드바이데이라이트 MMR 계산기")
        self.root.geometry("450x550")
        self.root.resizable(False, False)

        # 탭 생성
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True)

        self.survivor_frame = ttk.Frame(self.notebook, width=400, height=500)
        self.killer_frame = ttk.Frame(self.notebook, width=400, height=500)
        
        self.survivor_frame.pack(fill='both', expand=True)
        self.killer_frame.pack(fill='both', expand=True)

        self.notebook.add(self.survivor_frame, text="생존자 (Survivor)")
        self.notebook.add(self.killer_frame, text="살인마 (Killer)")

        self.setup_survivor_tab()
        self.setup_killer_tab()

    def setup_survivor_tab(self):
        # 변수
        self.s_gen = tk.DoubleVar(value=0)
        self.s_unhooks = tk.IntVar(value=0)
        self.s_heal = tk.DoubleVar(value=0)
        self.s_chase = tk.DoubleVar(value=0)
        self.s_stun = tk.IntVar(value=0)
        self.s_escape = tk.StringVar(value="희생/사망 (Sacrificed)")

        # 레이아웃
        self.create_input_row(self.survivor_frame, "발전기 수리 진행도 (%):", self.s_gen, 0)
        self.create_input_row(self.survivor_frame, "갈고리 구출 (회):", self.s_unhooks, 1)
        self.create_input_row(self.survivor_frame, "타인 치료 진행도 (%):", self.s_heal, 2)
        self.create_input_row(self.survivor_frame, "어그로/피추격 시간 (초):", self.s_chase, 3)
        self.create_input_row(self.survivor_frame, "살인마 기절/실명 (회):", self.s_stun, 4)

        ttk.Label(self.survivor_frame, text="최종 결과:").grid(row=5, column=0, padx=15, pady=10, sticky="w")
        escape_cb = ttk.Combobox(self.survivor_frame, textvariable=self.s_escape, values=["탈출구 (Gate)", "개구 (Hatch)", "희생/사망 (Sacrificed)"], state="readonly")
        escape_cb.grid(row=5, column=1, padx=15, pady=10)

        calc_btn = ttk.Button(self.survivor_frame, text="생존자 점수 계산하기", command=self.calc_survivor)
        calc_btn.grid(row=6, column=0, columnspan=2, pady=20)

        self.s_result_label = ttk.Label(self.survivor_frame, text="MMR 변동: 0점", font=("Helvetica", 16, "bold"))
        self.s_result_label.grid(row=7, column=0, columnspan=2, pady=10)

    def setup_killer_tab(self):
        # 변수
        self.k_gen = tk.DoubleVar(value=0)
        self.k_chase = tk.DoubleVar(value=0)
        self.k_tunneling = tk.BooleanVar(value=False)
        self.k_kills = tk.IntVar(value=0)
        self.k_hatch = tk.BooleanVar(value=False)
        self.k_gens = tk.IntVar(value=0)
        self.k_escapes = tk.IntVar(value=0)

        # 레이아웃
        self.create_input_row(self.killer_frame, "발전기 퇴행 진행도 (%):", self.k_gen, 0)
        self.create_input_row(self.killer_frame, "평균 추격 성공 시간 (초):", self.k_chase, 1)
        
        ttk.Checkbutton(self.killer_frame, text="180초 이상 한 명만 추격(터널링)", variable=self.k_tunneling).grid(row=2, column=0, columnspan=2, pady=5)
        
        self.create_input_row(self.killer_frame, "희생/처형 생존자 (명):", self.k_kills, 3)
        
        ttk.Checkbutton(self.killer_frame, text="마지막 생존자 개구 탈출", variable=self.k_hatch).grid(row=4, column=0, columnspan=2, pady=5)
        
        self.create_input_row(self.killer_frame, "매치 종료시 남은 발전기 (개):", self.k_gens, 5)
        self.create_input_row(self.killer_frame, "최종 탈출한 생존자 (명):", self.k_escapes, 6)

        calc_btn = ttk.Button(self.killer_frame, text="살인마 점수 계산하기", command=self.calc_killer)
        calc_btn.grid(row=7, column=0, columnspan=2, pady=20)

        self.k_result_label = ttk.Label(self.killer_frame, text="MMR 변동: 0점", font=("Helvetica", 16, "bold"))
        self.k_result_label.grid(row=8, column=0, columnspan=2, pady=10)

    def create_input_row(self, parent, text, variable, row):
        ttk.Label(parent, text=text).grid(row=row, column=0, padx=15, pady=10, sticky="w")
        ttk.Entry(parent, textvariable=variable, width=15).grid(row=row, column=1, padx=15, pady=10)

    def calc_survivor(self):
        try:
            score = calculate_survivor_mmr(
                self.s_gen.get(), self.s_unhooks.get(), self.s_heal.get(), 
                self.s_chase.get(), self.s_stun.get(), self.s_escape.get()
            )
            color = "green" if score > 0 else "red" if score < 0 else "black"
            prefix = "+" if score > 0 else ""
            self.s_result_label.config(text=f"MMR 변동: {prefix}{score}점", foreground=color)
        except Exception as e:
            messagebox.showerror("입력 오류", "숫자를 올바르게 입력해주세요.")

    def calc_killer(self):
        try:
            score = calculate_killer_mmr(
                self.k_gen.get(), self.k_chase.get(), self.k_tunneling.get(), 
                self.k_kills.get(), self.k_hatch.get(), self.k_gens.get(), self.k_escapes.get()
            )
            color = "green" if score > 0 else "red" if score < 0 else "black"
            prefix = "+" if score > 0 else ""
            self.k_result_label.config(text=f"MMR 변동: {prefix}{score}점", foreground=color)
        except Exception as e:
            messagebox.showerror("입력 오류", "숫자를 올바르게 입력해주세요.")

if __name__ == '__main__':
    root = tk.Tk()
    app = DBDMMRApp(root)
    root.mainloop()
