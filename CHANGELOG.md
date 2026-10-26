# Changelog - rhTools SKP Optimizer

Todas as notas de versão do projeto rhTools SKP Optimizer.

---

## [v1.0.1] - 26/10/2026

### Adicionado
- **Fila de Processamento em Lote (Batch Queue)**:
  - Capacidade de selecionar e processar múltiplos arquivos `.skp` sequencialmente.
  - Botão `+ Adicionar Arquivo(s)...` com seleção múltipla (<kbd>Ctrl</kbd> e <kbd>Shift</kbd>).
  - Botão `+ Adicionar Pasta...` para varredura e enfileiramento automático de diretórios inteiros.
- **Filtro Automático de Saídas**:
  - Detecção inteligente para ignorar automaticamente arquivos previamente gerados (`_Otimizado.skp`, `_Arquitetura.skp`, `_Mobiliario_Vegetacao.skp`).
- **Gerenciador de Fila**:
  - Tabela com colunas de índice (`#`), status visual (`⏳ Pendente`, `⚙️ Processando`, `✅ Concluído`, `❌ Erro`, `⏹ Cancelado`), nome do modelo, tamanho formatado e diretório.
  - Opções para remover arquivos específicos (<kbd>Del</kbd> ou botão) e limpar fila completa.
  - Duplo-clique em qualquer linha para abrir a pasta correspondente no Windows Explorer.
  - Barra dupla de progresso: Progresso Geral da Fila e Progresso do Arquivo Atual.
  - Botão `⏹ Cancelar Fila` seguro durante a execução.
- **Identidade e Metadados**:
  - Exibição da versão `v1.0.1` na barra de títulos da janela e badge estilizado no cabeçalho.
  - Metadados de versão do Windows PE (`FileVersion: 1.0.1.0`, `ProductVersion: 1.0.1.0`, `Company: rhTools`) embutidos no `.exe`.
- **Organização de Releases**:
  - Estrutura de pastas `release/v1.0.1/` e `dist/v1.0.1/`.

### Corrigido & Aprimorado
- **Isolamento de Memória**: Encerramento forçado e recriação do SketchUp a cada modelo para evitar vazamento de memória em arquivos pesados.
- **Tratamento de Erros no Ruby**: Saída e encerramento limpo do SketchUp em caso de falha de parsing para não travar os próximos arquivos da fila.

---

## [v1.0.0] - 26/10/2026

### Adicionado
- Versão inicial do pipeline de automação para SketchUp.
- Purga completa de definições não utilizadas e camadas órfãs.
- Remoção de arestas soltas (stray edges) do espaço modelo.
- Separação automatizada de Arquitetura (`_Arquitetura.skp`) e Mobiliário/Vegetação (`_Mobiliario_Vegetacao.skp`) com heurística bilingue (PT-BR / EN) e bounding box.
- Identidade visual rhTools com suporte a logo transparente e tema Dark Slate.
