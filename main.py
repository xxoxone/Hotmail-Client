import os
import sys
import requests
import json
import re
from flask import Flask, request, jsonify, render_template_string
from waitress import serve

APP_NAME = "Email Reader"
if sys.platform.startswith('win'):
    os.system(f'title {APP_NAME}')
else:
    sys.stdout.write(f"\x1b]2;{APP_NAME}\x07")

app = Flask(__name__)
app.secret_key = os.urandom(24)

class EmailClient:
    @staticmethod
    def get_access_token(client_id, refresh_token):
        """Get access token using refresh token"""
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        payload = {
            'client_id': client_id,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'scope': 'https://graph.microsoft.com/Mail.Read'
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('access_token')
            return None
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None

    @staticmethod
    def get_messages(access_token, top=10):
        """Fetch email list"""
        url = f"https://graph.microsoft.com/v1.0/me/messages?$top={top}&$orderby=receivedDateTime DESC&$select=id,subject,from,receivedDateTime,bodyPreview,body"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get('value', [])
            return []
        except Exception as e:
            print(f"Error fetching messages: {e}")
            return []

    @staticmethod
    def extract_otp(text):
        """Extract OTP / Verification code from string matching various formats"""
        if not text:
            return None
        
        # Advanced Regex patterns for all common OTP formats:
        # e.g. 0000, 000000, 000-000, 000 000, 000-000-000, "code: 12345"
        patterns = [
            r'(?:code|otp|pin|verification|passcode|confirm)[^\d]*(\d{3,4}[-\s]?\d{3,4}[-\s]?\d{0,4})',
            r'\b(\d{3,4}[-\s]\d{3,4}(?:[-\s]\d{3,4})?)\b',  # Numbers separated by space/dash (000-000, 000 000)
            r'\b(\d{4,8})\b'                                 # Continuous digits (0000 to 00000000)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                otp_code = match.group(1).strip()
                # If match length is valid, return clean OTP
                if len(re.sub(r'\D', '', otp_code)) >= 4:
                    return otp_code
        return None


# Single Page UI Template
UI_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Reader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        
        /* Toast Notification Styling & Animation */
        #toast {
            visibility: hidden;
            min-width: 280px;
            transform: translateY(100px);
            transition: transform 0.3s ease-in-out, opacity 0.3s ease-in-out;
            opacity: 0;
        }
        #toast.show {
            visibility: visible;
            transform: translateY(0);
            opacity: 1;
        }
    </style>
