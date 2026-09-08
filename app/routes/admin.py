import os
from flask import Blueprint, render_template, request, session
from config import ADMIN_PASSWORD, COOKIE_FILE_PATH

bp_admin = Blueprint('admin', __name__)

def get_current_cookie_content():
    try:
        if os.path.exists(COOKIE_FILE_PATH):
            with open(COOKIE_FILE_PATH, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass
    return ""

@bp_admin.route('/xadminx', methods=['GET', 'POST'])
def route_admin():
    if request.args.get('logout') == '1':
        session.pop('admin_auth', None)

    if request.method == 'POST':
        if not session.get('admin_auth'):
            pwd = request.form.get('password', '')
            if pwd == ADMIN_PASSWORD:
                session['admin_auth'] = True
                return render_template('admin.html', authenticated=True, current_cookies=get_current_cookie_content())
            return render_template('admin.html', authenticated=False, error=True)
        else:
            action = request.form.get('action')
            if action == 'update_cookie':
                new_cookies = request.form.get('cookie_content', '').strip()
                try:
                    os.makedirs(os.path.dirname(COOKIE_FILE_PATH), exist_ok=True)
                    with open(COOKIE_FILE_PATH, 'w', encoding='utf-8') as f:
                        f.write(new_cookies)
                    return render_template('admin.html', authenticated=True, current_cookies=new_cookies, message="Saved successfully")
                except Exception:
                    return render_template('admin.html', authenticated=True, current_cookies=new_cookies, message="Error writing file")

    if session.get('admin_auth'):
        return render_template('admin.html', authenticated=True, current_cookies=get_current_cookie_content())

    return render_template('admin.html', authenticated=False)
