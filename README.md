# DBD MMR Checker 

# 1. 배포
```bash
git add .
git commit -m "DBD MMR Checker V1.2.1.1"
git push -u origin main

# 2. 파일 생성
- 좌표 추출기
pyinstaller -w -F -n "DBD 좌표 추출기" --icon=coord_icon.ico --add-data="coord_icon.ico;." get_coords.py
py -m PyInstaller -w -F -n "DBD 좌표 추출기" --icon=coord_icon.ico --add-data="coord_icon.ico;." get_coords.py

- mmr checker 생성
py -m PyInstaller -w -F --icon=icon.ico --add-data="logo.png;." --add-data="icon.ico;." --add-data="rule_info.png;." DBD_MMR_Calculator.py

# 3. 파일 정보
DBD_MMR_Calculator.py : mmr 계산기 메인 파일
get_coords.py : 좌표기 메인 파일
make_coord_icon.py : 좌표기 프로그램 아이콘 파일 (coord_icon.ico)
make_images.py : mmr 계산기 프로그램 아이콘 파일 (icon.ico/logo.png)

---
