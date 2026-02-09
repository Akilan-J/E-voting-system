const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
    app.use(
        ['/api', '/health', '/docs', '/redoc', '/openapi.json'],
        createProxyMiddleware({
            target: process.env.PROXY_TARGET || 'http://localhost:8000',
            changeOrigin: true,
            timeout: 300000,
            proxyTimeout: 300000
        })
    );
};
