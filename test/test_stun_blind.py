import time
import mss
import cv2
import numpy as np
import pytesseract
import sys

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
POPUP_REGION = {"top": 98, "left": 1683, "width": 194, "height": 209}

def test_stun_blind_combo():
    kor_config = r'--psm 6 -l kor'
    
    print("==========================================")
    print(" 🎯 [개수 추적 방식] 완벽 콤보/스택 집계 테스트")
    print(" - 화면에 떠 있는 단어의 '개수'가 늘어나면 즉시 카운트합니다.")
    print(" - 메세지가 사라지기 전에 연달아 뜨는 팝업도 완벽히 잡아냅니다.")
    print(" - [Ctrl+C]로 종료하세요.")
    print("==========================================\n")

    # On/Off 스위치 대신 '현재 화면에 떠 있는 개수'를 추적
    active_stuns = 0
    stun_missing = 0
    
    active_blinds = 0
    blind_missing = 0
    
    total_count = 0

    with mss.MSS() as sct:
        while True:
            try:
                pop_img = np.array(sct.grab(POPUP_REGION))
                pop_gray = cv2.cvtColor(pop_img, cv2.COLOR_BGRA2GRAY)
                _, pop_thresh = cv2.threshold(pop_gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                
                pop_text_raw = pytesseract.image_to_string(pop_thresh, config=kor_config)
                pop_text = pop_text_raw.replace(" ", "").replace("\n", "").strip()

                stun_triggered_now = False
                blind_triggered_now = False

                # 오작동 방지 (구출 팝업일 때는 기절/실명 감지 무시)
                if "구출" in pop_text:
                    detected_stuns = 0
                    detected_blinds = 0
                else:
                    # 화면에 '기절', '실명' 단어가 몇 개 있는지 각각 카운트
                    detected_stuns = pop_text.count("기절")
                    detected_blinds = pop_text.count("실명")

                # ==========================================
                # A. 기절 개수 추적 로직
                # ==========================================
                if detected_stuns > active_stuns:
                    # 화면의 기절 단어가 이전보다 늘어났다면! (새 팝업 등장)
                    added = detected_stuns - active_stuns
                    total_count += added
                    active_stuns = detected_stuns
                    stun_missing = 0
                    stun_triggered_now = True
                elif detected_stuns < active_stuns:
                    # 글자가 사라지거나 안 보이면 5프레임(0.75초) 대기 후 개수 차감
                    stun_missing += 1
                    if stun_missing >= 3.5:
                        active_stuns = detected_stuns
                        stun_missing = 0
                else:
                    stun_missing = 0 # 개수가 그대로면 대기 시간 초기화

                # ==========================================
                # B. 실명 개수 추적 로직
                # ==========================================
                if detected_blinds > active_blinds:
                    # 화면의 실명 단어가 이전보다 늘어났다면! (연속 눈뽕 스택)
                    added = detected_blinds - active_blinds
                    total_count += added
                    active_blinds = detected_blinds
                    blind_missing = 0
                    blind_triggered_now = True
                elif detected_blinds < active_blinds:
                    blind_missing += 1
                    if blind_missing >= 3:
                        active_blinds = detected_blinds
                        blind_missing = 0
                else:
                    blind_missing = 0
                
                # ==========================================
                # 콘솔 출력 상태 표시
                # ==========================================
                status_msg = "❌ 대기중"
                
                if stun_triggered_now and blind_triggered_now:
                    status_msg = "🔥 기절+실명!"
                elif stun_triggered_now:
                    status_msg = "💥 기절 추가!"
                elif blind_triggered_now:
                    status_msg = "🔦 실명 추가!"
                elif active_stuns > 0 and active_blinds > 0:
                    status_msg = f"💥🔦 (기절:{active_stuns} 실명:{active_blinds})"
                elif active_stuns > 0:
                    status_msg = f"💥 (기절:{active_stuns}개 유지)"
                elif active_blinds > 0:
                    status_msg = f"🔦 (실명:{active_blinds}개 유지)"

                if pop_text or active_stuns > 0 or active_blinds > 0:
                    sys.stdout.write(f"\r[{status_msg:18s}] 인식: '{pop_text:8s}' | 총 집계: {total_count}회     ")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r[{status_msg:18s}] 팝업 대기중... | 총 집계: {total_count}회              ")
                    sys.stdout.flush()

            except KeyboardInterrupt:
                print("\n\n테스트를 종료합니다.")
                break
            except Exception as e:
                pass
            
            time.sleep(0.15)

if __name__ == '__main__':
    test_stun_blind_combo()