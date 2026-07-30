from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# 📌 구글 시트에서 '웹에 게시'한 CSV URL
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQGedjmRmY8xOs1TyW9AFHrlQa7yJQRQ5Ni__InlPF7g_IHYKRSjNyGBhubnYOYE-GQEl1P16I33Ycx/pub?output=csv"

@app.route('/api/kakao/check-status', methods=['POST'])
def check_status():
    req = request.get_json()
    
    # 카카오톡 오픈빌더에서 전달받은 이메일 파라미터 (search_keyword)
    try:
        user_email = req.get('action', {}).get('detailParams', {}).get('search_keyword', {}).get('value', '').strip()
    except Exception:
        user_email = ""

    if not user_email:
        return jsonify(make_kakao_response("이메일 주소가 정상적으로 전달되지 않았습니다."))

    try:
        # 구글 시트 CSV 데이터 읽기
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = [col.strip() for col in df.columns]
        
        # 이메일 열 자동 찾기 (보통 A열/타임스탬프 이후나 '이메일' 포함 열)
        email_col = None
        for col in df.columns:
            if '이메일' in col or 'email' in col.lower():
                email_col = col
                break
        
        if not email_col:
            # 이메일 열을 이름으로 못 찾을 경우 2번째 열(B열) 기본 지정
            email_col = df.columns[1]

        # 사용자가 입력한 이메일 검색 (대소문자 무시)
        filtered_df = df[df[email_col].astype(str).str.strip().str.lower() == user_email.lower()]

        if filtered_df.empty:
            message = (
                f"🔍 [{user_email}] 계정으로 접수된 내역을 찾을 수 없습니다.\n\n"
                f"구글 폼에 작성하신 이메일 주소가 맞는지 다시 한번 확인해 주세요."
            )
        else:
            # 가장 최근 접수된 내역 (마지막 행)
            latest_row = filtered_df.iloc[-1]
            submit_time = latest_row.iloc[0] # A열: 타임스탬프
            
            # I열 (인덱스 8): 처리 상태
            # 열 개수가 부족할 경우를 대비한 안전 처리
            raw_status = str(latest_row.iloc[8]).strip() if len(latest_row) > 8 else "접수"

            # 📌 상태별 맞춤 멘트 및 이모지 분기
            if raw_status == "접수":
                status_detail = "📥 [접수 완료]\n담당자가 문의 내용을 확인하고 있습니다. 빠르게 확인 후 답변해 드리겠습니다."
            elif raw_status == "진행중":
                status_detail = "⚙️ [처리 진행 중]\n현재 담당 부서에서 요청 내용을 처리하고 있습니다. 잠시만 기다려 주세요!"
            elif raw_status == "완료":
                status_detail = "✅ [처리 완료]\n문의하신 사항이 처리가 완료되었습니다. 상세 내용은 작성하신 이메일을 확인해 주세요."
            else:
                status_detail = f"ℹ️ [{raw_status}]\n현재 상태를 확인 중입니다."

            message = (
                f"📋 [{user_email}] 님의 최신 처리 현황입니다.\n\n"
                f"• 접수 일시: {submit_time}\n"
                f"• 현재 상태: {status_detail}"
            )

        return jsonify(make_kakao_response(message))

    except Exception as e:
        print(f"Error: {e}")
        return jsonify(make_kakao_response("처리 현황을 조회하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."))


def make_kakao_response(text_message):
    """카카오톡 텍스트형 응답 포맷 생성"""
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text_message
                    }
                }
            ]
        }
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)