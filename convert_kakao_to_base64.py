import base64

# KakaoPay.png 파일을 base64로 인코딩
with open('KakaoPay.png', 'rb') as f:
    image_data = f.read()
    base64_data = base64.b64encode(image_data).decode('utf-8')

# 결과를 파일로 저장
with open('kakao_base64.txt', 'w') as f:
    f.write(f'KAKAO_PAY_IMAGE_BASE64 = """{base64_data}"""')

print("KakaoPay.png가 base64로 인코딩되어 kakao_base64.txt에 저장되었습니다.")
print(f"인코딩된 데이터 크기: {len(base64_data)} 문자") 