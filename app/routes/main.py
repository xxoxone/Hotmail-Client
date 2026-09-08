from flask import Blueprint, render_template, Response

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

@bp_main.route('/robots.txt')
def robots():
    content = """User-agent: *
Allow: /
Sitemap: https://microtools.one/sitemap.xml
"""
    return Response(content, mimetype="text/plain")

@bp_main.route('/sitemap.xml')
def sitemap():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://microtools.one/</loc>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://microtools.one/hotmail</loc>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://microtools.one/2fa</loc>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://microtools.one/tiktok</loc>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://microtools.one/fb-check</loc>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://microtools.one/fb-uid</loc>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://microtools.one/x-downloader</loc>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://microtools.one/fb-id</loc>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://microtools.one/tempmail</loc>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://microtools.one/notepad</loc>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://microtools.one/gmail-dot</loc>
    <priority>0.5</priority>
  </url>
</urlset>"""
    return Response(content, mimetype="application/xml")
