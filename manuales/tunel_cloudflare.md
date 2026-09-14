# Túnel de Cloudflare para pruebas de WhatsApp

1. Copiar el ejecutable portable como `tools/cloudflared.exe`.
2. Agregar esta variable al archivo `.env`:

   ```env
   APP_ENV=TEST
   ```

Al no definir `CLOUDFLARE_TUNNEL_TOKEN`, la aplicación crea un túnel rápido hacia `http://localhost:8000`. La URL `trycloudflare.com` aparece en `logs/app.log`; debe configurarse en Meta en cada inicio porque cambia.

Para una URL fija, crear un túnel nombrado, agregar `CLOUDFLARE_TUNNEL_TOKEN=token-del-tunel-nombrado` al `.env` y configurar una sola vez en Meta el callback `https://tu-hostname/webhooks/whatsapp`.

En `APP_ENV=TEST`, Max_io inicia `cloudflared.exe` al arrancar y lo detiene al cerrarse. En cualquier otro entorno no se inicia el túnel.

Para empaquetar el ejecutable de Max_io, los archivos `.spec` ya incluyen `tools/cloudflared.exe`.
