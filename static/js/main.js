/**
 * EASY INTERVIEW - Main JavaScript
 * Handles: Dropdown, sidebar, file upload, alerts
 * NOTE: Interview speech-to-text is handled inline in interview.html
 */

// ============================================
// DROPDOWN TOGGLE
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    // Profile dropdown
    const profileBtn = document.querySelector('.profile-btn');
    const dropdownMenu = document.querySelector('.dropdown-menu');

    if (profileBtn && dropdownMenu) {
        profileBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdownMenu.classList.toggle('show');
        });

        document.addEventListener('click', function(e) {
            if (!dropdownMenu.contains(e.target) && !profileBtn.contains(e.target)) {
                dropdownMenu.classList.remove('show');
            }
        });
    }

    // Mobile sidebar toggle (Hardened)
    const mobileBtn = document.querySelector('.mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');

    if (mobileBtn && sidebar) {
        mobileBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            console.log('Mobile menu clicked');
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('show');
        });

        if (overlay) {
            overlay.addEventListener('click', function() {
                sidebar.classList.remove('open');
                overlay.classList.remove('show');
            });
        }
        
        // Close on link click (mobile)
        sidebar.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 1024) {
                    sidebar.classList.remove('open');
                    if (overlay) overlay.classList.remove('show');
                }
            });
        });
    }

    // File upload area
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.querySelector('.upload-area input[type="file"]');
    const fileSelected = document.querySelector('.file-selected');

    if (uploadArea && fileInput) {
        ['dragenter', 'dragover'].forEach(evt => {
            uploadArea.addEventListener(evt, function(e) {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(evt => {
            uploadArea.addEventListener(evt, function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });
        });

        fileInput.addEventListener('change', function() {
            if (this.files.length > 0 && fileSelected) {
                fileSelected.textContent = '📎 Selected: ' + this.files[0].name;
                fileSelected.classList.add('show');
            }
        });
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(function() { alert.remove(); }, 300);
        }, 5000);
    });
});
