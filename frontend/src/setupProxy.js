const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function (app) {
    app.use(
        '/api',
        createProxyMiddleware({
            target: process.env.PROXY_TARGET || 'http://backend:8000',
            changeOrigin: true,
        })
    );
};
