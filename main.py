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
    def get_messages(access_token, top=100):
        """Fetch email list with max limit 100"""
        top = min(top, 100)
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
        
        patterns = [
            r'(?:code|otp|pin|verification|passcode|confirm)[^\d]*(\d{3,4}[-\s]?\d{3,4}[-\s]?\d{0,4})',
            r'\b(\d{3,4}[-\s]\d{3,4}(?:[-\s]\d{3,4})?)\b',
            r'\b(\d{4,8})\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                otp_code = match.group(1).strip()
                if len(re.sub(r'\D', '', otp_code)) >= 4:
                    return otp_code
        return None

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

    <!-- Toast Notification -->
    <div id="toast" class="fixed bottom-6 right-6 z-50 bg-slate-900 text-white px-5 py-3.5 rounded-2xl shadow-2xl border border-slate-700 flex items-center gap-3">
        <div class="w-7 h-7 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center shrink-0">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>
        </div>
        <div>
            <h4 id="toast-title" class="text-xs font-bold text-slate-200 uppercase tracking-wider">Copied to Clipboard</h4>
            <p id="toast-message" class="text-xs text-slate-400 font-mono mt-0.5"></p>
        </div>
    </div>

    <div class="max-w-3xl mx-auto space-y-6">
        
        <!-- Main Form Section -->
        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            
            <!-- Large Prominent Counters Row -->
            <div class="grid grid-cols-2 gap-4 mb-6">
                <div class="bg-indigo-50/70 border border-indigo-100 rounded-xl p-4 flex items-center justify-between">
                    <div>
                        <span class="text-xs font-bold uppercase tracking-wider text-indigo-500 block">Total Emails</span>
                        <span id="count-total" class="text-2xl font-extrabold text-indigo-900 font-mono">0</span>
                    </div>
                    <div class="p-2.5 bg-indigo-100 text-indigo-600 rounded-lg">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                    </div>
                </div>

                <div class="bg-amber-50/70 border border-amber-100 rounded-xl p-4 flex items-center justify-between">
                    <div>
                        <span class="text-xs font-bold uppercase tracking-wider text-amber-600 block">Remaining</span>
                        <span id="count-remaining" class="text-2xl font-extrabold text-amber-900 font-mono">0</span>
                    </div>
                    <div class="p-2.5 bg-amber-100 text-amber-600 rounded-lg">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    </div>
                </div>
            </div>

            <form id="otp-form" onsubmit="handleFetchOtp(event)" class="space-y-4">
                <div>
                    <!-- Header Row with Label & Clear All Button -->
                    <div class="flex items-center justify-between mb-2">
                        <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Bulk Credentials Input</label>
                        
                        <button type="button" onclick="clearAllInput()" class="text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 px-3 py-1.5 rounded-lg transition border border-red-100 flex items-center gap-1.5">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                            Clear All
                        </button>
                    </div>

                    <textarea id="credentials-input" rows="8" wrap="off" oninput="handleInstantInput()" placeholder="email|password|refresh_token|client_id" class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs font-mono bg-slate-50 transition whitespace-pre overflow-x-auto leading-relaxed"></textarea>
                </div>

                <div id="error-msg" class="hidden p-3 bg-red-50 text-red-600 text-xs rounded-lg border border-red-100"></div>

                <div class="flex items-center gap-3">
                    <button type="submit" id="submit-btn" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-xl shadow-md transition text-sm flex items-center justify-center gap-2">
                        <span>Fetch OTP / Code</span>
                        <svg id="btn-spinner" class="w-4 h-4 hidden animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    </button>

                    <!-- Next Email Button -->
                    <button type="button" onclick="loadNextEmail()" class="bg-slate-800 hover:bg-slate-900 text-white font-medium px-5 py-3 rounded-xl shadow-md transition text-sm flex items-center gap-1.5 shrink-0">
                        <span>Next Email</span>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7"></path></svg>
                    </button>
                </div>
            </form>
        </div>

        <!-- Target Email Box -->
        <div id="email-display-box" class="hidden bg-white rounded-xl p-4 border border-slate-200 shadow-sm flex items-center justify-between gap-3">
            <div class="min-w-0">
                <span class="text-[10px] font-bold uppercase text-slate-400 tracking-wider block">Active Email Address</span>
                <span id="target-email-text" class="text-sm font-semibold text-slate-800 font-mono truncate block"></span>
            </div>
            <button id="copy-email-btn" onclick="manualCopyEmail()" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-3 py-2 rounded-lg transition font-medium shrink-0 flex items-center gap-1.5">
                <span>Copy Email</span>
            </button>
        </div>

        <!-- Results Display -->
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
        let initialTotalCount = 0;

        window.addEventListener('DOMContentLoaded', () => {
            try {
                const savedInput = localStorage.getItem('email_reader_credentials');
                const savedTotal = localStorage.getItem('email_reader_total_count');

                if (savedInput !== null) {
                    document.getElementById('credentials-input').value = savedInput;
                }
                if (savedTotal !== null) {
                    initialTotalCount = parseInt(savedTotal) || 0;
                }
            } catch (e) {
                console.error("LocalStorage error:", e);
            }

            handleInstantInput();
        });

        function getValidLines() {
            const inputElement = document.getElementById('credentials-input');
            let lines = inputElement.value.split('\\n').map(l => l.trim()).filter(l => l !== "");
            
            // Max input limit set to 100
            if (lines.length > 100) {
                lines = lines.slice(0, 100);
                inputElement.value = lines.join('\\n');
                showToast("Max Limit Reached", "You can only input up to 100 lines at once.");
            }
            return lines;
        }

        function handleInstantInput() {
            clearTimeout(debounceTimer);
            
            // getValidLines automatically limits and updates input field to 100 lines if exceeded
            const lines = getValidLines();
            const rawValue = document.getElementById('credentials-input').value;
            
            try {
                localStorage.setItem('email_reader_credentials', rawValue);
            } catch (e) {
                console.error("Failed to save to localStorage:", e);
            }

            if (lines.length > initialTotalCount) {
                initialTotalCount = lines.length;
                try { localStorage.setItem('email_reader_total_count', initialTotalCount); } catch(e){}
            } else if (lines.length === 0) {
                initialTotalCount = 0;
                try { localStorage.setItem('email_reader_total_count', 0); } catch(e){}
            }

            document.getElementById('count-total').innerText = initialTotalCount;
            document.getElementById('count-remaining').innerText = lines.length;

            debounceTimer = setTimeout(() => {
                const emailBox = document.getElementById('email-display-box');
                const errorDiv = document.getElementById('error-msg');

                if (lines.length === 0) {
                    emailBox.classList.add('hidden');
                    errorDiv.classList.add('hidden');
                    currentExtractedEmail = "";
                    return;
                }

                const firstLine = lines[0];
                const parts = firstLine.split('|');
                if (parts.length > 0 && parts[0].trim() !== "") {
                    const extractedEmail = parts[0].trim();
                    document.getElementById('target-email-text').innerText = extractedEmail;
                    emailBox.classList.remove('hidden');

                    if (currentExtractedEmail !== extractedEmail) {
                        currentExtractedEmail = extractedEmail;
                        copyToClipboard(currentExtractedEmail, "Email Address Copied!", currentExtractedEmail);
                    }
                }
            }, 200);
        }

        function loadNextEmail() {
            const input = document.getElementById('credentials-input');
            const lines = input.value.split('\\n');
            
            while (lines.length > 0 && lines[0].trim() === "") {
                lines.shift();
            }
            if (lines.length > 0) {
                lines.shift();
            }

            input.value = lines.join('\\n');
            
            document.getElementById('otp-results').innerHTML = `
                <div class="bg-white rounded-xl p-8 text-center text-slate-400 text-sm border border-slate-200">
                    Click "Fetch OTP / Code" above to load messages.
                </div>
            `;
            document.getElementById('mail-count').innerText = "0";

            handleInstantInput();
        }

        function clearAllInput() {
            document.getElementById('credentials-input').value = "";
            try {
                localStorage.removeItem('email_reader_credentials');
                localStorage.removeItem('email_reader_total_count');
            } catch(e){}
            
            initialTotalCount = 0;
            document.getElementById('count-total').innerText = "0";
            document.getElementById('count-remaining').innerText = "0";

            document.getElementById('email-display-box').classList.add('hidden');
            document.getElementById('error-msg').classList.add('hidden');
            document.getElementById('otp-results').innerHTML = `
                <div class="bg-white rounded-xl p-8 text-center text-slate-400 text-sm border border-slate-200">
                    Click "Fetch OTP / Code" above to load messages.
                </div>
            `;
            document.getElementById('mail-count').innerText = "0";
            currentExtractedEmail = "";
        }

        async function handleFetchOtp(event) {
            event.preventDefault();
            const lines = getValidLines();
            const errorDiv = document.getElementById('error-msg');
            const submitBtn = document.getElementById('submit-btn');
            const btnSpinner = document.getElementById('btn-spinner');
            const resultsDiv = document.getElementById('otp-results');

            errorDiv.classList.add('hidden');

            if (lines.length === 0) {
                errorDiv.textContent = 'Please enter at least one line of credentials!';
                errorDiv.classList.remove('hidden');
                return;
            }

            const firstLine = lines[0];
            const parts = firstLine.split('|');
            if (parts.length < 4) {
                errorDiv.textContent = 'Invalid format in active line! Expected: email|password|refresh_token|client_id';
                errorDiv.classList.remove('hidden');
                return;
            }

            submitBtn.disabled = true;
            btnSpinner.classList.remove('hidden');

            try {
                const response = await fetch('/api/get-otp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ credentials: firstLine })
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
        
        access_token = EmailClient.get_access_token(client_id, refresh_token)
        if not access_token:
            return jsonify({'success': False, 'error': 'Authentication failed! Check your refresh_token or client_id.'}), 401
        
        # Max limit set to 100
        messages = EmailClient.get_messages(access_token, top=100)
        
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
