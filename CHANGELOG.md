# Changelog - rhTools SKP Optimizer

Todas as notas de versão do projeto rhTools SKP Optimizer.

---

## [v1.0.2] - 26/10/2026

### Alterado
- **Nome do Arquivo de Saída**: O sufixo de salvamento de Mobiliário e Vegetação foi atualizado de `_Mobiliario_Vegetacao.skp` para **`_Assets.skp`** (ex: `Modelo_Assets.skp`).
- **Filtro Anti-Loop**: Atualizado para reconhecer e filtrar automaticamente arquivos com o sufixo `_Assets.skp`.
- **Interface Gráfica**: Atualizado o texto da opção na etapa 3 para exibir `_Assets.skp`.

---

## [v1.0.1] - 26/10/2026

### Adicionado
- **Fila de Processamento em Lote (Batch Queue)**:
  - Capacidade de selecionar e processar múltiplos arquivos `.skp` sequencialmente.
  - Botão `+ Adicionar Arquivo(s)...` com seleção múltipla (<kbd>Ctrl</kbd> e <kbd>Shift</kbd>).
  - Botão `+ Adicionar Pasta...` para varredura e enfileiramento automático de diretórios inteiros.
- **Filtro Automático de Saídas**:
  - Detecção inteligente para ignorar automaticamente arquivos previamente gerados (`_Otimizado.skp`, `_Arquitetura.skp`, `_Assets.skp`).
- **Gerenciador de Fila**:
  - Tabela com colunas de índice (`#`), status visual (`⏳ Pendente`, `⚙️ Processando`, `✅ Concluído`, `❌ Erro`, `⏹ Cancelado`), nome do modelo, tamanho formatado e diretório.
  - Opções para remover arquivos específicos (<kbd>Del</kbd> ou botão) e limpar fila completa.
  - Duplo-clique em qualquer linha para abrir a pasta correspondente no Windows Explorer.
  - Barra dupla de progresso: Progresso Geral da Fila e Progresso do Arquivo Atual.
  - Botão `⏹ Cancelar Fila` seguro durante a execução.
- **Identidade e Metadados**:
  - Exibição da versão na barra de títulos da janela e badge estilizado no cabeçalho.
  - Metadados de versão do Windows PE (`FileVersion`, `ProductVersion`, `Company: rhTools`) embutidos no `.exe`.

---

## [v1.0.0] - 26/10/2026

### Adicionado
- Versão inicial do pipeline de automação para SketchUp.
- Purga completa de definições não utilizadas e camadas órfãs.
- Remoção de arestas soltas (stray edges) do espaço modelo.
- Separação automatizada de Arquitetura (`_Arquitetura.skp`) e Mobiliário/Vegetação com heurística bilingue (PT-BR / EN) e bounding box.
- Identidade visual rhTools com suporte a logo transparente e tema Dark Slate.
