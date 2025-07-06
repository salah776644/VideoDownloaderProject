document.addEventListener('DOMContentLoaded', function() {
    let isDownloading = false;

    document.querySelectorAll('.download-btn').forEach(button => {
        button.addEventListener('click', async function(event) {
            event.preventDefault();
            if (this.disabled) return;

            isDownloading = true;
            
            const formatId = this.dataset.formatId;
            const vformatId = this.dataset.vformatId;
            const aformatId = this.dataset.aformatId;
            const title = this.dataset.title;
            const ext = this.dataset.ext;

            const originalButtonHTML = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            this.disabled = true;

            try {
                let requestUrl = `/api/process-download?user_ip=${USER_IP}&original_url=${ORIGINAL_URL}&title=${encodeURIComponent(title)}&ext=${ext}`;
                
                // تحديد نوع الطلب بناءً على البيانات المتاحة
                if (formatId) { // فيديو مدمج أو صوت فقط
                    requestUrl += `&format_id=${formatId}`;
                } else if (vformatId && aformatId) { // دمج فيديو وصوت
                    requestUrl += `&vformat_id=${vformatId}&aformat_id=${aformatId}`;
                } else {
                    throw new Error("لا توجد صيغة صالحة للتحميل.");
                }
                
                const response = await fetch(requestUrl);
                const result = await response.json();

                if (!response.ok) throw new Error(result.error);
                
                window.location.href = `/serve-file/${USER_IP.replace(/:/g, '_')}/${result.filename}`;

            } catch (error) {
                alert('فشل التحميل: ' + error.message);
            } finally {
                setTimeout(() => {
                    this.innerHTML = originalButtonHTML;
                    this.disabled = false;
                    isDownloading = false;
                }, 4000);
            }
        });
    });

    window.addEventListener('beforeunload', function() {
        if (isDownloading) return;
        const formData = new FormData();
        formData.append('user_ip', USER_IP);
        navigator.sendBeacon('/api/cleanup', formData);
    });
});