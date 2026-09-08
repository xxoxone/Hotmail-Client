import secrets
import requests
from flask import Blueprint, render_template, request, jsonify, Response
from app.services.media_service import download_tiktok_video, extract_x_video_info

bp_media = Blueprint('media_tools', __name__)

@bp_media.route('/tiktok')
def route_tiktok():
    return render_template('tiktok.html', active_tool='tiktok', page_title='TikTok HD Downloader')

@bp_media.route('/x-downloader')
def route_x_downloader():
    return render_template('x_downloader.html', active_tool='x-downloader', page_title='X Video Downloader')

@bp_media.route('/api/download-tiktok', methods=['POST'])
def api_download_tiktok():
    url = (request.get_json() or {}).get("url", "").strip()
    if not url:
        return jsonify({"success": False, "message": "An error occurred. Please try again."})
    
    dl_url, play_url = download_tiktok_video(url)
    if not dl_url:
        return jsonify({"success": False, "message": "An error occurred. Please try again."})

    return jsonify({
        "success": True, 
        "download_url": dl_url,
        "play_url": play_url
    })

@bp_media.route('/api/get-x-video', methods=['POST'])
def api_get_x_video():
    tweet_url = (request.get_json() or {}).get('url', '').strip()
    if not tweet_url:
        return jsonify({'error': 'An error occurred. Please try again.'}), 400
    try:
        data = extract_x_video_info(tweet_url)
        if not data.get('video_url'):
            return jsonify({'error': 'An error occurred. Please try again.'}), 404
        return jsonify(data)
    except Exception:
        return jsonify({'error': 'An error occurred. Please try again.'}), 500

@bp_media.route('/api/stream-x')
def api_stream_x():
    media_url = request.args.get('url')
    is_download = request.args.get('dl') == '1'
    if not media_url:
        return 'An error occurred. Please try again.', 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://x.com/'
    }
    req_range = request.headers.get('Range')
    if req_range:
        headers['Range'] = req_range

    try:
        r = requests.get(media_url, headers=headers, stream=True)
        resp_headers = {
            'Content-Type': r.headers.get('Content-Type', 'video/mp4'),
            'Accept-Ranges': 'bytes'
        }

        if 'Content-Range' in r.headers:
            resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Content-Length' in r.headers:
            resp_headers['Content-Length'] = r.headers['Content-Length']

        if is_download:
            rand = secrets.token_hex(8).upper()
            resp_headers['Content-Disposition'] = f'attachment; filename="MicroTools-{rand}.mp4"'

        def generate():
            for chunk in r.iter_content(chunk_size=1024 * 128):
                yield chunk

        return Response(generate(), status=r.status_code, headers=resp_headers)
    except Exception:
        return 'An error occurred. Please try again.', 500
