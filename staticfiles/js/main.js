document.addEventListener('DOMContentLoaded', function() {
    // Initialize QR Scanner
    if (document.getElementById('startScanner')) {
        const startBtn = document.getElementById('startScanner');
        const scannerContainer = document.getElementById('scanner-container');
        const scannerVideo = document.getElementById('scanner');
        let scanner = null;

        startBtn.addEventListener('click', function() {
            if (scannerContainer.style.display === 'none') {
                // Start scanner
                scannerContainer.style.display = 'block';
                startBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Scanner';
                startBtn.classList.remove('btn-primary');
                startBtn.classList.add('btn-danger');

                scanner = new Instascan.Scanner({
                    video: scannerVideo,
                    mirror: false,
                    scanPeriod: 5
                });

                scanner.addListener('scan', function(content) {
                    fetch(window.location.href, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRFToken': '{{ csrf_token }}'
                        },
                        body: `scan_data=${encodeURIComponent(content)}`
                    }).then(response => {
                        if (response.ok) {
                            window.location.reload();
                        }
                    });
                });

                Instascan.Camera.getCameras().then(function(cameras) {
                    if (cameras.length > 0) {
                        scanner.start(cameras[0]);
                    } else {
                        alert('No cameras found.');
                        stopScanner();
                    }
                }).catch(function(e) {
                    console.error(e);
                    alert('Camera error: ' + e);
                    stopScanner();
                });
            } else {
                // Stop scanner
                stopScanner();
            }
        });

        function stopScanner() {
            if (scanner) {
                scanner.stop();
            }
            scannerContainer.style.display = 'none';
            startBtn.innerHTML = '<i class="fas fa-play"></i> Start Scanner';
            startBtn.classList.remove('btn-danger');
            startBtn.classList.add('btn-primary');
        }
    }
});