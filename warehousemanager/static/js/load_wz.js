function updateFileName() {
        const fileInput = document.getElementById('wz_file');
        const fileNameDisplay = document.getElementById('file-name');
        fileNameDisplay.textContent = fileInput.files[0] ? fileInput.files[0].name : 'No file chosen';
    }