document.addEventListener('DOMContentLoaded', () => {
    const viewer = new PrintFlowViewer('threejs-container');

    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('model-input');
    const progressWrapper = document.getElementById('progress-wrapper');
    const uploadFilename = document.getElementById('upload-filename');
    const uploadPercent = document.getElementById('upload-percent');
    const uploadBar = document.getElementById('upload-bar');
    const inspectionBadge = document.getElementById('inspection-badge');
    const confirmForm = document.getElementById('confirm-order-form');
    const confirmBtn = document.getElementById('btn-confirm-order');

    const ALLOWED_EXT = ['stl', 'step', 'obj'];
    const MAX_BYTES = 50 * 1024 * 1024;

    // Botones de control del Visor 3D
    document.getElementById('btn-rotate')?.addEventListener('click', () => viewer.toggleAutoRotate());
    document.getElementById('btn-zoom-in')?.addEventListener('click', () => viewer.zoom(0.85));
    document.getElementById('btn-zoom-out')?.addEventListener('click', () => viewer.zoom(1.18));
    document.getElementById('btn-reset')?.addEventListener('click', () => viewer.resetView());
    document.getElementById('btn-orient')?.addEventListener('click', () => viewer.rotate90X());

    // Eventos Drag & Drop
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.backgroundColor = '#e6dccb';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.backgroundColor = 'var(--sand-bg)';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.backgroundColor = 'var(--sand-bg)';
        if (e.dataTransfer.files.length > 0) {
            handleSelectedFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleSelectedFile(fileInput.files[0]);
        }
    });

    function handleSelectedFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();

        if (!ALLOWED_EXT.includes(ext)) {
            alert('Formato no permitido. Solo se aceptan archivos .STL, .STEP u .OBJ.');
            return;
        }

        if (file.size > MAX_BYTES) {
            alert('El archivo excede el límite máximo de 50 MB.');
            return;
        }

        // 1. Renderizar inmediatamente en el lienzo Three.js
        viewer.loadLocalFile(file);

        // 2. Preparar barra de progreso real
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        progressWrapper.style.display = 'block';
        uploadFilename.textContent = `Archivo: ${file.name} (${sizeMb} MB)`;
        uploadPercent.textContent = 'Progreso de carga: 0%';
        uploadBar.style.width = '0%';
        confirmBtn.disabled = true;

        // 3. Subir vía XHR para capturar eventos de progreso
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/inspect-model', true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                uploadPercent.textContent = `Progreso de carga: ${percent}%`;
                uploadBar.style.width = `${percent}%`;
            }
        };

        xhr.onload = () => {
            if (xhr.status === 200) {
                const res = JSON.parse(xhr.responseText);
                const m = res.metrics;

                document.getElementById('meta-dimensions').textContent = m.dimensions_mm;
                document.getElementById('meta-volume').textContent = `${m.volume_cm3} cm³`;
                document.getElementById('meta-facets').textContent = m.facets;
                document.getElementById('meta-time').textContent = m.estimated_label;
                document.getElementById('meta-material').textContent = m.material;

                inspectionBadge.textContent = 'STATUS: Inspección Preliminar';
                confirmForm.action = `/confirm-order/${res.order_id}`;
                confirmBtn.disabled = false;
            } else {
                const err = JSON.parse(xhr.responseText || '{}');
                alert(err.error || 'Error al procesar el modelo en el servidor.');
            }
        };

        xhr.onerror = () => {
            alert('Error de red al intentar subir el archivo.');
        };

        xhr.send(formData);
    }
});