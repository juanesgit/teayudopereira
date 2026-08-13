# Despliegue — Te Ayudo Pereira
# Servidor: 46.225.23.108 | Dominio: teayudopereira.com

---

## PASO 1 — Subir el proyecto a GitHub (desde tu PC)

```bash
cd C:\Users\juane\sigotc\pereira-alerta

git init
git add .
git commit -m "feat: Te Ayudo Pereira v1.0"

# Crea un repo en github.com (ej: github.com/TU_USUARIO/teayudopereira)
git remote add origin https://github.com/TU_USUARIO/teayudopereira.git
git branch -M main
git push -u origin main
```

---

## PASO 2 — Entrar al servidor

```bash
ssh deploy@46.225.23.108
```

---

## PASO 3 — Clonar el proyecto en el servidor

```bash
cd /home/deploy
git clone https://github.com/TU_USUARIO/teayudopereira.git teayudopereira
cd teayudopereira/backend
```

---

## PASO 4 — Crear entorno virtual e instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## PASO 5 — Configurar variables de entorno

```bash
cp .env.example .env
nano .env
```

Edita el `.env` y cambia `SECRET_KEY` por una clave segura:
```
SECRET_KEY=pon_aqui_una_clave_larga_y_aleatoria_minimo_32_caracteres
DATABASE_URL=sqlite+aiosqlite:////home/deploy/teayudopereira/backend/teayudopereira.db
```

Genera una clave segura así:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## PASO 6 — Instalar servicio systemd

```bash
sudo cp /home/deploy/teayudopereira/deploy/teayudopereira.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable teayudopereira
sudo systemctl start teayudopereira

# Verificar que está corriendo
sudo systemctl status teayudopereira
```

---

## PASO 7 — Configurar Nginx

```bash
sudo cp /home/deploy/teayudopereira/deploy/teayudopereira.nginx /etc/nginx/sites-available/teayudopereira
sudo ln -s /etc/nginx/sites-available/teayudopereira /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## PASO 8 — Instalar SSL con Certbot (HTTPS gratis)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d teayudopereira.com -d www.teayudopereira.com
```

Certbot configura el HTTPS automáticamente y renueva el certificado solo.

---

## PASO 9 — DNS en GoDaddy

Entra a **GoDaddy → Mis productos → teayudopereira.com → Administrar DNS**

Agrega o edita estos registros:

| Tipo  | Nombre | Valor           | TTL  |
|-------|--------|-----------------|------|
| A     | @      | 46.225.23.108   | 600  |
| A     | www    | 46.225.23.108   | 600  |

Espera 5-15 minutos para que propaguen y luego abre https://teayudopereira.com

---

## ACTUALIZAR en el futuro (desde tu PC)

```bash
# 1. Hacer cambios, commit y push
git add .
git commit -m "descripción del cambio"
git push origin main

# 2. En el servidor, ejecutar el script de actualización
ssh deploy@46.225.23.108
bash /home/deploy/teayudopereira/deploy/update.sh
```

---

## Verificar que todo funciona

```bash
# Estado del servicio
sudo systemctl status teayudopereira

# Logs en tiempo real
sudo journalctl -u teayudopereira -f

# Prueba local en el servidor
curl http://127.0.0.1:8002/health
```
