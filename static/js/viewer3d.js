class PrintFlowViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x141414);

        const width = this.container.clientWidth || 400;
        const height = this.container.clientHeight || 340;

        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2000);
        this.camera.position.set(120, 100, 120);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.container.innerHTML = '';
        this.container.appendChild(this.renderer.domElement);

        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.autoRotate = false;
        this.controls.autoRotateSpeed = 2.0;

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
        this.scene.add(ambientLight);

        const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.75);
        dirLight1.position.set(100, 150, 100);
        this.scene.add(dirLight1);

        const dirLight2 = new THREE.DirectionalLight(0xd94e34, 0.35);
        dirLight2.position.set(-100, -50, -100);
        this.scene.add(dirLight2);

        const grid = new THREE.GridHelper(220, 22, 0x555555, 0x2a2a2a);
        this.scene.add(grid);

        this.currentMesh = null;
        this.initialCameraPos = this.camera.position.clone();

        window.addEventListener('resize', () => this.onResize());
        this.animate();
    }

    clearModel() {
        if (this.currentMesh) {
            this.scene.remove(this.currentMesh);
            this.currentMesh = null;
        }
    }

    normalizeAndCenter(object3D, applyCadZUpFix = true) {
        // 1. Convertir eje Z-arriba (estándar CAD/STL) a Y-arriba (Three.js)
        if (applyCadZUpFix) {
            object3D.traverse((child) => {
                if ((child.isMesh || child.isLine) && child.geometry) {
                    child.geometry.rotateX(-Math.PI / 2);
                    child.geometry.computeBoundingBox();
                }
            });
        }

        // 2. Calcular dimensiones reales tras corregir orientación
        const box = new THREE.Box3().setFromObject(object3D);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z) || 1;
        const scale = 90 / maxDim;

        // 3. Hornear traslación y escala en los vértices: centro X/Z en 0 y base en Y=0
        object3D.traverse((child) => {
            if ((child.isMesh || child.isLine) && child.geometry) {
                child.geometry.translate(-center.x, -box.min.y, -center.z);
                child.geometry.scale(scale, scale, scale);
                if (child.isMesh) {
                    child.geometry.computeVertexNormals();
                }
                child.geometry.computeBoundingBox();
                child.geometry.computeBoundingSphere();
            }
        });

        // 4. Garantizar origen y rotación locales estrictamente en 0
        object3D.position.set(0, 0, 0);
        object3D.rotation.set(0, 0, 0);
        object3D.scale.set(1, 1, 1);

        this.scene.add(object3D);
        this.currentMesh = object3D;

        const finalBox = new THREE.Box3().setFromObject(object3D);
        this.controls.target.set(0, finalBox.max.y / 2, 0);
        this.camera.position.set(110, 90, 110);
        this.initialCameraPos = this.camera.position.clone();
        this.controls.update();
    }

    // Permite girar 90° en X si un modelo ya venía exportado con Y-arriba (ej. Blender)
    rotate90X() {
        if (!this.currentMesh) return;
        this.currentMesh.traverse((child) => {
            if ((child.isMesh || child.isLine) && child.geometry) {
                child.geometry.rotateX(Math.PI / 2);
                child.geometry.computeBoundingBox();
            }
        });

        const box = new THREE.Box3().setFromObject(this.currentMesh);
        const center = box.getCenter(new THREE.Vector3());

        this.currentMesh.traverse((child) => {
            if ((child.isMesh || child.isLine) && child.geometry) {
                child.geometry.translate(-center.x, -box.min.y, -center.z);
                child.geometry.computeBoundingBox();
                child.geometry.computeBoundingSphere();
            }
        });

        this.currentMesh.position.set(0, 0, 0);
        this.currentMesh.rotation.set(0, 0, 0);
        const finalBox = new THREE.Box3().setFromObject(this.currentMesh);
        this.controls.target.set(0, finalBox.max.y / 2, 0);
        this.controls.update();
    }

    loadFromUrl(url, ext, onDone) {
        const format = ext.toLowerCase();
        this.clearModel();

        const material = new THREE.MeshStandardMaterial({
            color: 0xe6dfd3,
            roughness: 0.45,
            metalness: 0.1
        });

        if (format === 'stl') {
            new THREE.STLLoader().load(url, (geometry) => {
                const mesh = new THREE.Mesh(geometry, material);
                this.normalizeAndCenter(mesh, true);
                if (onDone) onDone('WebGL Activo');
            });
        } else if (format === 'obj') {
            new THREE.OBJLoader().load(url, (group) => {
                group.traverse((child) => {
                    if (child.isMesh) child.material = material;
                });
                this.normalizeAndCenter(group, true);
                if (onDone) onDone('WebGL Activo');
            });
        } else {
            const geo = new THREE.BoxGeometry(50, 50, 50);
            const wire = new THREE.WireframeGeometry(geo);
            const line = new THREE.LineSegments(wire, new THREE.LineBasicMaterial({ color: 0xd94e34 }));
            this.normalizeAndCenter(line, false);
            if (onDone) onDone('CAD Paramétrico (.STEP)');
        }
    }

    loadLocalFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const url = URL.createObjectURL(file);
        const statusEl = document.getElementById('webgl-status');

        this.loadFromUrl(url, ext, (label) => {
            if (statusEl) {
                statusEl.textContent = label;
                statusEl.style.color = ext === 'step' ? '#e0a800' : '#4caf50';
            }
            URL.revokeObjectURL(url);
        });
    }

    toggleAutoRotate() {
        this.controls.autoRotate = !this.controls.autoRotate;
    }

    zoom(factor) {
        this.camera.position.multiplyScalar(factor);
        this.controls.update();
    }

    resetView() {
        this.controls.autoRotate = false;
        this.camera.position.copy(this.initialCameraPos);
        const height = this.currentMesh ? new THREE.Box3().setFromObject(this.currentMesh).max.y / 2 : 15;
        this.controls.target.set(0, height, 0);
        this.controls.update();
    }

    onResize() {
        if (!this.container) return;
        const width = this.container.clientWidth || 400;
        const height = this.container.clientHeight || 340;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}