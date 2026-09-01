import time
import mss
import cv2
import numpy as np
import pytesseract

# Tesseract 설치 경로
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 팝업 감지 영역 (사용자 환경의 모니터 해상도/위치에 맞게 수치 변경)
POPUP_REGION = {
    "top": 216,      # 화면 위에서부터의 Y 좌표
    "left": 1524,    # 화면 왼쪽에서부터의 X 좌표
    "width": 332,    # 영역 가로 길이
    "height": 265     # 영역 세로 길이
}

def start_unhook_test():
    kor_config = r'--psm 6 -l kor'
    unhook_count = 0
    pop_active = False

    print("==========================================")
    print(" 🎯 '구출' 메인 기반 정밀 OCR 테스트")
    print(" - '구출' 단어를 메인으로 인식하되, '안전' 단어는 차단합니다.")
    print("==========================================\n")

    with mss.MSS() as sct:
        while True:
            try:
                pop_img = np.array(sct.grab(POPUP_REGION))
                pop_gray = cv2.cvtColor(pop_img, cv2.COLOR_BGRA2GRAY)
                _, pop_thresh = cv2.threshold(pop_gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

                pop_text_raw = pytesseract.image_to_string(pop_thresh, config=kor_config)
                pop_text = pop_text_raw.replace(" ", "").replace("\n", "").strip()

                if pop_text:
                    print(f"[실시간 인식 텍스트]: {pop_text}")

                # 핵심 조건식: '안전'이 없고 '구출' 또는 '갈고리' 유사의 단어가 존재할 때
                is_unhook_popup = ("안전" not in pop_text) and any(k in pop_text for k in ["구출", "갈고리", "고리"])

                if is_unhook_popup:
                    if not pop_active:
                        unhook_count += 1
                        pop_active = True
                        print(f"\n🎉 >>> [갈고리 구출 감지!] 현재 누적 구출 횟수: {unhook_count}회 <<<\n")
                else:
                    # 화면에서 구출 글자가 지워지면 다음 감지 준비
                    pop_active = False

            except KeyboardInterrupt:
                print("\n테스트를 종료합니다.")
                break
            except Exception as e:
                print("오류 발생:", e)
            
            time.sleep(0.2)

if __name__ == '__main__':
    start_unhook_test()