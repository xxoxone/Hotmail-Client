from flask import Blueprint, render_template, request, jsonify
from app.services.fb_service import check_facebook_identity_precise, extract_facebook_uid

bp_fb = Blueprint('fb_tools', __name__)

@bp_fb.route('/fb-check')
def route_fb_check():
    return render_template('fb_check.html', active_tool='fb-check', page_title='Check FB Number (Batch)')

@bp_fb.route('/fb-uid')
def route_fb_uid():
    return render_template('fb_uid.html', active_tool='fb-uid', page_title='FB Link to UID Extractor')

@bp_fb.route('/api/check-fb', methods=['POST'])
def api_check_fb():
    data = request.get_json() or {}
    target = data.get("identifier", "").strip()
    proxy = data.get("proxy", "").strip()
    return jsonify({"found": check_facebook_identity_precise(target, proxy)})

@bp_fb.route('/api/extract-uid', methods=['POST'])
def api_extract_uid():
    link = (request.get_json() or {}).get("url", "").strip()
    return jsonify({"uid": extract_facebook_uid(link)})
