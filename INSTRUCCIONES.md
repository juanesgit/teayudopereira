# Pereira Alerta — Instrucciones de arranque

## Requisitos
- Python 3.11+
- Node.js 18+
- (opcional) Docker y Docker Compose

---

## Opción 1 — Sin Docker (recomendado para desarrollo)

### Backend (FastAPI)

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate       # Mac/Linux
# venv\Scripts\activate        # Windows

# Instalar dependencias
pip install -r requirements.txt

# Copiar variables de entorno
cp .env.example .env

# Correr el servidor
uvicorn app.main:app --reload --port 8000
```

El backend queda en: http://localhost:8000
Documentación automática: http://localhost:8000/docs

---

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

La app queda en: http://localhost:5173

---

## Opción 2 — Con Docker

```bash
docker-compose up --build
```

---

## Flujo de uso

1. **Víctima**: abre el mapa en `/`, ve el botón "Pedir ayuda", llena el formulario y marca su ubicación. No necesita cuenta.

2. **Voluntario**: se registra en `/login` con rol "voluntario", queda visible en la lista de voluntarios.

3. **Coordinador**: se registra como "coordinador", accede al panel `/panel` donde puede:
   - Ver todos los reportes y actualizar su estado (tomar caso / marcar resuelto)
   - Registrar puntos de ayuda (albergues, brigadas médicas, puntos de agua)
   - Dibujar zonas de peligro en el mapa con círculos de radio ajustable

---

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /auth/register | Registro de usuario |
| POST | /auth/login | Login (devuelve JWT) |
| GET | /reports/ | Lista reportes (filtrable) |
| POST | /reports/ | Crear reporte (sin auth) |
| PATCH | /reports/{id} | Actualizar estado |
| GET | /aid-points/ | Lista puntos de ayuda |
| POST | /aid-points/ | Crear punto (requiere auth) |
| GET | /danger-zones/ | Lista zonas de peligro |
| POST | /danger-zones/ | Crear zona (requiere auth) |
| GET | /users/volunteers | Lista voluntarios |

---

## Siguiente paso sugerido
- Agregar WebSockets para que el mapa se actualice en tiempo real sin recargar
- Enviar SMS via Twilio cuando se crea un reporte de rescate
- Migrar de SQLite a PostgreSQL para producción
