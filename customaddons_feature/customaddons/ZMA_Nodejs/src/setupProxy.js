const {createProxyMiddleware} = require("http-proxy-middleware")

module.exports = app => {
    app.use(
      createProxyMiddleware('/zalo_mini_app/point_exchange_history',{
        target: 'https://e83d-2001-ee0-4a48-dcd0-4e92-2599-3e4e-2e2b.ngrok-free.app',
        changeOrigin: true
      })
    )
}