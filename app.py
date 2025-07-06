import os
import sys
import shutil
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
import yt_dlp

# --- إعداد التطبيق ---
app = Flask(__name__)
DOWNLOAD_FOLDER = 'temp_downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- دالة ذكية لاختيار ملف الكوكيز المناسب ---
def get_cookies_file(url):
    """
    تحدد ملف الكوكيز الذي يجب استخدامه بناءً على رابط الفيديو.
    """
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube_cookies.txt"
    elif "facebook.com" in url or "fb.watch" in url:
        return "facebook_cookies.txt"
    elif "instagram.com" in url:
        return "instagram_cookies.txt"
    else:
        # لا تستخدم أي ملف كوكيز للمواقع الأخرى
        return None

# --- 1. المسارات الرئيسية للصفحات ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/downloading')
def downloading_page():
    video_url = request.args.get('url')
    if not video_url:
        return redirect(url_for('index'))

    # --- التحديث التلقائي لـ yt-dlp ---
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'], check=True)
    except Exception as update_e:
        print(f"Could not upgrade yt-dlp: {update_e}")

    user_ip = request.remote_addr.replace(':', '_')
    user_folder = os.path.join(DOWNLOAD_FOLDER, user_ip)
    if os.path.exists(user_folder):
        shutil.rmtree(user_folder)
    os.makedirs(user_folder)

    # --- إعداد خيارات yt-dlp مع اختيار الكوكيز الديناميكي ---
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    
    cookies_file = get_cookies_file(video_url)
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts['cookies'] = cookies_file
        print(f"-> Using cookies file: {cookies_file}")
    # --------------------------------------------------------

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(video_url, download=False)
        
        # ... (بقية منطق الفرز والترتيب يبقى كما هو)
        complete_formats, video_only_formats, audio_only_formats = {}, {}, {}
        for f in video_info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('resolution'):
                res = int(f['resolution'].split('x')[1]); complete_formats[res] = f
            elif f.get('vcodec') != 'none' and f.get('resolution'):
                res = int(f['resolution'].split('x')[1]); video_only_formats[res] = f
            elif f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('abr'):
                abr = int(f['abr']); audio_only_formats[abr] = f
        sorted_complete = sorted(complete_formats.values(), key=lambda x: x.get('height', 0), reverse=True)
        sorted_video_only = sorted(video_only_formats.values(), key=lambda x: x.get('height', 0), reverse=True)
        sorted_audio_only = sorted(audio_only_formats.values(), key=lambda x: x.get('abr', 0), reverse=True)
        
        return render_template('download_page.html', video_info=video_info, original_url=video_url, user_ip=user_ip,
                               sorted_complete=sorted_complete, sorted_video_only=sorted_video_only, sorted_audio_only=sorted_audio_only)
    except Exception as e:
        print(f"Error fetching video info: {e}")
        return redirect(url_for('index'))

# --- (بقية المسارات تبقى كما هي بدون أي تغيير) ---

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms-of-use')
def terms_of_use():
    return render_template('terms_of_use.html')

@app.route('/api/process-download')
def process_download():
    user_ip = request.args.get('user_ip'); original_url = request.args.get('original_url')
    title = request.args.get('title', 'video'); format_id = request.args.get('format_id')
    vformat_id = request.args.get('vformat_id'); aformat_id = request.args.get('aformat_id')
    if not all([user_ip, original_url]): return jsonify({'error': 'Missing params'}), 400
    user_folder = os.path.join(DOWNLOAD_FOLDER, user_ip.replace(':', '_'))
    if not os.path.exists(user_folder): os.makedirs(user_folder)
    safe_title = "".join(c for c in title if c.isalnum() or c in ' ._-').rstrip()
    try:
        if format_id:
            path_tmpl = os.path.join(user_folder, f"{safe_title[:60]}.%(ext)s")
            with yt_dlp.YoutubeDL({'format': format_id, 'outtmpl': path_tmpl}) as ydl:
                info = ydl.extract_info(original_url, download=True); filename = os.path.basename(ydl.prepare_filename(info))
            return jsonify({'filename': filename})
        elif vformat_id and aformat_id:
            vpath_tmpl = os.path.join(user_folder, f"v_{safe_title[:50]}.%(ext)s")
            apath_tmpl = os.path.join(user_folder, f"a_{safe_title[:50]}.%(ext)s")
            with yt_dlp.YoutubeDL({'format': vformat_id, 'outtmpl': vpath_tmpl}) as ydl:
                v_info = ydl.extract_info(original_url, download=True); v_filename = ydl.prepare_filename(v_info)
            with yt_dlp.YoutubeDL({'format': aformat_id, 'outtmpl': apath_tmpl}) as ydl:
                a_info = ydl.extract_info(original_url, download=True); a_filename = ydl.prepare_filename(a_info)
            out_filename = f"{safe_title[:60]}.mp4"; out_path = os.path.join(user_folder, out_filename)
            subprocess.run(['ffmpeg', '-y', '-i', v_filename, '-i', a_filename, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', out_path], check=True)
            os.remove(v_filename); os.remove(a_filename)
            return jsonify({'filename': out_filename})
        else: return jsonify({'error': 'Invalid format combination.'}), 400
    except Exception as e: print(f"Processing error: {e}"); return jsonify({'error': f'Processing error: {e}'}), 500

@app.route('/serve-file/<user_ip>/<filename>')
def serve_file(user_ip, filename):
    user_folder = os.path.join(DOWNLOAD_FOLDER, user_ip.replace(':', '_'))
    return send_from_directory(user_folder, filename, as_attachment=True)

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    user_ip = request.form.get('user_ip')
    if user_ip:
        user_folder = os.path.join(DOWNLOAD_FOLDER, user_ip.replace(':', '_'))
        if os.path.exists(user_folder): shutil.rmtree(user_folder)
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
