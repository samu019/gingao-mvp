# Gingao MVP

Plataforma compacta de generación de vídeo por IA inspirada en el flujo de trabajo Guion → Imágenes → Corte final.

## MVP
- Inicio con tarjetas de creación
- Mis proyectos
- Mis activos
- Perfil + wallet de créditos
- Proyecto con escenas
- Estimación de créditos antes de generar
- Cola Celery para render
- Adaptador GPU por implementar

## Arranque local
```bash
python -m venv .venv
# activar entorno
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Validaciones
```bash
python scripts/audit_structure.py
python scripts/validate_models.py
python scripts/validate_costs.py
```

## Próximo bloque
1. Credit reservation/refund transaccional
2. API de creación de proyectos y escenas
3. Adaptador RunPod/LTX
4. Ensamblado FFmpeg
5. UI estilo tarjetas + wizard Guion/Imágenes/Corte final
