import mss
import cv2
import numpy as np
import pytesseract

# 1. Tesseract가 설치된 실제 경로를 지정해 줍니다.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 2. 캡처할 모니터 영역 (본인 화면에 맞게 top, left, width, height 숫자를 조절해야 합니다)
# 아래는 1920x1080 해상도 기준, 대략적인 좌측 하단 영역입니다.
monitor = {"top": 796, "left": 157, "width": 132, "height": 68}

with mss.MSS() as sct:
    print("화면 캡처를 시작합니다...")
    
    # 지정한 영역 캡처 후 OpenCV 배열로 변환
    img = np.array(sct.grab(monitor))
    
    # 흑백으로 변환하여 글자 인식률을 높임
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    
    # 0~5 사이의 숫자만 읽도록 화이트리스트 설정
    custom_config = r'--psm 7 -c tessedit_char_whitelist=012345'
    text = pytesseract.image_to_string(gray, config=custom_config)
    
    print(f"인식된 남은 발전기 수: {text.strip()}")
    
    # 내가 지정한 좌표가 정확히 발전기 숫자를 가리키는지 이미지 창을 띄워 확인
    cv2.imshow("Captured ROI", gray)
    cv2.waitKey(0) # 아무 키나 누르면 창 닫힘
    cv2.destroyAllWindows()