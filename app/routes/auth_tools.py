from flask import Blueprint, render_template, request, jsonify
import pyotp
from app.services.email_service import EmailClient

bp_auth = Blueprint('auth_tools', __name__)

@bp_auth.route('/hotmail')
def route_hotmail():
    return render_template('hotmail.html', active_tool='hotmail', page_title='Read Outlook / Hotmail')

@bp_auth.route('/2fa')
def route_2fa():
    return render_template('2fa.html', active_tool='2fa', page_title='Two-Factor Auth (2FA)')

@bp_auth.route('/api/get-otp', methods=['POST'])
def api_get_otp():
    try:
        data = request.get_json() or {}
        credentials = data.get('credentials', '').strip()
        parts = credentials.split('|')
        if len(parts) < 4:
            return jsonify({'success': False, 'error': 'An error occurred. Please try again.'}), 400

        refresh_token = parts[2].strip()
        client_id = parts[3].strip()

        access_token = EmailClient.get_access_token(client_id, refresh_token)
        if not access_token:
            return jsonify({'success': False, 'error': 'An error occurred. Please try again.'}), 401

        messages = EmailClient.get_messages(access_token, top=100)
        parsed_emails = []
        seen_keys = set()

        for msg in messages:
            from_addr = msg.get('from', {}).get('emailAddress', {}).get('name') or msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')
            subject = msg.get('subject', 'No Subject')
            date_str = msg.get('receivedDateTime', '')
            try:
                date = date_str.split('T')[1][:5] if 'T' in date_str else date_str
            except Exception:
                date = date_str

            preview_text = msg.get('bodyPreview', '')
            body_content = msg.get('body', {}).get('content', '')
            otp = EmailClient.extract_otp(subject, preview_text, body_content)

            unique_key = otp if otp else f"{subject}_{date_str}"
            if unique_key in seen_keys:
                continue
            seen_keys.add(unique_key)

            parsed_emails.append({
                'from': from_addr,
                'subject': subject,
                'date': date,
                'otp': otp,
                'preview': preview_text,
                'body': body_content
            })

        return jsonify({'success': True, 'emails': parsed_emails})
    except Exception:
        return jsonify({'success': False, 'error': 'An error occurred. Please try again.'}), 500

@bp_auth.route('/api/get-2fa', methods=['POST'])
def api_get_2fa():
    try:
        secret = (request.get_json() or {}).get("key", "").strip().replace(" ", "").upper()
        if not secret:
            return jsonify({"success": False, "error": "An error occurred. Please try again."}), 400
        totp = pyotp.TOTP(secret)
        return jsonify({"success": True, "code": totp.now()})
    except Exception:
        return jsonify({"success": False, "error": "An error occurred. Please try again."}), 400
