document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. تفعيل الأكورديون للأسئلة الشائعة ---
    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        question.addEventListener('click', () => {
            // إغلاق جميع الأسئلة الأخرى
            faqItems.forEach(otherItem => {
                if (otherItem !== item && otherItem.classList.contains('active')) {
                    otherItem.classList.remove('active');
                }
            });
            // فتح أو إغلاق السؤال الحالي
            item.classList.toggle('active');
        });
    });

    // --- 2. تأثيرات الحركة عند ظهور العناصر ---
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    // إضافة كلاس للتحريك
    document.querySelectorAll('.bento-box, .content-section').forEach(el => {
        el.classList.add('fade-in-up');
        observer.observe(el);
    });
});

// --- 3. إضافة CSS للحركات في رأس الصفحة ---
const style = document.createElement('style');
style.innerHTML = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .fade-in-up {
        opacity: 0;
    }
    .animate-in {
        animation: fadeInUp 0.8s ease-out forwards;
    }
`;
document.head.appendChild(style);
