import re

try:
    html1 = open('forte_debug.html', encoding='utf-8').read()
    print("debug html count buy:", len(re.findall(r'"buy":', html1)))
    print("debug html count sell:", len(re.findall(r'"sell":', html1)))
except Exception as e:
    print(e)

try:
    html2 = open('forte_debug2.html', encoding='utf-8').read()
    print("debug html2 count buy:", len(re.findall(r'"buy":', html2)))
    print("debug html2 count sell:", len(re.findall(r'"sell":', html2)))
    print("debug html2 count RUB:", len(re.findall(r'RUB', html2)))
    print("debug html2 count CNY:", len(re.findall(r'CNY', html2)))
except Exception as e:
    print(e)
