from PIL import Image, ImageDraw

# 파란색 바탕의 좌표 추출기 전용 아이콘 생성
icon = Image.new('RGB', (64, 64), color=(30, 144, 255)) # 딥 스카이 블루
icon_draw = ImageDraw.Draw(icon)

# 십자선(Target) 모양 그리기
icon_draw.line((32, 10, 32, 54), fill=(255, 255, 255), width=4)
icon_draw.line((10, 32, 54, 32), fill=(255, 255, 255), width=4)
icon_draw.rectangle([20, 20, 44, 44], outline=(255, 255, 255), width=3)

icon.save('coord_icon.ico', format='ICO')
print("coord_icon.ico 파일이 성공적으로 생성되었습니다!")