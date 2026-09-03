import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
import time
import ctypes
from PIL import Image, ImageTk
import mss
import cv2
import numpy as np
import pytesseract
import keyboard  # 스톱워치 단축키 감지용

try:
    myappid = 'dbd.mmr.calculator.app.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    #윈도우 배율 변경으로 인한 창 크기 수축 방지
    ctypes.windll.user32.SetProcessDPIAware()

except Exception:
    pass

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
        "ocr_top": 796, "ocr_left": 157, "ocr_width": 132, "ocr_height": 68,
        "popup_top": 98, "popup_left": 1683, "popup_width": 194, "popup_height": 209
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

def calculate_survivor_mmr(gen, unhook, heal, chase, is_tunneled, stun, esc):
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
    else: score += 0
        
    if is_tunneled:
        score += 8
    else:
        if chase >= 120: score += 8
        elif chase >= 90: score += 4
        elif chase >= 60: score += 2
        elif chase >= 30: score += 0
        else: score -= 8
        
    if stun >= 4: score += 4
    elif stun == 3: score += 3
    elif stun == 2: score += 2
    elif stun == 1: score += 1
    else: score += 0
        
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
    else: score += 0
        
    if tunnel or chase >= 180:
        score -= 8
    else:
        if chase <= 30: score += 8
        elif chase <= 60: score += 4
        elif chase <= 90: score += 2
        elif chase <= 120: score += 0
        else: score += 0

    kill_scores = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8}
    score += kill_scores.get(kills, 0)
    
    if hatch: score += 1

    if gens_left in [1, 2, 3, 4, 5]: score += gens_left
    else: score += 0

    escape_penalties = {0: 0, 1: -2, 2: -4, 3: -6, 4: -8}
    score += escape_penalties.get(esc_count, 0)

    return score

class DBDMMRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("데드바이데이라이트 MMR 누적 계산기")
        # 💡 740을 680으로 줄여서 하단 여백 제거
        self.root.geometry("480x800") 
        self.root.resizable(False, False)

        try:
            icon_path = resource_path('icon.ico')
            self.app_icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, self.app_icon)
        except Exception:
            try:
                self.root.iconbitmap(resource_path('icon.ico'))
            except Exception:
                pass

        try:
            self.logo_img = tk.PhotoImage(file=resource_path('logo.png'))
            ttk.Label(root, image=self.logo_img).pack(pady=3)
        except Exception:
            ttk.Label(root, text="[ 데바데 로고 이미지 없음 ]").pack(pady=3)

        self.data = load_data()
        self.ocr_running = False

        self.is_chasing = False
        self.chase_start_time = 0.0
        self.hotkey_enabled = tk.BooleanVar(value=False)
        
        self.current_hotkey = self.data.get("chase_hotkey", "3")
        try:
            keyboard.on_press_key(self.current_hotkey, lambda e: self.toggle_chase_timer())
        except Exception:
            pass

        self.current_s_score = 0
        self.current_k_score = 0

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=1, fill='both')

        self.survivor_frame = ttk.Frame(self.notebook)
        self.killer_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.survivor_frame, text="생존자 (Survivor)")
        self.notebook.add(self.killer_frame, text="살인마 (Killer)")

        self.setup_survivor_tab()
        self.setup_killer_tab()
        
        # 💡 위치 변경: 탭 가이드 바로 아래에 단축키 설정 UI 배치
        self.setup_hotkey_frame()
        self.setup_ocr_control_frame()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_hotkey_frame(self):
        # 💡 프레임 이름 변경
        hk_frame = ttk.LabelFrame(self.root, text=" ⏱️ 추격/어그로 측정 스톱워치 ")
        hk_frame.pack(fill="x", padx=10, pady=2)
        
        self.chase_hotkey_var = tk.StringVar(value=self.current_hotkey)
        
        top_row = ttk.Frame(hk_frame)
        top_row.pack(pady=2)
        
        self.hk_btn = ttk.Button(top_row, text=f"현재 단축키: [ {self.current_hotkey} ]", command=self.open_hotkey_popup)
        self.hk_btn.pack(side="left", padx=5, pady=2)
        
        ttk.Checkbutton(top_row, text="인게임 단축키 활성화", variable=self.hotkey_enabled).pack(side="left", padx=5)

        bottom_row = ttk.Frame(hk_frame)
        bottom_row.pack(pady=2)
        
        self.chase_status_label = ttk.Label(bottom_row, text="상태: 대기 중", foreground="gray")
        self.chase_status_label.pack()

    def open_hotkey_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("단축키 입력")
        popup.geometry("250x100")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        popup.grab_set()
        popup.focus_force()
        
        ttk.Label(popup, text="적용할 키를 누르세요...", font=("맑은 고딕", 11)).pack(expand=True)
        
        def on_key_press(event):
            key = event.keysym.lower()
            if key in ('shift_l', 'shift_r', 'alt_l', 'alt_r', 'control_l', 'control_r'):
                return
                
            self.chase_hotkey_var.set(key)
            self.hk_btn.config(text=f"현재 단축키: [ {key} ]")
            popup.destroy()
            
            # 💡 창이 닫히자마자 자동으로 단축키 변경 로직 실행
            self.update_hotkey()
            
        popup.bind("<KeyPress>", on_key_press)

    def update_hotkey(self):
        new_key = self.chase_hotkey_var.get().strip().lower()
        if not new_key: return
        
        # 💡 기존 후킹 해제
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
            
        try:
            # 💡 단독 조합 제한이 있는 add_hotkey 대신, 다른 키와 조합되어도 반응하는 on_press_key 사용
            keyboard.on_press_key(new_key, lambda e: self.toggle_chase_timer())
            self.current_hotkey = new_key
            self.data["chase_hotkey"] = new_key
            save_data(self.data)
        except Exception as e:
            messagebox.showerror("오류", f"지원하지 않는 단축키입니다.\n{e}")

    def toggle_chase_timer(self):
        if not self.hotkey_enabled.get():
            return
            
        if not self.is_chasing:
            self.is_chasing = True
            self.chase_start_time = time.time()
            
            # 💡 현재 선택된 탭이 생존자(0)인지 살인마(1)인지 확인하여 메세지 분리
            current_tab = self.notebook.index(self.notebook.select())
            status_msg = "상태: 어그로 측정 중..." if current_tab == 0 else "상태: 추격 측정 중..."
            
            self.root.after(0, lambda: self.chase_status_label.config(text=status_msg, foreground="orange"))
        else:
            self.is_chasing = False
            duration = time.time() - self.chase_start_time
            self.root.after(0, lambda d=duration: self.apply_chase_time(d))

    def apply_chase_time(self, duration):
        # 💡 현재 열려있는 탭에 따라 각각 다른 변수에 시간을 더해줌
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 0:  # 생존자 탭
            current_val = self.s_chase.get()
            self.s_chase.set(round(current_val + duration))
        else:  # 살인마 탭
            current_val = self.k_chase.get()
            self.k_chase.set(round(current_val + duration))
        
        self.chase_status_label.config(text="상태: 대기 중", foreground="gray")

    def open_rule_popup(self):
        rule_win = tk.Toplevel(self.root)
        rule_win.title("MMR 점수 산출 상세 규칙표")
        rule_win.geometry("560x760")
        rule_win.resizable(True, True)
        rule_win.attributes("-topmost", True)

        try:
            rule_win.iconphoto(True, self.app_icon)
        except Exception:
            pass

        canvas = tk.Canvas(rule_win, bg="#141418", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        try:
            img_path = resource_path('rule_info.png')
            original_pil_img = Image.open(img_path)

            def resize_image(event):
                new_w, new_h = event.width, event.height
                if new_w < 10 or new_h < 10: return
                resized_pil = original_pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                rule_win.tk_img = ImageTk.PhotoImage(resized_pil)
                canvas.delete("all")
                canvas.create_image(0, 0, anchor="nw", image=rule_win.tk_img)

            canvas.bind("<Configure>", resize_image)
        except Exception as e:
            ttk.Label(rule_win, text=f"규칙 이미지를 불러올 수 없습니다.\n({e})", padding=20).pack()

        rule_win.bind("<Escape>", lambda e: rule_win.destroy())

    def setup_survivor_tab(self):
        self.s_gen = tk.DoubleVar(value=0)
        self.s_unhooks = tk.IntVar(value=0)
        self.s_heal = tk.DoubleVar(value=0)
        self.s_chase = tk.DoubleVar(value=0)
        self.s_tunneled = tk.BooleanVar(value=False)
        self.s_stun = tk.IntVar(value=0)
        self.s_escape = tk.StringVar(value="희생/사망 (Sacrificed)")

        for var in [self.s_gen, self.s_unhooks, self.s_heal, self.s_chase, self.s_tunneled, self.s_stun, self.s_escape]:
            var.trace_add("write", lambda *args: self.update_survivor_preview())

        top_frame = ttk.Frame(self.survivor_frame)
        top_frame.pack(pady=2)

        self.create_input_row(top_frame, "발전기 수리 진행도 (%) [수동]:", self.s_gen, 0)
        self.create_input_row(top_frame, "갈고리 구출 (회) [자동]:", self.s_unhooks, 1)
        self.create_input_row(top_frame, "타인 치료 진행도 (%) [수동]:", self.s_heal, 2)
        self.create_input_row(top_frame, "어그로/피추격 시간 (초) [수동]:", self.s_chase, 3)
        
        ttk.Checkbutton(top_frame, text="180초 이상 추격당함 (터널링 피해자)", variable=self.s_tunneled).grid(row=4, column=0, columnspan=2, pady=2)
        self.create_input_row(top_frame, "살인마 기절/실명 (회) [자동]:", self.s_stun, 5)
        
        ttk.Label(top_frame, text="최종 결과 [수동]:").grid(row=6, column=0, padx=10, pady=2, sticky="e")
        escape_cb = ttk.Combobox(top_frame, textvariable=self.s_escape, values=["탈출구 (Gate)", "개구 (Hatch)", "희생/사망 (Sacrificed)"], state="readonly")
        escape_cb.grid(row=6, column=1, padx=10, pady=2, sticky="w")

        bottom_frame = ttk.Frame(self.survivor_frame)
        bottom_frame.pack(fill='x', pady=1)

        ttk.Button(bottom_frame, text="누적 점수 반영하기", command=self.apply_survivor_score).pack(pady=2)
        self.s_result_label = ttk.Label(bottom_frame, text="이번 매치 변동: 0점", font=("맑은 고딕", 11))
        self.s_result_label.pack(pady=1)
        self.s_total_label = ttk.Label(bottom_frame, text=f"총 누적 MMR: {self.data['survivor_mmr']}점", font=("맑은 고딕", 14, "bold"), foreground="blue")
        self.s_total_label.pack(pady=2)
        
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(pady=1)
        ttk.Button(btn_frame, text="입력 취소 (되돌리기)", command=lambda: self.undo_score('survivor')).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="누적 점수 초기화", command=lambda: self.reset_score('survivor')).pack(side="left", padx=5)

        info_box = ttk.LabelFrame(self.survivor_frame, text=" 💡 생존자 MMR 핵심 가이드 ")
        info_box.pack(fill="x", padx=10, pady=2)

        summary_txt = "• 어그로 30초 미만(-8점) & 구출 0회(-4점) 감점 주의!\n• 발전기 150%+ / 어그로 60s+ / 구출 1회+ 목표 권장"
        ttk.Label(info_box, text=summary_txt, font=("맑은 고딕", 9), foreground="#333333", justify="left").pack(anchor="w", padx=6, pady=2)
        ttk.Button(info_box, text="📖 상세 규칙표 팝업 보기", command=self.open_rule_popup).pack(anchor="e", padx=6, pady=2)

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
        top_frame.pack(pady=2)

        self.create_input_row(top_frame, "발전기 퇴행 진행도 (%) [수동]:", self.k_gen, 0)
        self.create_input_row(top_frame, "평균 추격 성공 시간 (초) [수동]:", self.k_chase, 1)
        ttk.Checkbutton(top_frame, text="180초 이상 한 명만 추격(터널링)", variable=self.k_tunneling).grid(row=2, column=0, columnspan=2, pady=1)
        self.create_input_row(top_frame, "희생/처형 생존자 (명) [수동]:", self.k_kills, 3)
        ttk.Checkbutton(top_frame, text="마지막 생존자 개구 탈출", variable=self.k_hatch).grid(row=4, column=0, columnspan=2, pady=1)
        self.create_input_row(top_frame, "매치 종료시 남은 발전기 (개) [자동]:", self.k_gens, 5)
        self.create_input_row(top_frame, "최종 탈출한 생존자 (명) [수동]:", self.k_escapes, 6)

        bottom_frame = ttk.Frame(self.killer_frame)
        bottom_frame.pack(fill='x', pady=1)

        ttk.Button(bottom_frame, text="누적 점수 반영하기", command=self.apply_killer_score).pack(pady=2)
        self.k_result_label = ttk.Label(bottom_frame, text="이번 매치 변동: 0점", font=("맑은 고딕", 11))
        self.k_result_label.pack(pady=1)
        self.k_total_label = ttk.Label(bottom_frame, text=f"총 누적 MMR: {self.data['killer_mmr']}점", font=("맑은 고딕", 14, "bold"), foreground="purple")
        self.k_total_label.pack(pady=2)

        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(pady=1)
        ttk.Button(btn_frame, text="입력 취소 (되돌리기)", command=lambda: self.undo_score('killer')).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="누적 점수 초기화", command=lambda: self.reset_score('killer')).pack(side="left", padx=5)

        info_box = ttk.LabelFrame(self.killer_frame, text=" 💡 살인마 MMR 핵심 가이드 ")
        info_box.pack(fill="x", padx=10, pady=2)

        summary_txt = "• 빠른 추격 성공(30s 이하 +8점) & 터널링 지양(-8점)\n• 희생자 수(+2~8점) 및 남은 발전기 수(+1~5점) 가점 반영"
        ttk.Label(info_box, text=summary_txt, font=("맑은 고딕", 9), foreground="#333333", justify="left").pack(anchor="w", padx=6, pady=2)
        ttk.Button(info_box, text="📖 상세 규칙표 팝업 보기", command=self.open_rule_popup).pack(anchor="e", padx=6, pady=2)

        self.update_killer_preview()

    def update_survivor_preview(self):
        try:
            gen = self.s_gen.get()
            unhook = self.s_unhooks.get()
            heal = self.s_heal.get()
            chase = self.s_chase.get()
            tunneled = self.s_tunneled.get()
            stun = self.s_stun.get()
            escape = self.s_escape.get()

            if gen == 0 and unhook == 0 and heal == 0 and chase == 0 and not tunneled and stun == 0:
                self.current_s_score = 0
                self.s_result_label.config(text="이번 매치 변동: 0점")
                return

            score = calculate_survivor_mmr(gen, unhook, heal, chase, tunneled, stun, escape)
            self.current_s_score = score
            prefix = "+" if score > 0 else ""
            self.s_result_label.config(text=f"이번 매치 변동: {prefix}{score}점")
        except Exception as e:
            print("생존자 계산 에러:", e)

    def update_killer_preview(self):
        try:
            gen_reg = self.k_gen.get()
            chase = self.k_chase.get()
            tunnel = self.k_tunneling.get()
            kills = self.k_kills.get()
            hatch = self.k_hatch.get()
            gens = self.k_gens.get()
            escapes = self.k_escapes.get()

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
        self.s_chase.set(0); self.s_tunneled.set(False); self.s_stun.set(0); self.s_escape.set("희생/사망 (Sacrificed)")

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
        ocr_frame = ttk.LabelFrame(self.root, text=" 🤖 실시간 인게임 자동 감지 영역 설정 ")
        ocr_frame.pack(fill="x", padx=10, pady=2)

        self.ocr_top_var = tk.IntVar(value=self.data.get("ocr_top", 796))
        self.ocr_left_var = tk.IntVar(value=self.data.get("ocr_left", 157))
        self.ocr_width_var = tk.IntVar(value=self.data.get("ocr_width", 132))
        self.ocr_height_var = tk.IntVar(value=self.data.get("ocr_height", 68))

        self.popup_top_var = tk.IntVar(value=self.data.get("popup_top", 98))
        self.popup_left_var = tk.IntVar(value=self.data.get("popup_left", 1683))
        self.popup_width_var = tk.IntVar(value=self.data.get("popup_width", 194))
        self.popup_height_var = tk.IntVar(value=self.data.get("popup_height", 209))

        rows = [
            ("발전기 영역 (숫자)", self.ocr_top_var, self.ocr_left_var, self.ocr_width_var, self.ocr_height_var),
            ("팝업 영역 (이벤트)", self.popup_top_var, self.popup_left_var, self.popup_width_var, self.popup_height_var)
        ]

        for i, (label_txt, top, left, w, h) in enumerate(rows):
            f = ttk.Frame(ocr_frame)
            f.pack(pady=1)
            ttk.Label(f, text=f"{label_txt} - Top:").grid(row=0, column=0, padx=1)
            ttk.Entry(f, textvariable=top, width=4).grid(row=0, column=1, padx=1)
            ttk.Label(f, text="Left:").grid(row=0, column=2, padx=1)
            ttk.Entry(f, textvariable=left, width=4).grid(row=0, column=3, padx=1)
            ttk.Label(f, text="W:").grid(row=0, column=4, padx=1)
            ttk.Entry(f, textvariable=w, width=4).grid(row=0, column=5, padx=1)
            ttk.Label(f, text="H:").grid(row=0, column=6, padx=1)
            ttk.Entry(f, textvariable=h, width=4).grid(row=0, column=7, padx=1)

        btn_container = ttk.Frame(ocr_frame)
        btn_container.pack(pady=2)

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
        
        active_unhooks = 0
        unhook_missing = 0
        
        active_stuns = 0
        stun_missing = 0
        
        active_blinds = 0
        blind_missing = 0

        with mss.MSS() as sct:
            while self.ocr_running:
                try:
                    # 1. 살인마용 남은 발전기 개수 감지
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

                    # 2. 중앙 우측 팝업 감지
                    pop_monitor = {
                        "top": self.popup_top_var.get(),
                        "left": self.popup_left_var.get(),
                        "width": self.popup_width_var.get(),
                        "height": self.popup_height_var.get()
                    }
                    pop_img = np.array(sct.grab(pop_monitor))
                    pop_gray = cv2.cvtColor(pop_img, cv2.COLOR_BGRA2GRAY)
                    _, pop_thresh = cv2.threshold(pop_gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                    
                    pop_text_raw = pytesseract.image_to_string(pop_thresh, config=kor_config)
                    pop_text_clean = pop_text_raw.replace(" ", "").replace("\n", "").strip()

                    # ==========================================
                    # 💡 키워드 정밀 타격 매칭 ('안전하게 구출' 중복 차단)
                    # ==========================================
                    # '구출' 단독 매칭 대신 '갈고리'가 붙은 완벽한 문구만 카운트 (오타 '누출' 대응 포함)
                    detected_unhooks = pop_text_clean.count("갈고리구출") + pop_text_clean.count("갈고리누출")
                    detected_stuns = pop_text_clean.count("기절")
                    detected_blinds = pop_text_clean.count("실명")

                    # ==========================================
                    # A. 갈고리 구출 스택 (연속 구출 정상 반영)
                    # ==========================================
                    if detected_unhooks > active_unhooks:
                        added = detected_unhooks - active_unhooks
                        self.root.after(0, lambda a=added: self.s_unhooks.set(self.s_unhooks.get() + a))
                        active_unhooks = detected_unhooks
                        unhook_missing = 0
                    elif detected_unhooks < active_unhooks:
                        unhook_missing += 1
                        if unhook_missing >= 4:  # 팝업 사라질 때 약 0.45초 대기
                            active_unhooks = detected_unhooks
                            unhook_missing = 0
                    else:
                        unhook_missing = 0

                    # ==========================================
                    # B. 기절 스택 (최적화된 6프레임 대기)
                    # ==========================================
                    if detected_stuns > active_stuns:
                        added = detected_stuns - active_stuns
                        self.root.after(0, lambda a=added: self.s_stun.set(self.s_stun.get() + a))
                        active_stuns = detected_stuns
                        stun_missing = 0
                    elif detected_stuns < active_stuns:
                        stun_missing += 1
                        if stun_missing >= 3:  # 판자 스턴 화면 흔들림 고려 대기 시간 보정
                            active_stuns = detected_stuns
                            stun_missing = 0
                    else:
                        stun_missing = 0

                    # ==========================================
                    # C. 실명 스택 (최적화된 3프레임 대기)
                    # ==========================================
                    if detected_blinds > active_blinds:
                        added = detected_blinds - active_blinds
                        self.root.after(0, lambda a=added: self.s_stun.set(self.s_stun.get() + a))
                        active_blinds = detected_blinds
                        blind_missing = 0
                    elif detected_blinds < active_blinds:
                        blind_missing += 1
                        if blind_missing >= 3:
                            active_blinds = detected_blinds
                            blind_missing = 0
                    else:
                        blind_missing = 0

                except Exception as e:
                    pass
                
                time.sleep(0.15)

    def create_input_row(self, parent, text, variable, row):
        ttk.Label(parent, text=text).grid(row=row, column=0, padx=10, pady=2, sticky="e")
        ttk.Entry(parent, textvariable=variable, width=15).grid(row=row, column=1, padx=10, pady=2, sticky="w")

    def on_closing(self):
        self.ocr_running = False
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = DBDMMRApp(root)
    root.mainloop()