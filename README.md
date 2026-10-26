# rhTools SKP Optimizer (`v1.0.2`)

Ferramenta desktop standalone moderna para Windows focada na **otimização, limpeza geométrica profunda e separação automatizada de arquivos do Trimble SketchUp** (`.skp`), com suporte a **fila de processamento em lote (Batch Queue)**.

Projetada para fluxos de trabalho de **ArchViz, Engenharia e BIM**, permitindo reduzir o peso de arquivos complexos em até 85% e separar instantaneamente os elementos de **Arquitetura** do **Mobiliário e Vegetação**.

---

## 🚀 Download Direto
Baixe a versão compilada portátil (não requer instalação de Python nem dependências):
- 📥 **[Baixar rhTools SKP Optimizer v1.0.1 (.exe)](https://github.com/rafahaya/rhTools_SKP_Optimizer/releases/latest)**

---

## 📌 Principais Funcionalidades

### 1. Otimização & Limpeza Profunda
- **Remoção de Arestas Soltas (*Stray Edges*):** Remove automaticamente arestas isoladas e resíduos geométricos no modelo que pesam na viewport e no cálculo de sombras.
- **Purga Multi-Pass Não-Destrutiva:** Limpa recursivamente definições de componentes, blocos aninhados, camadas órfãs e materiais sem uso.
- **Redução Acentuada de Arquivo:** Reduções típicas entre 45% e 85% no tamanho do arquivo `.skp`, acelerando abertura, salvamento e exportação.

### 2. Separação Inteligente (Arquitetura vs. Mobiliário & Vegetação)
A ferramenta analisa a árvore de entidades e classifica os objetos por heurística bilingue (Português/Inglês), tags de camada, nomes de blocos e dimensões de *bounding box*:
- **`_Arquitetura.skp`:** Isola alvenarias, paredes, pisos, lajes, forros, telhados, estruturas, esquadrias, portas, janelas e vidros.
- **`_Assets.skp`:** Isola móveis soltos, aparelhos, decorações, luminárias, equipamentos de academia/crossfit/pilates e plantas/árvores/vegetação.

### 3. Fila de Processamento em Lote (*Batch Queue*)
- **Seleção Múltipla:** Adicione múltiplos arquivos `.skp` segurando <kbd>Ctrl</kbd> ou <kbd>Shift</kbd>.
- **Adicionar Pasta Inteira:** Enfileira automaticamente todos os modelos `.skp` presentes no diretório selecionado.
- **Filtro Inteligente Anti-Loop:** Ignora automaticamente arquivos derivados já criados (`_Otimizado`, `_Arquitetura`, `_Assets`).
- **Isolamento de Processo:** Cada arquivo é processado em uma instância limpa do SketchUp que é fechada ao terminar, prevenindo vazamentos de memória (*memory leaks*) e travamentos em arquivos gigantes.
- **Tabela Interativa:** Indicadores visuais de status (`⏳ Pendente`, `⚙️ Processando`, `✅ Concluído`, `❌ Erro`, `⏹ Cancelado`), tamanho e diretório. Duplo clique na linha abre a pasta no Explorer.
- **Cancelamento Seguro:** Permite interromper a fila a qualquer momento com o botão `⏹ Cancelar Fila`.

---

## 🖥️ Compatibilidade

- **Sistema Operacional:** Windows 10 e Windows 11 (64-bit).
- **SketchUp:** Suporte a detecção automática e manual para:
  - Trimble SketchUp 2026
  - Trimble SketchUp 2025
  - Trimble SketchUp 2024
  - Trimble SketchUp 2023
  - Trimble SketchUp 2022
  - Trimble SketchUp 2021
  - Trimble SketchUp 2020

---

## 🛠️ Executando a Partir do Código-Fonte

Caso prefira rodar ou modificar o projeto com Python:

```powershell
# 1. Clonar repositório
git clone https://github.com/rafahaya/rhTools_SKP_Optimizer.git
cd rhTools_SKP_Optimizer

# 2. Criar ambiente virtual
uv venv --python 3.10
# ou: python -m venv .venv

# 3. Instalar dependências
uv pip install pyinstaller pillow
# ou: .venv\Scripts\pip install pyinstaller pillow

# 4. Executar ferramenta
.venv\Scripts\python.exe main.py
```

### Compilar para Executável Standalone:
```powershell
.venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name "rhTools SKP Optimizer" --icon="app_icon.ico" --version-file="version_info.txt" main.py
```

---

## 📄 Licença
Distribuído sob a licença MIT. Parte do ecossistema de produtividade **rhTools**.
