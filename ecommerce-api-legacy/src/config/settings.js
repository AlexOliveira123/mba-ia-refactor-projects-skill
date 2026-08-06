const config = {
  port: Number(process.env.PORT) || 3000,
  dbUser: process.env.DB_USER || 'admin_master',
  dbPass: process.env.DB_PASS || 'senha_super_secreta_prod_123',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || 'pk_live_1234567890abcdef',
  smtpUser: process.env.SMTP_USER || 'no-reply@fullcycle.com.br',
  adminToken: process.env.ADMIN_TOKEN || 'change-me-admin-token',
};

module.exports = config;
