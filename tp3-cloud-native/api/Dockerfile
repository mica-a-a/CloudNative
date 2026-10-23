# Imagen base ligera (alpine): evitamos imágenes gigantes
FROM node:20-alpine

WORKDIR /app
COPY package.json server.js ./

# Usuario no-root (buena práctica)
USER node

# Puerto interno que usa la API
EXPOSE 3000

CMD ["node", "server.js"]
