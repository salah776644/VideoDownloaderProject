# 1. استخدام صورة بايثون رسمية كنظام أساسي
FROM python:3.11-slim

# 2. تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# 3. تحديث النظام وتثبيت ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 4. نسخ ملف المتطلبات
COPY requirements.txt .

# 5. تثبيت مكتبات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# 6. نسخ جميع ملفات المشروع
COPY . .

# 7. تحديد الأمر الذي سيتم تشغيله عند بدء تشغيل الخادم
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "2", "app:app"]
