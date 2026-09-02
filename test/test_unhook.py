import time
import mss
import cv2
import numpy as np
import pytesseract

# Tesseract 설치 경로
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 팝업 감지 영역 (사용자 환경의 모니터 해상도/위치에 맞게 수치 변경)
POPUP_REGION = {
    "top": 98,      # 화면 위에서부터의 Y 좌표
    "left": 1683,    # 화면 왼쪽에서부터의 X 좌표
    "width": 194,    # 영역 가로 길이
    "height": 209     # 영역 세로 길이
}

def start_double_unhook_test():
    kor_config = r'--psm 6 -l kor'
    unhook_count = 0
    
    # 상태 관리 변수
    is_pop_active = False
    missing_frame_count = 0  # 팝업 사라짐 프레임 카운터

    print("==========================================")
    print(" 🎯 연속 구출 대응 정밀 OCR 테스트")
    print(" - 연속으로 2명 구출 시에도 즉시 각각 집계됩니다.")
    print(" - '안전한 구출' 팝업은 완벽 차단합니다.")
    print("==========================================\n")

    with mss.MSS() as sct:
        while True:
            try:
                pop_img = np.array(sct.grab(POPUP_REGION))
                pop_gray = cv2.cvtColor(pop_img, cv2.COLOR_BGRA2GRAY)
                _, pop_thresh = cv2.threshold(pop_gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

                pop_text_raw = pytesseract.image_to_string(pop_thresh, config=kor_config)
                pop_text = pop_text_raw.replace(" ", "").replace("\n", "").strip()

                # '안전' 차단 + ('구출' 또는 '갈고리' 계열 키워드)
                is_unhook_popup = ("안전" not in pop_text) and any(k in pop_text for k in ["구출", "갈고리", "고리"])

                if is_unhook_popup:
                    missing_frame_count = 0  # 팝업 감지 중이면 사라짐 카운터 초기화
                    
                    if not is_pop_active:
                        unhook_count += 1
                        is_pop_active = True
                        print(f"\n🎉 >>> [갈고리 구출 감지!] 현재 누적 구출 횟수: {unhook_count}회 <<<\n")
                else:
                    # 팝업이 화면에서 안 보일 경우 프레임 누적
                    if is_pop_active:
                        missing_frame_count += 1
                        # 약 0.4초(2프레임 연속) 동안 팝업이 없으면 다음 구출 감지 준비 완료
                        if missing_frame_count >= 2:
                            is_pop_active = False
                            missing_frame_count = 0

            except KeyboardInterrupt:
                print("\n테스트를 종료합니다.")
                break
            except Exception as e:
                print("오류 발생:", e)
            
            time.sleep(0.15) # 빠른 인식을 위해 루프 주기 감축 (0.15초)

if __name__ == '__main__':
    start_double_unhook_test()