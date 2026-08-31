from PIL import Image, ImageDraw

# 1. 데바데 스타일 로고 (logo.png) 생성 (어두운 배경 + 핏빛 텍스트)
logo = Image.new('RGB', (400, 80), color=(20, 20, 20))
draw = ImageDraw.Draw(logo)

# 데바데 느낌의 붉은 선(스크래치) 긋기
draw.line((20, 40, 380, 40), fill=(180, 0, 0), width=3)
draw.text((150, 20), "DBD MMR CALCULATOR", fill=(255, 50, 50))
logo.save('logo.png')
print("logo.png 파일이 생성되었습니다!")

# 2. 아이콘 (icon.ico) 생성 (심플한 붉은 바탕)
icon = Image.new('RGB', (64, 64), color=(139, 0, 0))
icon_draw = ImageDraw.Draw(icon)
icon_draw.line((15, 15, 49, 49), fill=(0, 0, 0), width=5)
icon_draw.line((15, 49, 49, 15), fill=(0, 0, 0), width=5)
icon.save('icon.ico', format='ICO')
print("icon.ico 파일이 생성되었습니다!")