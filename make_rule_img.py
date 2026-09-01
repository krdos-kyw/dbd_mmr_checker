import os
from PIL import Image, ImageDraw, ImageFont

width, height = 1120, 1520
img = Image.new("RGB", (width, height), color=(20, 20, 24))
draw = ImageDraw.Draw(img)

# Windows 시스템 폰트 로드
font_path = "C:/Windows/Fonts/malgun.ttf"
if not os.path.exists(font_path):
    font_path = "C:/Windows/Fonts/gulim.ttc"

try:
    font_title = ImageFont.truetype(font_path, 40)
    font_sub = ImageFont.truetype(font_path, 30)
    font_body = ImageFont.truetype(font_path, 24)
except Exception:
    font_title = font_sub = font_body = ImageFont.load_default()

# 타이틀
draw.text((40, 40), "《데드바이데이라이트》 MMR 산출 상세 규칙", fill=(255, 215, 0), font=font_title)
draw.line((40, 110, 1080, 110), fill=(255, 215, 0), width=4)

# 생존자
y = 140
draw.rectangle([40, y, 1080, y+56], fill=(40, 65, 110))
draw.text((60, y+8), "■ 생존자 (Survivor) 점수 산출 규칙", fill=(255, 255, 255), font=font_sub)
y += 76

surv_rules = [
    ("발전기 수리", "150% / 200% / 300% -> +0 / +2 / +4점 (150% 미만: -4점)"),
    ("갈고리 구출", "1회 / 2회 / 3회 / 4회 -> +0 / +1 / +2 / +4점 (0회: -4점)"),
    ("타인 치료", "50% / 100% / 150% / 200% -> +1 / +2 / +3 / +4점 (50% 미만: 0점)"),
    ("어그로(추격)", "30s / 60s / 90s / 120s -> +0 / +2 / +4 / +8점 (30s 미만: -8점)\n※ 180s 초과 추격당할 경우 '터널링 피해자' 판정 (+8점)"),
    ("기절 / 실명", "1회 / 2회 / 3회 / 4회 -> +1 / +2 / +3 / +4점 (판자, 손전등 등)"),
    ("탈출 및 희생", "탈출구: +8점  |  개구: +0점  |  희생(사망): -8점")
]

for title, desc in surv_rules:
    draw.text((60, y), f"• {title}:", fill=(120, 200, 255), font=font_body)
    lines = desc.split('\n')
    draw.text((280, y), lines[0], fill=(230, 230, 230), font=font_body)
    if len(lines) > 1:
        y += 36
        draw.text((280, y), lines[1], fill=(255, 180, 100), font=font_body)
    y += 48

# 살인마
y += 20
draw.rectangle([40, y, 1080, y+56], fill=(110, 45, 55))
draw.text((60, y+8), "■ 살인마 (Killer) 점수 산출 규칙", fill=(255, 255, 255), font=font_sub)
y += 76

killer_rules = [
    ("발전기 감퇴", "50% / 75% / 100% / 150% -> +1 / +2 / +3 / +4점 (50% 미만: 0점)\n※ '주술: 파멸(루인)' 적용시 감퇴 점수 제외"),
    ("추격 시간", "30s / 60s / 90s / 120s 이내 다운 -> +8 / +4 / +2 / +0점\n※ 180s 이상 한 명만 추격시 '터널링' 판정 (-8점)"),
    ("희생 및 처형", "1명 / 2명 / 3명 / 4명 -> +2 / +4 / +6 / +8점\n※ 마지막 생존자가 개구로 탈출 시 +1점"),
    ("남은 발전기", "5개 / 4개 / 3개 / 2개 / 1개 남음 -> +5 / +4 / +3 / +2 / +1점 (0개: 0점)"),
    ("생존자 탈출", "1명 / 2명 / 3명 / 4명 탈출 시 -> -2 / -4 / -6 / -8점")
]

for title, desc in killer_rules:
    draw.text((60, y), f"• {title}:", fill=(255, 130, 130), font=font_body)
    lines = desc.split('\n')
    draw.text((280, y), lines[0], fill=(230, 230, 230), font=font_body)
    if len(lines) > 1:
        y += 36
        draw.text((280, y), lines[1], fill=(255, 180, 100), font=font_body)
    y += 48

draw.rectangle([40, height-80, 1080, height-30], fill=(30, 30, 38), outline=(80, 80, 90))
draw.text((260, height-66), "💡 창을 닫으려면 [ESC] 키 또는 X 버튼을 누르세요.", fill=(200, 200, 200), font=font_body)

img.save("rule_info.png")
print("고해상도 rule_info.png 생성 완료!")