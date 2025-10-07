-- ============================================
-- MIGRAÇÃO: Sistema de Cache de APIs
-- ============================================
-- Data: Outubro 2025
-- Descrição: Cria tabela para cache de resultados de APIs externas
-- ============================================

-- Criar tabela de cache de APIs
CREATE TABLE IF NOT EXISTS public.cache_api (
  isbn TEXT PRIMARY KEY,
  dados_json JSONB NOT NULL,
  cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Criar índice para busca por data (útil para limpeza de cache antigo)
CREATE INDEX IF NOT EXISTS idx_cache_api_cached_at 
ON public.cache_api(cached_at DESC);

-- Comentários para documentação
COMMENT ON TABLE public.cache_api IS 'Cache de resultados de APIs externas de busca de livros';
COMMENT ON COLUMN public.cache_api.isbn IS 'ISBN do livro (chave primária)';
COMMENT ON COLUMN public.cache_api.dados_json IS 'Dados completos do livro em formato JSON';
COMMENT ON COLUMN public.cache_api.cached_at IS 'Data e hora do último cache/atualização';
COMMENT ON COLUMN public.cache_api.created_at IS 'Data e hora da primeira inserção';

-- ============================================
-- OPCIONAL: Função para limpar cache antigo
-- ============================================

CREATE OR REPLACE FUNCTION limpar_cache_antigo(dias INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
  linhas_deletadas INTEGER;
BEGIN
  DELETE FROM public.cache_api
  WHERE cached_at < NOW() - (dias || ' days')::INTERVAL;
  
  GET DIAGNOSTICS linhas_deletadas = ROW_COUNT;
  RETURN linhas_deletadas;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION limpar_cache_antigo IS 'Remove entradas de cache mais antigas que X dias (padrão: 90)';

-- Exemplo de uso:
-- SELECT limpar_cache_antigo(90);  -- Remove cache > 90 dias

-- ============================================
-- INSTRUÇÕES DE USO
-- ============================================

/*
COMO EXECUTAR ESTA MIGRAÇÃO:

1. Acesse o Supabase Dashboard
2. Vá em "SQL Editor"
3. Crie uma nova query
4. Cole este SQL completo
5. Clique em "Run"
6. Verifique se a tabela foi criada em "Table Editor"

VERIFICAÇÃO:
- Tabela "cache_api" deve aparecer na lista
- Deve ter colunas: isbn, dados_json, cached_at, created_at
- Índice idx_cache_api_cached_at deve estar criado

SEGURANÇA:
- Esta migração é segura e idempotente (IF NOT EXISTS)
- Pode ser executada múltiplas vezes sem problemas
- Não afeta dados existentes em outras tabelas

MANUTENÇÃO:
- Execute limpar_cache_antigo(90) periodicamente
- Ou configure um cron job no Supabase
*/

