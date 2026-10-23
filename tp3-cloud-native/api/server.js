// Servicio de Envíos (versión mínima) - TP3 Arquitectura de Sistemas 2026
// Es el nodo "Servicio de Envíos" diseñado en el TP2, sin lógica de negocio ni base de datos.
// Sin dependencias externas: solo el módulo http nativo de Node.js
const http = require('http');
const os = require('os');

const PORT = process.env.PORT || 3000;
const HOSTNAME = os.hostname(); // dentro de Docker = ID corto del contenedor

function send(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
    'X-Served-By': HOSTNAME,
  });
  res.end(payload);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);

  // Endpoint clave del TP2: POST /envios/crear
  // Respeta el contrato: Idempotency-Key obligatorio (400 si falta) y responde 201.
  // No hay BD: la deduplicación real vive en la base del Servicio de Envíos (TP2).
  if (url.pathname === '/envios/crear' && req.method === 'POST') {
    if (!req.headers['idempotency-key']) {
      return send(res, 400, { codigo: 'IDEMPOTENCY_KEY_REQUIRED', mensaje: 'Falta Idempotency-Key' });
    }
    req.resume(); // descartar el cuerpo
    return req.on('end', () => send(res, 201, {
      idEnvio: 'ENV-' + Date.now() + '-' + process.pid,
      estado: 'CREADO',
      hostname: HOSTNAME,
    }));
  }

  // Health check (lo usa Docker para marcar la réplica como "healthy")
  if (url.pathname === '/health') {
    return send(res, 200, { status: 'ok', hostname: HOSTNAME });
  }

  // Carga de CPU a demanda (escenario de saturación): GET /work?n=300000
  if (url.pathname === '/work') {
    const n = Math.min(parseInt(url.searchParams.get('n') || '300000', 10), 5000000);
    let acc = 0;
    for (let i = 0; i < n; i++) acc += Math.sqrt(i) * Math.sin(i);
    return send(res, 200, { hostname: HOSTNAME, iterations: n, result: acc });
  }

  // Endpoint principal: devuelve el Hostname / ID del contenedor
  if (url.pathname === '/') {
    return send(res, 200, {
      message: 'GlobalLogistics - Servicio de Envios',
      hostname: HOSTNAME,
      pid: process.pid,
      timestamp: new Date().toISOString(),
    });
  }

  send(res, 404, { error: 'not found' });
});

server.listen(PORT, '0.0.0.0', () =>
  console.log(`API escuchando en :${PORT} - hostname=${HOSTNAME}`)
);

process.on('SIGTERM', () => server.close(() => process.exit(0)));