</head>
<body class="bg-slate-100 min-h-screen text-slate-800 p-4 md:p-8 relative">

    <!-- Smart Toast Notification -->
    <div id="toast" class="fixed bottom-6 right-6 z-50 bg-slate-900 text-white px-5 py-3.5 rounded-2xl shadow-2xl border border-slate-700 flex items-center gap-3">
        <div class="w-7 h-7 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center shrink-0">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>
        </div>
        <div>
            <h4 id="toast-title" class="text-xs font-bold text-slate-200 uppercase tracking-wider">Copied to Clipboard</h4>
            <p id="toast-message" class="text-xs text-slate-400 font-mono mt-0.5"></p>
        </div>
    </div>

    <div class="max-w-2xl mx-auto space-y-6">
        
        <!-- Input Form Section -->
        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            <div class="flex items-center gap-3 mb-4">
                <div class="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 002-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                </div>
                <div>
                    <h1 class="text-xl font-bold text-slate-900">Email Reader</h1>
                    <p class="text-xs text-slate-500">Paste credentials string to read emails & extract OTPs</p>
                </div>
            </div>

            <form id="otp-form" onsubmit="handleFetchOtp(event)" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold text-slate-500 uppercase mb-2">Account Credentials String</label>
                    <textarea id="credentials-input" rows="2" oninput="handleInstantInput()" required placeholder="email|password|refresh_token|client_id" class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-mono bg-slate-50 transition"></textarea>
                    <p class="text-[11px] text-slate-400 mt-1">Format: email|password|refresh_token|client_id</p>
                </div>

                <div id="error-msg" class="hidden p-3 bg-red-50 text-red-600 text-xs rounded-lg border border-red-100"></div>

                <button type="submit" id="submit-btn" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-xl shadow-md transition text-sm flex items-center justify-center gap-2">
                    <span>Fetch OTP / Code</span>
                    <svg id="btn-spinner" class="w-4 h-4 hidden animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                </button>
            </form>
        </div>

        <!-- Target Email Box (Shows & Auto-Copies immediately on Input) -->
        <div id="email-display-box" class="hidden bg-white rounded-xl p-4 border border-slate-200 shadow-sm flex items-center justify-between gap-3">
            <div class="min-w-0">
                <span class="text-[10px] font-bold uppercase text-slate-400 tracking-wider block">Target Email Address</span>
                <span id="target-email-text" class="text-sm font-semibold text-slate-800 font-mono truncate block"></span>
            </div>
            <button id="copy-email-btn" onclick="manualCopyEmail()" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-3 py-2 rounded-lg transition font-medium shrink-0 flex items-center gap-1.5">
                <span>Copy Email</span>
            </button>
        </div>

        <!-- Live OTP Display Section -->
        <div class="space-y-3">
            <div class="flex justify-between items-center px-1">
                <h2 class="text-xs font-bold uppercase text-slate-400 tracking-wider">Latest Received Codes / OTPs</h2>
                <span id="mail-count" class="text-xs bg-slate-200 text-slate-600 font-semibold px-2 py-0.5 rounded-full">0</span>
            </div>

            <div id="otp-results" class="space-y-3">
                <div class="bg-white rounded-xl p-8 text-center text-slate-400 text-sm border border-slate-200">
                    Click "Fetch OTP / Code" above to load messages.
                </div>
            </div>
        </div>

    </div>

    <script>
        let currentExtractedEmail = "";
        let debounceTimer = null;

        // Instant detection only for Email extraction & Auto-Copy (NO API FETCH)
        function handleInstantInput() {
            clearTimeout(debounceTimer);
            
            debounceTimer = setTimeout(() => {
                const credentials = document.getElementById('credentials-input').value.trim();
                const emailBox = document.getElementById('email-display-box');
                const errorDiv = document.getElementById('error-msg');

                if (!credentials) {
                    emailBox.classList.add('hidden');
                    errorDiv.classList.add('hidden');
                    currentExtractedEmail = "";
                    return;
                }

                const parts = credentials.split('|');
                if (parts.length > 0 && parts[0].trim() !== "") {
                    const extractedEmail = parts[0].trim();
                    document.getElementById('target-email-text').innerText = extractedEmail;
                    emailBox.classList.remove('hidden');

                    // Auto-copy only if a new email is detected
                    if (currentExtractedEmail !== extractedEmail) {
                        currentExtractedEmail = extractedEmail;
                        copyToClipboard(currentExtractedEmail, "Email Address Copied!", currentExtractedEmail);
                    }
                }
            }, 200);
        }

        // Triggered ONLY when clicking "Fetch OTP / Code" button
        async function handleFetchOtp(event) {
            event.preventDefault();
            const credentials = document.getElementById('credentials-input').value.trim();
            const errorDiv = document.getElementById('error-msg');
            const submitBtn = document.getElementById('submit-btn');
            const btnSpinner = document.getElementById('btn-spinner');
            const resultsDiv = document.getElementById('otp-results');

            errorDiv.classList.add('hidden');
            
            const parts = credentials.split('|');
            if (!credentials || parts.length < 4) {
                errorDiv.textContent = 'Invalid format! Expected: email|password|refresh_token|client_id';
                errorDiv.classList.remove('hidden');
                return;
            }

            submitBtn.disabled = true;
            btnSpinner.classList.remove('hidden');

            try {
                const response = await fetch('/api/get-otp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ credentials: credentials })
                });

                const data = await response.json();

                if (data.success) {
                    const emails = data.emails || [];
                    document.getElementById('mail-count').innerText = emails.length;

                    if (emails.length === 0) {
                        resultsDiv.innerHTML = `<div class="bg-white rounded-xl p-6 text-center text-slate-500 text-sm border border-slate-200">No emails found!</div>`;
                        return;
                    }

                    resultsDiv.innerHTML = emails.map(item => {
                        return `
                            <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div class="space-y-1 min-w-0 flex-1">
                                    <div class="flex items-center gap-2">
                                        <span class="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md truncate max-w-[150px]">${escapeHtml(item.from)}</span>
                                        <span class="text-[11px] text-slate-400">${item.date}</span>
                                    </div>
                                    <h3 class="text-sm font-medium text-slate-800 truncate">${escapeHtml(item.subject)}</h3>
                                </div>

                                <div class="bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-center justify-between md:justify-end gap-3 min-w-[160px]">
                                    <div class="text-right">
                                        <div class="text-[10px] text-slate-400 font-semibold uppercase">Verification Code</div>
                                        <div class="text-xl font-extrabold text-slate-900 tracking-wider font-mono">${item.otp ? item.otp : '<span class="text-xs font-normal text-slate-400">No OTP found</span>'}</div>
                                    </div>
                                    ${item.otp ? `<button type="button" onclick="copyToClipboard('${item.otp}', 'OTP Copied!', '${item.otp}')" class="bg-indigo-600 hover:bg-indigo-700 text-white text-xs px-3 py-2 rounded-lg transition font-medium">Copy</button>` : ''}
                                </div>
                            </div>
                        `;
                    }).join('');

                } else {
                    errorDiv.textContent = data.error || 'Failed to load emails!';
                    errorDiv.classList.remove('hidden');
                }
            } catch (err) {
                console.error(err);
                errorDiv.textContent = 'Server connection error!';
                errorDiv.classList.remove('hidden');
            } finally {
                submitBtn.disabled = false;
                btnSpinner.classList.add('hidden');
            }
        }

        function manualCopyEmail() {
            if (currentExtractedEmail) {
                copyToClipboard(currentExtractedEmail, "Email Address Copied!", currentExtractedEmail);
            }
        }

        // Smart Copy & Toast Notification Function
        function copyToClipboard(text, title, message) {
            navigator.clipboard.writeText(text).then(() => {
                showToast(title, message);
            });
        }

        let toastTimer = null;
        function showToast(title, message) {
            const toast = document.getElementById('toast');
            document.getElementById('toast-title').innerText = title;
            document.getElementById('toast-message').innerText = message;

            toast.classList.add('show');

            clearTimeout(toastTimer);
            toastTimer = setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(UI_TEMPLATE)

@app.route('/api/get-otp', methods=['POST'])
def get_otp():
    try:
        data = request.get_json()
        credentials = data.get('credentials', '').strip()
        
        parts = credentials.split('|')
        if len(parts) < 4:
            return jsonify({'success': False, 'error': 'Invalid credentials string'}), 400
        
        email = parts[0].strip()
        refresh_token = parts[2].strip()
        client_id = parts[3].strip()
        
        # Get access token
        access_token = EmailClient.get_access_token(client_id, refresh_token)
        if not access_token:
            return jsonify({'success': False, 'error': 'Authentication failed! Check your refresh_token or client_id.'}), 401
        
        # Fetch emails
        messages = EmailClient.get_messages(access_token, top=10)
        
        parsed_emails = []
        for msg in messages:
            from_addr = msg.get('from', {}).get('emailAddress', {}).get('name') or msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')
            subject = msg.get('subject', 'No Subject')
            date_str = msg.get('receivedDateTime', '')
            
            try:
                date = date_str.split('T')[1][:5] if 'T' in date_str else date_str
            except:
                date = date_str

            preview_text = msg.get('bodyPreview', '')
            body_content = msg.get('body', {}).get('content', '')
            
            full_text = f"{subject} {preview_text} {body_content}"
            otp = EmailClient.extract_otp(full_text)
            
            parsed_emails.append({
                'from': from_addr,
                'subject': subject,
                'date': date,
                'otp': otp
            })
            
        return jsonify({'success': True, 'emails': parsed_emails})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"[{APP_NAME}] Serving on http://0.0.0.0:{port} ...")
    serve(app, host='0.0.0.0', port=port)
