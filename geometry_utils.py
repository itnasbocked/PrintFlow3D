import os
import trimesh

def format_hours(hours_float):
    """Convierte horas decimales a formato legible (ej. ~ 3 h 45 min)."""
    total_minutes = max(15, int(round(hours_float * 60)))
    hrs = total_minutes // 60
    mins = total_minutes % 60
    if hrs > 0:
        return f"~ {hrs} h {mins:02d} min"
    return f"~ {mins} min"

def analyze_3d_model(filepath, file_format, file_size_kb):
    """
    Analiza la malla 3D (.stl, .obj) para obtener dimensiones, volumen y tiempo estimado.
    """
    ext = file_format.lower()

    if ext in ('stl', 'obj'):
        try:
            loaded = trimesh.load(filepath, force='mesh')
            if isinstance(loaded, trimesh.Scene):
                meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
                mesh = trimesh.util.concatenate(meshes) if meshes else None
            else:
                mesh = loaded

            if mesh is not None and len(mesh.faces) > 0:
                extents = mesh.extents  # [X, Y, Z] en mm
                dim_str = f"{extents[0]:.0f} × {extents[1]:.0f} × {extents[2]:.0f} mm"

                # Volumen en mm³ -> convertir a cm³
                raw_vol = mesh.volume if mesh.is_watertight else mesh.convex_hull.volume
                volume_cm3 = round(abs(float(raw_vol)) / 1000.0, 2)
                facets = int(len(mesh.faces))

                # Heurística FDM estándar (20% relleno, boquilla 0.4mm): ~0.11 hrs/cm³ + 0.25h preparación
                est_hours = round(0.25 + (volume_cm3 * 0.11), 2)

                return {
                    'dimensions_mm': dim_str,
                    'volume_cm3': volume_cm3,
                    'facets': f"{facets:,} facetas",
                    'estimated_hours': est_hours,
                    'estimated_label': format_hours(est_hours),
                    'material': 'PLA Grado Técnico (1.75 mm)'
                }
        except Exception:
            pass

    # Respaldo para archivos .step o mallas no cerradas
    est_volume = round(max(1.5, file_size_kb * 0.015), 2)
    est_hours = round(0.35 + (est_volume * 0.11), 2)
    return {
        'dimensions_mm': 'Cad Paramétrico (Validar en taller)',
        'volume_cm3': est_volume,
        'facets': 'Geometría NURBS / Sólido',
        'estimated_hours': est_hours,
        'estimated_label': format_hours(est_hours),
        'material': 'PLA / PETG Técnico (1.75 mm)'
    }