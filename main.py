import os
import sys
import requests
import json
from datetime import datetime
import re
from flask import Flask, request, jsonify, render_template_string
from waitress import serve

# Process Name / Application Title সেট করা (OS / Terminal Title)
APP_NAME = "Email Client"
if sys.platform.startswith('win'):
    os.system(f'title {APP_NAME}')
else:
    sys.stdout.write(f"\x1b]2;{APP_NAME}\x07")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global storage for user session
user_data = {}

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
    def get_messages(access_token, top=50):
        """Fetch email list"""
        url = f"https://graph.microsoft.com/v1.0/me/messages?$top={top}&$orderby=receivedDateTime DESC&$select=id,subject,from,receivedDateTime,parentFolderId,isRead,bodyPreview"
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
    def get_message_details(access_token, message_id):
        """Fetch full email details"""
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}?$select=id,subject,from,toRecipients,receivedDateTime,body,isRead"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching message details: {e}")
            return None

# The UI HTML template with fixed scrolling and Title "Email Client"
UI_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en" class="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="color-scheme" content="light only">
    <meta name="supported-color-schemes" content="light">
    <title>Email Client</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            color-scheme: light only !important;
        }
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #f8fafc !important;
            color: #1e293b !important;
        }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
        
        .email-card {
            background-color: #ffffff !important;
            color: #0f172a !important;
        }
        .email-body-content {
            background-color: #ffffff !important;
            color: #334155 !important;
        }
        .email-body-content * {
            max-width: 100% !important;
        }
        
        .email-item {
            transition: all 0.2s ease;
            cursor: pointer;
        }
        .email-item:hover {
            background-color: #f8fafc;
        }
        
        .loading-spinner {
            border: 2px solid #f3f4f6;
            border-top: 2px solid #4f46e5;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Fix scrolling issues */
        .email-list-container {
            height: calc(100vh - 140px);
            overflow-y: auto;
            overflow-x: hidden;
        }
        
        .email-detail-container {
            height: calc(100vh - 140px);
            overflow-y: auto;
            overflow-x: hidden;
        }
        
        @media (max-width: 768px) {
            .email-list-container {
                height: calc(100vh - 120px);
            }
            .email-detail-container {
                height: calc(100vh - 120px);
            }
        }
        
        /* Force light theme */
        .bg-slate-50 { background-color: #f8fafc !important; }
        .bg-white { background-color: #ffffff !important; }
        .text-slate-800 { color: #1e293b !important; }
        .text-slate-900 { color: #0f172a !important; }
        .text-slate-700 { color: #334155 !important; }
        .text-slate-600 { color: #475569 !important; }
        .text-slate-500 { color: #64748b !important; }
        .text-slate-400 { color: #94a3b8 !important; }
        .border-slate-200 { border-color: #e2e8f0 !important; }
        .border-slate-100 { border-color: #f1f5f9 !important; }
        
        /* Email body styling */
        .email-body-content {
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        .email-body-content pre {
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .email-body-content img {
            max-width: 100%;
            height: auto;
        }
    </style>
</head>
<body class="bg-slate-50 text-slate-800 antialiased h-screen flex flex-col overflow-hidden">

    <!-- LOGIN SCREEN SECTION -->
    <div id="login-screen" class="min-h-screen flex items-center justify-center p-4 overflow-y-auto">
        <div class="bg-white rounded-2xl shadow-xl border border-slate-100 p-8 w-full max-w-lg">
            <div class="text-center mb-8">
                <div class="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 mb-3">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 002-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                </div>
                <h1 class="text-2xl font-bold text-slate-900">Email Client</h1>
                <p class="text-slate-500 text-sm mt-1">Paste your authentication credentials string below</p>
            </div>

            <div id="login-error" class="hidden mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                Invalid Credentials!
            </div>

            <form id="login-form" class="space-y-4" onsubmit="handleLogin(event)">
                <div>
                    <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Account String Format</label>
                    <textarea id="credentials-input" rows="3" required placeholder="email|password|refresh_token|client_id" class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm transition font-mono bg-slate-50/50"></textarea>
                    <p class="text-xs text-slate-400 mt-2">Format: email|password|refresh_token|client_id</p>
                </div>
                <button type="submit" class="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 rounded-xl shadow-lg transition duration-200 text-sm">
                    Connect Inbox
                </button>
            </form>
        </div>
    </div>

    <!-- MAIN DASHBOARD SECTION (Hidden by default) -->
    <div id="dashboard-screen" class="hidden h-screen flex flex-col overflow-hidden">
        
        <header class="bg-white border-b border-slate-200 px-4 md:px-6 py-3 flex items-center justify-between z-10 shrink-0">
            <div class="flex items-center gap-3 min-w-0">
                <div id="user-avatar" class="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
                    U
                </div>
                <div class="min-w-0">
                    <h2 id="user-email" class="text-sm font-semibold text-slate-900 truncate">user@hotmail.com</h2>
                    <p class="text-xs text-emerald-600 flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Connected
                    </p>
                </div>
            </div>
            <button onclick="handleLogout()" class="text-xs font-medium text-slate-500 hover:text-red-600 transition shrink-0 ml-2">Logout</button>
        </header>

        <div class="flex-1 flex overflow-hidden relative">
            
            <!-- Email List Sidebar -->
            <div id="email-list-container" class="w-full md:w-5/12 bg-white border-r border-slate-200 flex flex-col h-full">
                <div class="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50 shrink-0">
                    <span class="text-xs font-semibold uppercase text-slate-400 tracking-wider">Inbox (<span id="mail-count">0</span>)</span>
                    <button onclick="fetchMailList()" class="text-xs text-indigo-600 font-medium hover:underline flex items-center gap-1">
                        <svg id="refresh-spinner" class="w-3.5 h-3.5 hidden animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                        Refresh
                    </button>
                </div>

                <div id="email-list" class="flex-1 overflow-y-auto custom-scrollbar divide-y divide-slate-100 email-list-container">
                    <div class="p-8 text-center text-slate-400 text-sm">Loading emails...</div>
                </div>
            </div>

            <!-- Full Message Display Container -->
            <div id="email-detail-container" class="hidden md:flex flex-1 bg-slate-50 flex-col h-full absolute md:relative inset-0 z-20 md:z-0">
                <div class="p-3 bg-white border-b border-slate-200 md:hidden flex items-center shrink-0">
                    <button onclick="closeMobileDetail()" class="text-xs font-semibold text-indigo-600 flex items-center gap-1 bg-indigo-50 px-3 py-1.5 rounded-lg">
                        ← Back to Inbox
                    </button>
                </div>

                <div id="email-detail-content" class="flex-1 overflow-y-auto custom-scrollbar p-3 md:p-6 email-detail-container">
                    <div class="h-full flex flex-col items-center justify-center text-slate-400">
                        <svg class="w-12 h-12 mb-3 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 19v-8.93a2 2 0 010.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5"></path></svg>
                        <p class="text-sm">Select an email to view details</p>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <!-- JAVASCRIPT logic -->
    <script>
        let currentActiveId = null;

        async function handleLogin(event) {
            event.preventDefault();
            const credentials = document.getElementById('credentials-input').value.trim();
            
            if (!credentials) {
                showError('Please enter your credentials');
                return;
            }

            const parts = credentials.split('|');
            if (parts.length < 4) {
                showError('Invalid format. Expected: email|password|refresh_token|client_id');
                return;
            }

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ credentials: credentials })
                });

                const data = await response.json();

                if (data.success) {
                    document.getElementById('login-screen').classList.add('hidden');
                    document.getElementById('dashboard-screen').classList.remove('hidden');
                    document.getElementById('user-email').textContent = data.email || 'user@email.com';
                    document.getElementById('user-avatar').textContent = (data.email || 'U')[0].toUpperCase();
                    document.getElementById('login-error').classList.add('hidden');
                    fetchMailList();
                } else {
                    showError(data.error || 'Login failed');
                }
            } catch (error) {
                showError('Connection error. Please try again.');
                console.error(error);
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('login-error');
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
        }

        function handleLogout() {
            document.getElementById('dashboard-screen').classList.add('hidden');
            document.getElementById('login-screen').classList.remove('hidden');
            document.getElementById('credentials-input').value = '';
            document.getElementById('login-error').classList.add('hidden');
            
            // Clear session
            fetch('/api/logout', { method: 'POST' });
        }

        async function fetchMailList() {
            const spinner = document.getElementById('refresh-spinner');
            spinner.classList.remove('hidden');
            
            try {
                const response = await fetch('/api/messages');
                const data = await response.json();
                
                const listContainer = document.getElementById('email-list');
                
                if (!response.ok) {
                    listContainer.innerHTML = `<div class="p-8 text-center text-red-500 text-sm">Error: ${data.error || 'Failed to fetch emails'}</div>`;
                    document.getElementById('mail-count').innerText = '0';
                    return;
                }

                const messages = data.messages || [];
                document.getElementById('mail-count').innerText = messages.length;

                if (messages.length === 0) {
                    listContainer.innerHTML = '<div class="p-8 text-center text-slate-400 text-sm">📭 No emails found</div>';
                    return;
                }

                listContainer.innerHTML = messages.map(msg => {
                    const sender = (msg.from && msg.from.emailAddress) ? 
                        (msg.from.emailAddress.name || msg.from.emailAddress.address || 'Unknown') : 'Unknown';
                    const subject = msg.subject || 'No Subject';
                    const date = msg.receivedDateTime ? new Date(msg.receivedDateTime).toLocaleDateString() : '';
                    const isSelected = currentActiveId === msg.id;

                    return `
                        <div onclick="loadEmailDetail('${msg.id}', this)" class="email-item p-4 hover:bg-slate-50 transition border-l-2 ${isSelected ? 'border-indigo-600 bg-indigo-50/30' : 'border-transparent'}" data-id="${msg.id}">
                            <div class="flex justify-between items-baseline mb-1">
                                <span class="text-sm font-medium text-slate-900 truncate max-w-[180px]">${escapeHtml(sender)}</span>
                                <span class="text-[11px] text-slate-400">${date}</span>
                            </div>
                            <div class="text-xs font-semibold text-slate-700 truncate mb-1">${escapeHtml(subject)}</div>
                            <div class="text-xs text-slate-400 truncate">${msg.bodyPreview ? escapeHtml(msg.bodyPreview.substring(0, 100)) : 'Click to read email body...'}</div>
                        </div>
                    `;
                }).join('');

            } catch (err) {
                console.error(err);
                document.getElementById('email-list').innerHTML = '<div class="p-8 text-center text-red-500 text-sm">Failed to load emails</div>';
            } finally {
                spinner.classList.add('hidden');
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function loadEmailDetail(msgId, element) {
            currentActiveId = msgId;

            // Update selection state
            document.querySelectorAll('.email-item').forEach(el => {
                el.classList.remove('border-indigo-600', 'bg-indigo-50/30');
                el.classList.add('border-transparent');
            });
            if(element) {
                element.classList.remove('border-transparent');
                element.classList.add('border-indigo-600', 'bg-indigo-50/30');
            }

            const detailContainer = document.getElementById('email-detail-container');
            const detailContent = document.getElementById('email-detail-content');

            // Show detail container on mobile
            if (window.innerWidth < 768) {
                detailContainer.classList.remove('hidden');
                detailContainer.style.display = 'flex';
            } else {
                detailContainer.classList.remove('hidden');
            }

            detailContent.innerHTML = `
                <div class="h-full flex items-center justify-center text-slate-400 text-sm">
                    <div class="loading-spinner mr-2"></div>
                    Loading email...
                </div>
            `;

            try {
                const response = await fetch(`/api/message/${encodeURIComponent(msgId)}`);
                const msg = await response.json();

                if (!response.ok) {
                    detailContent.innerHTML = `<div class="p-4 text-red-500 text-sm">Error: ${msg.error || 'Failed to load email'}</div>`;
                    return;
                }

                const sender = (msg.from && msg.from.emailAddress) ? 
                    (msg.from.emailAddress.name || msg.from.emailAddress.address || 'Unknown') : 'Unknown';
                const subject = msg.subject || 'No Subject';
                const date = msg.receivedDateTime ? new Date(msg.receivedDateTime).toLocaleString() : '';
                const toRecipients = msg.toRecipients || [];
                const to = toRecipients.map(r => r.emailAddress && r.emailAddress.address ? r.emailAddress.address : '').filter(Boolean).join(', ');
                const body = (msg.body && msg.body.content) ? msg.body.content : '<p class="text-slate-400">Empty message body.</p>';

                detailContent.innerHTML = `
                    <div class="email-card bg-white rounded-2xl p-4 md:p-8 border border-slate-200 shadow-sm w-full max-w-3xl mx-auto mb-8">
                        <div class="border-b border-slate-100 pb-4 mb-4">
                            <h1 class="text-lg md:text-xl font-bold text-slate-900 mb-2">${escapeHtml(subject)}</h1>
                            <div class="flex flex-col md:flex-row md:items-center justify-between text-xs md:text-sm gap-1">
                                <div>
                                    <span class="text-slate-500">From:</span> 
                                    <span class="font-medium text-slate-800">${escapeHtml(sender)}</span>
                                </div>
                                <div class="text-xs text-slate-400">${escapeHtml(date)}</div>
                            </div>
                            ${to ? `<div class="text-xs text-slate-500 mt-1"><span class="text-slate-500">To:</span> ${escapeHtml(to)}</div>` : ''}
                        </div>
                        <div class="email-body-content text-slate-800 text-sm leading-relaxed overflow-x-auto">
                            ${body}
                        </div>
                    </div>
                `;

            } catch (err) {
                console.error(err);
                detailContent.innerHTML = `<div class="p-4 text-red-500 text-sm">Failed to load email content.</div>`;
            }
        }

        function closeMobileDetail() {
            const detailContainer = document.getElementById('email-detail-container');
            detailContainer.classList.add('hidden');
            detailContainer.style.display = '';
        }

        // Auto-refresh on mobile when clicking back
        document.addEventListener('DOMContentLoaded', function() {
            function handleResize() {
                if (window.innerWidth >= 768) {
                    const detailContainer = document.getElementById('email-detail-container');
                    detailContainer.classList.remove('hidden');
                    detailContainer.style.display = '';
                }
            }
            
            window.addEventListener('resize', handleResize);
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the main UI"""
    return render_template_string(UI_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    """Handle login and store session"""
    try:
        data = request.get_json()
        credentials = data.get('credentials', '').strip()
        
        if not credentials:
            return jsonify({'success': False, 'error': 'No credentials provided'}), 400
        
        parts = credentials.split('|')
        if len(parts) < 4:
            return jsonify({'success': False, 'error': 'Invalid format. Expected: email|password|refresh_token|client_id'}), 400
        
        email = parts[0].strip()
        password = parts[1].strip()  # Not used, but kept for format
        refresh_token = parts[2].strip()
        client_id = parts[3].strip()
        
        # Get access token
        access_token = EmailClient.get_access_token(client_id, refresh_token)
        
        if not access_token:
            return jsonify({'success': False, 'error': 'Failed to authenticate. Please check your credentials.'}), 401
        
        # Store user data
        user_data['access_token'] = access_token
        user_data['email'] = email
        user_data['refresh_token'] = refresh_token
        user_data['client_id'] = client_id
        
        return jsonify({
            'success': True,
            'email': email
        })
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Clear session"""
    user_data.clear()
    return jsonify({'success': True})

@app.route('/api/messages')
def get_messages():
    """Get list of messages"""
    if 'access_token' not in user_data:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        messages = EmailClient.get_messages(user_data['access_token'])
        return jsonify({'messages': messages})
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/message/<message_id>')
def get_message(message_id):
    """Get full message details"""
    if 'access_token' not in user_data:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        message = EmailClient.get_message_details(user_data['access_token'], message_id)
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        return jsonify(message)
    except Exception as e:
        print(f"Error fetching message: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # OS Environment থেকে পোর্ট নেওয়া হচ্ছে, না থাকলে বাইডিফল্ট 5000 ব্যবহার করবে
    port = int(os.getenv('PORT', 5000))
    
    print(f"[{APP_NAME}] Serving Web App via Waitress WSGI on http://0.0.0.0:{port} ...")
    serve(app, host='0.0.0.0', port=port)
