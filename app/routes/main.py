from flask import Blueprint, render_template

bp_main = Blueprint('main', __name__)

@bp_main.route('/')
def route_home():
    return render_template('home.html', active_tool='home', page_title='Home')

@bp_main.route('/fb-id')
def route_fb_id():
    return render_template('under_construction.html', active_tool='fb-id', page_title='Find Facebook ID')

@bp_main.route('/tempmail')
def route_tempmail():
    return render_template('under_construction.html', active_tool='tempmail', page_title='Tempmail Generator')

@bp_main.route('/notepad')
def route_notepad():
    return render_template('under_construction.html', active_tool='notepad', page_title='Online Notepad')

@bp_main.route('/gmail-dot')
def route_gmail_dot():
    return render_template('under_construction.html', active_tool='gmail-dot', page_title='Gmail Dot Trick Generator')
