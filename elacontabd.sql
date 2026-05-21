-- ─────────────────────────────────────────────────────────────────────────────
-- ElaConta — Schema MySQL/MariaDB
-- Sincronizado com models.py v1.0
-- ─────────────────────────────────────────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS elaconta CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE elaconta;


-- ── Usuários (contadores) ─────────────────────────────────────────────────────
CREATE TABLE usuarios (
    id         INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome       VARCHAR(255)  NOT NULL,
    email      VARCHAR(255)  NOT NULL UNIQUE,
    senha_hash VARCHAR(512)  NOT NULL,
    tipo       ENUM('contador','cliente') NOT NULL,
    ativo      TINYINT(1)    NOT NULL DEFAULT 1,
    criado_em  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_usuarios_email (email)
);


-- ── Empresas (clientes) ───────────────────────────────────────────────────────
CREATE TABLE empresas (
    id            INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    razao_social  VARCHAR(255) NOT NULL,
    nome_fantasia VARCHAR(255),
    cnpj          VARCHAR(20)  UNIQUE,
    email         VARCHAR(255) UNIQUE,
    senha_hash    VARCHAR(512) NOT NULL,
    telefone      VARCHAR(30),
    cep           VARCHAR(10),
    cidade        VARCHAR(100),
    endereco      VARCHAR(500),
    ativo         TINYINT(1)   NOT NULL DEFAULT 1,
    criado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    contador_id   INT,
    INDEX ix_empresas_cnpj  (cnpj),
    INDEX ix_empresas_email (email),
    FOREIGN KEY (contador_id) REFERENCES usuarios(id)
);


-- ── Lançamentos financeiros ───────────────────────────────────────────────────
CREATE TABLE lancamentos (
    id         INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT          NOT NULL,
    data       VARCHAR(10)  NOT NULL,
    descricao  VARCHAR(500) NOT NULL,
    categoria  VARCHAR(100) NOT NULL,
    tipo       ENUM('receita','despesa') NOT NULL,
    valor      DOUBLE       NOT NULL,
    status     ENUM('pendente','confirmado','cancelado') NOT NULL DEFAULT 'confirmado',
    origem     VARCHAR(20)  NOT NULL DEFAULT 'manual',
    observacao TEXT,
    criado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por INT,
    INDEX ix_lancamentos_empresa_id (empresa_id),
    INDEX ix_lancamentos_data       (data),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (criado_por) REFERENCES usuarios(id)
);


-- ── Contas a pagar ────────────────────────────────────────────────────────────
CREATE TABLE contas_pagar (
    id         INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT          NOT NULL,
    descricao  VARCHAR(500) NOT NULL,
    valor      DOUBLE       NOT NULL,
    vencimento VARCHAR(10)  NOT NULL,
    categoria  VARCHAR(100),
    codigo_barras   VARCHAR(200),
    arquivo_url     VARCHAR(500),
    comprovante_url VARCHAR(500),
    pago            TINYINT(1)   NOT NULL DEFAULT 0,
    recorrente      TINYINT(1)   NOT NULL DEFAULT 0,
    frequencia      VARCHAR(20),
    recorrencia_id  INT,
    criado_em       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por      INT,
    INDEX ix_contas_pagar_empresa_id (empresa_id),
    INDEX ix_contas_pagar_vencimento (vencimento),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (criado_por) REFERENCES usuarios(id)
);
