import os
import shutil
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
import yt_dlp

# --- إعداد التطبيق والمجلد المؤقت ---
app = Flask(__name__)
DOWNLOAD_FOLDER = 'temp_downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- 1. المسارات الرئيسية للصفحات ---

@app.route('/')
def index():
    """ يعرض الصفحة الرئيسية. """
    return render_template('index.html')

@app.route('/downloading')
def downloading_page():
    """ يعرض صفحة التحميل وينفذ نظام الحذف الذكي. """
    video_url = request.args.get('url')
    if not video_url:
        return redirect(url_for('index'))

    # نظام الحذف الذكي بناءً على IP المستخدم
    user_ip = request.remote_addr.replace(':', '_')
    user_folder = os.path.join(DOWNLOAD_FOLDER, user_ip)
    if os.path.exists(user_folder):
        shutil.rmtree(user_folder)
    os.makedirs(user_folder)

    ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(video_url, download=False)

        # التصنيف الذكي للصيغ (مدمج، فيديو فقط، صوت فقط)
        complete_formats, video_only_formats, audio_only_formats = {}, {}, {}
        
        for f in video_info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('resolution'):
                res = int(f['resolution'].split('x')[1])
                if res not in complete_formats or f.get('filesize', 0) > complete_formats.get(res, {}).get('filesize', 0):
                    complete_formats[res] = f
            elif f.get('vcodec') != 'none' and f.get('resolution'):
                res = int(f['resolution'].split('x')[1])
                if res not in video_only_formats or f.get('filesize', 0) > video_only_formats.get(res, {}).get('filesize', 0):
                    video_only_formats[res] = f
            elif f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('abr'):
                abr = int(f['abr'])
                if abr not in audio_only_formats or f.get('filesize', 0) > audio_only_formats.get(abr, {}).get('filesize', 0):
                    audio_only_formats[abr] = f

        # ترتيب الصيغ من الأعلى للأقل
        sorted_complete = sorted(complete_formats.values(), key=lambda x: x.get('height', 0), reverse=True)
        sorted_video_only = sorted(video_only_formats.values(), key=lambda x: x.get('height', 0), reverse=True)
        sorted_audio_only = sorted(audio_only_formats.values(), key=lambda x: x.get('abr', 0), reverse=True)
        
        return render_template('download_page.html', 
                               video_info=video_info, original_url=video_url, user_ip=user_ip,
                               sorted_complete=sorted_complete,
                               sorted_video_only=sorted_video_only,
                               sorted_audio_only=sorted_audio_only)
    except Exception as e:
        print(f"Error fetching video info: {e}")
        return redirect(url_for('index'))

@app.route('/privacy-policy')
def privacy_policy():
    """ يعرض صفحة سياسة الخصوصية. """
    return render_template('privacy_policy.html')

@app.route('/terms-of-use')
def terms_of_use():
    """ يعرض صفحة شروط الاستخدام. """
    return render_template('terms_of_use.html')

# --- 2. مسارات API للوظائف الخلفية ---

@app.route('/api/process-download')
def process_download():
    """ يقوم بتحميل الملف المحدد ودمجه إذا لزم الأمر. """
    user_ip = request.args.get('user_ip')
    original_url = request.args.get('original_url')
    title = request.args.get('title', 'video')
    
    format_id = request.args.get('format_id')
    vformat_id = request.args.get('vformat_id')
    aformat_id = request.args.get('aformat_id')

    if not all([user_ip, original_url]):
        return jsonify({'error': 'Request parameters are missing.'}), 400

    user_folder = os.path.join(DOWNLOAD_FOLDER, user_ip.replace(':', '_'))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    safe_title = "".join(c for c in title if c.isalnum() or c in ' ._-').rstrip()
    
    try:
        # الحالة 1: تحميل فيديو مدمج أو صوت فقط
        if format_id:
            path_tmpl = os.path.join(user_folder, f"{safe_title[:60]}.%(ext)s")
            ydl_opts = {'format': format_id, 'outtmpl': path_tmpl}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(original_url, download=True)
                final_filename = os.path.basename(ydl.prepare_filename(info))
            return jsonify({'filename': final_filename})

        # الحالة 2: دمج فيديو منفصل مع صوت
        elif vformat_id and aformat_id:
            video_path_tmpl = os.path.join(user_folder, f"video_{safe_title[:50]}.%(ext)s")
            audio_path_tmpl = os.path.join(user_folder, f"audio_{safe_title[:50]}.%(ext)s")
            
            with yt_dlp.YoutubeDL({'format': vformat_id, 'outtmpl': video_path_tmpl}) as ydl:
                info = ydl.extract_info(original_url, download=True)
                video_filename = ydl.prepare_filename(info)
            
            with yt_dlp.YoutubeDL({'format': aformat_id, 'outtmpl': audio_path_tmpl}) as ydl:
                info = ydl.extract_info(original_url, download=True)
                audio_filename = ydl.prepare_filename(info)
            
            output_filename = f"{safe_title[:60]}.mp4"
            output_path = os.path.join(user_folder, output_filename)
            
            print("-> Starting FFmpeg merge with re-encoding...")
            subprocess.run([
                'ffmpeg', '-y', '-i', video_filename, '-i', audio_filename,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', output_path
            ], check=True, capture_output=True)
            print("-> Merging complete.")
            
            os.remove(video_filename)
            os.remove(audio_filename)
            return jsonify({'filename': output_filename})
        
        else:
            return jsonify({'error': 'Invalid format combination.'}), 400

    except Exception as e:
        print(f"Error during processing: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print("FFMPEG STDERR:", e.stderr.decode())
        return jsonify({'error': f'فشل في معالجة الملف: {e}'}), 500

@app.route('/serve-file/<user_ip>/<filename>')
def serve_file(user_ip, filename):
    """ يرسل الملف المحفوظ للمستخدم. """
    user_folder = os.path.join(DOWNLOAD_FOLDER, user_ip.replace(':', '_'))
    return send_from_directory(user_folder, filename, as_attachment=True)

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """ يحذف مجلد المستخدم فورًا عند مغادرة الصفحة. """
    user_ip = request.form.get('user_ip')
    if user_ip:
        user_folder = os.path.join(DOWNLOAD_FOLDER, user_ip.replace(':', '_'))
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
    return "OK", 200

# --- نقطة انطلاق التطبيق للتشغيل المحلي ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
