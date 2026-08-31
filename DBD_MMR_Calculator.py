import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
import time
import mss
import cv2
import numpy as np
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_app_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

DATA_FILE = os.path.join(get_app_path(), "mmr_data.json")

def load_data():
    default_data = {
        "survivor_mmr": 0, "killer_mmr": 0, 
        "survivor_history": [], "killer_history": [],
        "ocr_top": 900, "ocr_left": 100, "ocr_width": 100, "ocr_height": 50,
        "popup_top": 200, "popup_left": 1400, "popup_width": 300, "popup_height": 150
    }
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

# --- 규칙 검증이 완료된 MMR 계산 로직 ---
def calculate_survivor_mmr(gen, unhook, heal, chase, stun, esc):
    score = 0
    
    # 1. 발전기 수리 진행도
    if gen >= 300: score += 4
    elif gen >= 200: score += 2
    elif gen >= 150: score += 0
    else: score -= 4
        
    # 2. 갈고리 구출
    if unhook >= 4: score += 4
    elif unhook == 3: score += 2
    elif unhook == 2: score += 1
    elif unhook == 1: score += 0
    else: score -= 4
        
    # 3. 타인 치료 진행도
    if heal >= 200: score += 4
    elif heal >= 150: score += 3
    elif heal >= 100: score += 2
    elif heal >= 50: score += 1
    else: score += 0
        
    # 4. 피추격 시간
    if chase >= 180: score += 8
    elif chase >= 120: score += 8
    elif chase >= 90: score += 4
    elif chase >= 60: score += 2
    elif chase >= 30: score += 0
    else: score -= 8
        
    # 5. 살인마 기절/실명
    if stun >= 4: score += 4
    elif stun == 3: score += 3
    elif stun == 2: score += 2
    elif stun == 1: score += 1
    else: score += 0
        
    # 6. 탈출 결과
    if esc == "탈출구 (Gate)": score += 8
    elif esc == "개구 (Hatch)": score += 0
    else: score -= 8
        
    return score

def calculate_killer_mmr(gen_reg, chase, tunnel, kills, hatch, gens_left, esc_count):
    score = 0
    
    # 1. 발전기 감퇴
    if gen_reg >= 150: score += 4
    elif gen_reg >= 100: score += 3
    elif gen_reg >= 75: score += 2
    elif gen_reg >= 50: score += 1
    else: score += 0
        
    # 2. 추격 시간 및 터널링
    if tunnel or chase >= 180:
        score -= 8
    else:
        if chase <= 30: score += 8
        elif chase <= 60: score += 4
        elif chase <= 90: score += 2
        elif chase <= 120: score += 0
        else: score += 0

    # 3. 생존자 희생/살해
    kill_scores = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8}
    score += kill_scores.get(kills, 0)
    
    # 4. 개구 탈출 허용
    if hatch: score += 1

    # 5. 매치 종료시 남은 발전기
    if gens_left in [1, 2, 3, 4, 5]: 
        score += gens_left
    else: 
        score += 0

    # 6. 탈출한 생존자 수 감점
    escape_penalties = {0: 0, 1: -2, 2: -4, 3: -6, 4: -8}
    score += escape_penalties.get(esc_count, 0)

    return score

class DBDMMRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("데드바이데이라이트 MMR 누적 계산기")
        self.root.geometry("480x820")
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
        self.ocr_running = False

        self.current_s_score = 0
        self.current_k_score = 0

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=5, expand=True, fill='both')

        self.survivor_frame = ttk.Frame(self.notebook, width=400, height=570)
        self.killer_frame = ttk.Frame(self.notebook, width=400, height=570)
        self.notebook.add(self.survivor_frame, text="생존자 (Survivor)")
        self.notebook.add(self.killer_frame, text="살인마 (Killer)")

        self.setup_survivor_tab()
        self.setup_killer_tab()
        self.setup_ocr_control_frame()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_survivor_tab(self):
        self.s_gen = tk.DoubleVar(value=0)
        self.s_unhooks = tk.IntVar(value=0)
        self.s_heal = tk.DoubleVar(value=0)
        self.s_chase = tk.DoubleVar(value=0)
        self.s_stun = tk.IntVar(value=0)
        self.s_escape = tk.StringVar(value="희생/사망 (Sacrificed)")

        for var in [self.s_gen, self.s_unhooks, self.s_heal, self.s_chase, self.s_stun, self.s_escape]:
            var.trace_add("write", lambda *args: self.update_survivor_preview())

        top_frame = ttk.Frame(self.survivor_frame)
        top_frame.pack(pady=10)

        self.create_input_row(top_frame, "발전기 수리 진행도 (%):", self.s_gen, 0)
        self.create_input_row(top_frame, "갈고리 구출 (회) [자동]:", self.s_unhooks, 1)
        self.create_input_row(top_frame, "타인 치료 진행도 (%):", self.s_heal, 2)
        self.create_input_row(top_frame, "어그로/피추격 시간 (초):", self.s_chase, 3)
        self.create_input_row(top_frame, "살인마 기절/실명 (회) [자동]:", self.s_stun, 4)
        
        ttk.Label(top_frame, text="최종 결과:").grid(row=5, column=0, padx=10, pady=8, sticky="e")
        escape_cb = ttk.Combobox(top_frame, textvariable=self.s_escape, values=["탈출구 (Gate)", "개구 (Hatch)", "희생/사망 (Sacrificed)"], state="readonly")
        escape_cb.grid(row=5, column=1, padx=10, pady=8, sticky="w")

        bottom_frame = ttk.Frame(self.survivor_frame)
        bottom_frame.pack(fill='x', pady=5)

        ttk.Button(bottom_frame, text="누적 점수 반영하기", command=self.apply_survivor_score).pack(pady=5)
        self.s_result_label = ttk.Label(bottom_frame, text="이번 매치 변동: 0점", font=("Helvetica", 12))
        self.s_result_label.pack(pady=5)
        self.s_total_label = ttk.Label(bottom_frame, text=f"총 누적 MMR: {self.data['survivor_mmr']}점", font=("Helvetica", 16, "bold"), foreground="blue")
        self.s_total_label.pack(pady=10)
        
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="입력 취소 (되돌리기)", command=lambda: self.undo_score('survivor')).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="누적 점수 초기화", command=lambda: self.reset_score('survivor')).pack(side="left", padx=5)

        self.update_survivor_preview()

    def setup_killer_tab(self):
        self.k_gen = tk.DoubleVar(value=0)
        self.k_chase = tk.DoubleVar(value=0)
        self.k_tunneling = tk.BooleanVar(value=False)
        self.k_kills = tk.IntVar(value=0)
        self.k_hatch = tk.BooleanVar(value=False)
        self.k_gens = tk.IntVar(value=0)
        self.k_escapes = tk.IntVar(value=0)

        for var in [self.k_gen, self.k_chase, self.k_tunneling, self.k_kills, self.k_hatch, self.k_gens, self.k_escapes]:
            var.trace_add("write", lambda *args: self.update_killer_preview())

        top_frame = ttk.Frame(self.killer_frame)
        top_frame.pack(pady=10)

        self.create_input_row(top_frame, "발전기 퇴행 진행도 (%):", self.k_gen, 0)
        self.create_input_row(top_frame, "평균 추격 성공 시간 (초):", self.k_chase, 1)
        ttk.Checkbutton(top_frame, text="180초 이상 한 명만 추격(터널링)", variable=self.k_tunneling).grid(row=2, column=0, columnspan=2, pady=5)
        self.create_input_row(top_frame, "희생/처형 생존자 (명):", self.k_kills, 3)
        ttk.Checkbutton(top_frame, text="마지막 생존자 개구 탈출", variable=self.k_hatch).grid(row=4, column=0, columnspan=2, pady=5)
        self.create_input_row(top_frame, "매치 종료시 남은 발전기 (개) [자동]:", self.k_gens, 5)
        self.create_input_row(top_frame, "최종 탈출한 생존자 (명):", self.k_escapes, 6)

        bottom_frame = ttk.Frame(self.killer_frame)
        bottom_frame.pack(fill='x', pady=5)

        ttk.Button(bottom_frame, text="누적 점수 반영하기", command=self.apply_killer_score).pack(pady=5)
        self.k_result_label = ttk.Label(bottom_frame, text="이번 매치 변동: 0점", font=("Helvetica", 12))
        self.k_result_label.pack(pady=5)
        self.k_total_label = ttk.Label(bottom_frame, text=f"총 누적 MMR: {self.data['killer_mmr']}점", font=("Helvetica", 16, "bold"), foreground="purple")
        self.k_total_label.pack(pady=10)

        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="입력 취소 (되돌리기)", command=lambda: self.undo_score('killer')).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="누적 점수 초기화", command=lambda: self.reset_score('killer')).pack(side="left", padx=5)

        self.update_killer_preview()

    def update_survivor_preview(self):
        try:
            gen = self.s_gen.get()
            unhook = self.s_unhooks.get()
            heal = self.s_heal.get()
            chase = self.s_chase.get()
            stun = self.s_stun.get()
            escape = self.s_escape.get()

            # 수치 입력이 모두 0인 완전한 초기화 상태 검사
            if gen == 0 and unhook == 0 and heal == 0 and chase == 0 and stun == 0:
                self.current_s_score = 0
                self.s_result_label.config(text="이번 매치 변동: 0점")
                return

            score = calculate_survivor_mmr(gen, unhook, heal, chase, stun, escape)
            self.current_s_score = score
            prefix = "+" if score > 0 else ""
            self.s_result_label.config(text=f"이번 매치 변동: {prefix}{score}점")
        except Exception:
            pass

    def update_killer_preview(self):
        try:
            gen_reg = self.k_gen.get()
            chase = self.k_chase.get()
            tunnel = self.k_tunneling.get()
            kills = self.k_kills.get()
            hatch = self.k_hatch.get()
            gens = self.k_gens.get()
            escapes = self.k_escapes.get()

            # 수치 입력이 모두 0인 완전한 초기화 상태 검사
            if gen_reg == 0 and chase == 0 and not tunnel and kills == 0 and not hatch and gens == 0 and escapes == 0:
                self.current_k_score = 0
                self.k_result_label.config(text="이번 매치 변동: 0점")
                return

            score = calculate_killer_mmr(gen_reg, chase, tunnel, kills, hatch, gens, escapes)
            self.current_k_score = score
            prefix = "+" if score > 0 else ""
            self.k_result_label.config(text=f"이번 매치 변동: {prefix}{score}점")
        except Exception:
            pass

    def apply_survivor_score(self):
        self.data["survivor_history"].append(self.data["survivor_mmr"])
        if len(self.data["survivor_history"]) > 10:
            self.data["survivor_history"].pop(0)

        self.data["survivor_mmr"] += self.current_s_score
        save_data(self.data)

        self.s_total_label.config(text=f"총 누적 MMR: {self.data['survivor_mmr']}점")
        self.s_gen.set(0); self.s_unhooks.set(0); self.s_heal.set(0)
        self.s_chase.set(0); self.s_stun.set(0); self.s_escape.set("희생/사망 (Sacrificed)")

    def apply_killer_score(self):
        self.data["killer_history"].append(self.data["killer_mmr"])
        if len(self.data["killer_history"]) > 10:
            self.data["killer_history"].pop(0)

        self.data["killer_mmr"] += self.current_k_score
        save_data(self.data)

        self.k_total_label.config(text=f"총 누적 MMR: {self.data['killer_mmr']}점")
        self.k_gen.set(0); self.k_chase.set(0); self.k_tunneling.set(False)
        self.k_kills.set(0); self.k_hatch.set(False); self.k_gens.set(0); self.k_escapes.set(0)

    def undo_score(self, role):
        history_key = f"{role}_history"
        mmr_key = f"{role}_mmr"

        if self.data[history_key]:
            prev_score = self.data[history_key].pop()
            self.data[mmr_key] = prev_score
            save_data(self.data)

            if role == 'survivor':
                self.s_total_label.config(text=f"총 누적 MMR: {self.data['survivor_mmr']}점")
            else:
                self.k_total_label.config(text=f"총 누적 MMR: {self.data['killer_mmr']}점")
        else:
            messagebox.showinfo("알림", "더 이상 되돌릴 이전 기록이 없습니다.")

    def reset_score(self, role):
        if messagebox.askyesno("초기화", f"{'생존자' if role == 'survivor' else '살인마'} 누적 점수를 0으로 초기화하시겠습니까?"):
            history_key = f"{role}_history"
            mmr_key = f"{role}_mmr"

            self.data[history_key].append(self.data[mmr_key])
            self.data[mmr_key] = 0
            save_data(self.data)

            if role == 'survivor':
                self.s_total_label.config(text=f"총 누적 MMR: 0점")
            else:
                self.k_total_label.config(text=f"총 누적 MMR: 0점")

    def setup_ocr_control_frame(self):
        ocr_frame = ttk.LabelFrame(self.root, text=" 🤖 실시간 인게임 자동 감지 ")
        ocr_frame.pack(fill="x", padx=10, pady=5)

        self.ocr_top_var = tk.IntVar(value=self.data.get("ocr_top", 900))
        self.ocr_left_var = tk.IntVar(value=self.data.get("ocr_left", 100))
        self.ocr_width_var = tk.IntVar(value=self.data.get("ocr_width", 100))
        self.ocr_height_var = tk.IntVar(value=self.data.get("ocr_height", 50))

        pos_frame = ttk.Frame(ocr_frame)
        pos_frame.pack(pady=2)

        ttk.Label(pos_frame, text="발전기 영역 - Top:").grid(row=0, column=0, padx=1)
        ttk.Entry(pos_frame, textvariable=self.ocr_top_var, width=4).grid(row=0, column=1, padx=1)
        ttk.Label(pos_frame, text="Left:").grid(row=0, column=2, padx=1)
        ttk.Entry(pos_frame, textvariable=self.ocr_left_var, width=4).grid(row=0, column=3, padx=1)
        ttk.Label(pos_frame, text="W:").grid(row=0, column=4, padx=1)
        ttk.Entry(pos_frame, textvariable=self.ocr_width_var, width=4).grid(row=0, column=5, padx=1)
        ttk.Label(pos_frame, text="H:").grid(row=0, column=6, padx=1)
        ttk.Entry(pos_frame, textvariable=self.ocr_height_var, width=4).grid(row=0, column=7, padx=1)

        self.popup_top_var = tk.IntVar(value=self.data.get("popup_top", 200))
        self.popup_left_var = tk.IntVar(value=self.data.get("popup_left", 1400))
        self.popup_width_var = tk.IntVar(value=self.data.get("popup_width", 300))
        self.popup_height_var = tk.IntVar(value=self.data.get("popup_height", 150))

        pop_frame = ttk.Frame(ocr_frame)
        pop_frame.pack(pady=2)

        ttk.Label(pop_frame, text="팝업 영역 - Top:").grid(row=0, column=0, padx=1)
        ttk.Entry(pop_frame, textvariable=self.popup_top_var, width=4).grid(row=0, column=1, padx=1)
        ttk.Label(pop_frame, text="Left:").grid(row=0, column=2, padx=1)
        ttk.Entry(pop_frame, textvariable=self.popup_left_var, width=4).grid(row=0, column=3, padx=1)
        ttk.Label(pop_frame, text="W:").grid(row=0, column=4, padx=1)
        ttk.Entry(pop_frame, textvariable=self.popup_width_var, width=4).grid(row=0, column=5, padx=1)
        ttk.Label(pop_frame, text="H:").grid(row=0, column=6, padx=1)
        ttk.Entry(pop_frame, textvariable=self.popup_height_var, width=4).grid(row=0, column=7, padx=1)

        btn_container = ttk.Frame(ocr_frame)
        btn_container.pack(pady=5)

        self.ocr_toggle_btn = ttk.Button(btn_container, text="실시간 감지 시작", command=self.toggle_ocr)
        self.ocr_toggle_btn.pack(side="left", padx=5)

        self.ocr_status_label = ttk.Label(btn_container, text="상태: 꺼짐", foreground="gray")
        self.ocr_status_label.pack(side="left", padx=5)

    def toggle_ocr(self):
        if not self.ocr_running:
            self.data["ocr_top"] = self.ocr_top_var.get()
            self.data["ocr_left"] = self.ocr_left_var.get()
            self.data["ocr_width"] = self.ocr_width_var.get()
            self.data["ocr_height"] = self.ocr_height_var.get()

            self.data["popup_top"] = self.popup_top_var.get()
            self.data["popup_left"] = self.popup_left_var.get()
            self.data["popup_width"] = self.popup_width_var.get()
            self.data["popup_height"] = self.popup_height_var.get()
            save_data(self.data)

            self.ocr_running = True
            self.ocr_toggle_btn.config(text="자동 감지 중지")
            self.ocr_status_label.config(text="상태: 감지 중...", foreground="green")

            threading.Thread(target=self.ocr_loop, daemon=True).start()
        else:
            self.ocr_running = False
            self.ocr_toggle_btn.config(text="실시간 감지 시작")
            self.ocr_status_label.config(text="상태: 꺼짐", foreground="gray")

    def ocr_loop(self):
        num_config = r'--psm 7 -c tessedit_char_whitelist=012345'
        kor_config = r'--psm 6 -l kor'
        
        last_gen = None
        last_popup_time = 0

        with mss.MSS() as sct:
            while self.ocr_running:
                try:
                    now = time.time()

                    gen_monitor = {
                        "top": self.ocr_top_var.get(),
                        "left": self.ocr_left_var.get(),
                        "width": self.ocr_width_var.get(),
                        "height": self.ocr_height_var.get()
                    }
                    gen_img = np.array(sct.grab(gen_monitor))
                    gen_gray = cv2.cvtColor(gen_img, cv2.COLOR_BGRA2GRAY)
                    gen_text = pytesseract.image_to_string(gen_gray, config=num_config).strip()

                    if gen_text in ['0', '1', '2', '3', '4', '5']:
                        val = int(gen_text)
                        if val != last_gen:
                            last_gen = val
                            self.root.after(0, lambda v=val: self.k_gens.set(v))

                    if now - last_popup_time > 3.5:
                        pop_monitor = {
                            "top": self.popup_top_var.get(),
                            "left": self.popup_left_var.get(),
                            "width": self.popup_width_var.get(),
                            "height": self.popup_height_var.get()
                        }
                        pop_img = np.array(sct.grab(pop_monitor))
                        pop_gray = cv2.cvtColor(pop_img, cv2.COLOR_BGRA2GRAY)
                        pop_text = pytesseract.image_to_string(pop_gray, config=kor_config).replace(" ", "")

                        if "기절" in pop_text or "실명" in pop_text:
                            self.root.after(0, lambda: self.s_stun.set(self.s_stun.get() + 1))
                            last_popup_time = now
                        elif "갈고리구출" in pop_text:
                            self.root.after(0, lambda: self.s_unhooks.set(self.s_unhooks.get() + 1))
                            last_popup_time = now

                except Exception as e:
                    print("OCR 감지 오류:", e)
                
                time.sleep(0.1)

    def create_input_row(self, parent, text, variable, row):
        ttk.Label(parent, text=text).grid(row=row, column=0, padx=10, pady=8, sticky="e")
        ttk.Entry(parent, textvariable=variable, width=15).grid(row=row, column=1, padx=10, pady=8, sticky="w")

    def on_closing(self):
        self.ocr_running = False
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = DBDMMRApp(root)
    root.mainloop()