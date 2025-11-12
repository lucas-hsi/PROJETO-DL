-- Tabelas principais

CREATE TABLE IF NOT EXISTS produto (
  id SERIAL PRIMARY KEY,
  sku TEXT UNIQUE NOT NULL,
  titulo TEXT NOT NULL,
  descricao TEXT,
  preco NUMERIC(12,2) DEFAULT 0,
  estoque_atual INTEGER DEFAULT 0,
  origem TEXT DEFAULT 'LOCAL',
  status TEXT DEFAULT 'ATIVO',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sincronizacao (
  id SERIAL PRIMARY KEY,
  produto_id INTEGER NOT NULL,
  origem TEXT NOT NULL,
  destino TEXT NOT NULL,
  acao TEXT NOT NULL,
  status TEXT NOT NULL,
  mensagem TEXT,
  ts TIMESTAMP DEFAULT NOW()
);