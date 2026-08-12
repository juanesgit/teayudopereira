#!/bin/bash
# Script de actualización — ejecutar en el servidor después de cada git pull
set -e

APP_DIR="/home/deploy/teayudopereira"

echo "🔄 Actualizando Te Ayudo Pereira..."

cd $APP_DIR
git pull origin main

cd backend
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "🔁 Reiniciando servicio..."
sudo systemctl restart teayudopereira

echo "✅ Listo. Versión actualizada en producción."
