import re
import requests

class EmailClient:
    @staticmethod
    def get_access_token(client_id, refresh_token):
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        payload = {
            'client_id': client_id,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'scope': 'https://graph.microsoft.com/Mail.Read'
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        try:
            res = requests.post(url, data=payload, headers=headers, timeout=12)
            return res.json().get('access_token') if res.status_code == 200 else None
        except Exception:
            return None

    @staticmethod
    def get_messages(access_token, top=100):
        url = f"https://graph.microsoft.com/v1.0/me/messages?$top={min(top, 100)}&$orderby=receivedDateTime DESC&$select=id,subject,from,receivedDateTime,bodyPreview,body"
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        try:
            res = requests.get(url, headers=headers, timeout=15)
            return res.json().get('value', []) if res.status_code == 200 else []
        except Exception:
            return []

    @staticmethod
    def clean_html(raw_html):
        if not raw_html:
            return ""
        return ' '.join(re.sub(re.compile('<.*?>'), ' ', raw_html).split())

    @staticmethod
    def extract_otp(subject, preview, body):
        clean_body = EmailClient.clean_html(body)
        context_patterns = [
            r'(?:confirmation\s+code|verification\s+code|security\s+code|passcode|otp|code|pin)\s*(?:is|:|-)?\s*<b>?\s*([A-Za-z0-9]{3,6}(?:-[A-Za-z0-9]{3,6})?|[0-9]{4,8})\b',
            r'(?:enter|use)\s+([A-Za-z0-9]{3,6}(?:-[A-Za-z0-9]{3,6})?|[0-9]{4,8})\s+(?:to\s+verify|as\s+your)',
            r'([A-Za-z0-9]{3,6}(?:-[A-Za-z0-9]{3,6})?|[0-9]{4,8})\s+is\s+your\s+(?:security\s+code|verification\s+code|confirmation\s+code|otp|code)'
        ]
        ignored = {'below', 'here', 'your', 'this', 'that', 'from', 'with', 'code'}
        for pattern in context_patterns:
            for text in [subject, preview, clean_body]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and match.group(1).strip().lower() not in ignored:
                    return match.group(1).strip()

        fallback_patterns = [
            r'\b([A-Za-z0-9]{3,4}-[A-Za-z0-9]{3,4})\b',
            r'\b(\d{3}[-\s]\d{3})\b',
            r'\b(\d{6})\b',
            r'\b(?!(?:19\d{2}|20[2-3]\d)\b)(\d{4,8})\b'
        ]
        for pattern in fallback_patterns:
            for text in [preview, clean_body]:
                match = re.search(pattern, text)
                if match:
                    return match.group(1).replace(" ", "")
        return None
