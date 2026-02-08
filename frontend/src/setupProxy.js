const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
    app.use(
        '/api',
        createProxyMiddleware({
            target: process.env.PROXY_TARGET || 'http://localhost:8000',
            changeOrigin: true,
        })
    );
};
