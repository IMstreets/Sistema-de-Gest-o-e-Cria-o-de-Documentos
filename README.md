Link para acesso: https://gestao-e-criacao-de-documentos-para.onrender.com/

Sistema de Gestão Fiscal e Municipal (Lotes Vagos)

Sistema web full-stack desenvolvido para otimizar e centralizar a fiscalização municipal de Lotes Vagos, automatizando a emissão de Autos de Infração e Intimações Fiscais, o controle de prazos de vistorias, o cálculo dinâmico de multas e a conformidade legal com a Lei Geral de Proteção de Dados (LGPD).

🚀 Funcionalidades Principais

Gestão Centralizada de Documentos: Emissão automatizada de Autos de Infração e Intimações Fiscais com suporte a lotes ilimitados e cálculo dinâmico de valores e penalidades.

Geração de Documentos em Lote (.docx): Integração com modelos oficiais do Word (docxtpl) para exportação instantânea preenchida com dados do contribuinte e inscrições imobiliárias.

Controle de Prazos e Vistorias Independentes: Painel de acompanhamento individual por infração (Limpeza, Fechamento e Passeio) com sincronização inteligente de datas e cálculo automático de status (Atendido, Não Atendido, Conferir, Multado, Devolvido ou Cancelado).

Automação para Correios (SIGEP): Sistema inteligente de agrupamento e robô automatizado para postagem em massa de ARs.

Dashboard Analítico Avançado: Gráficos interativos em tempo real (Chart.js) com filtros cruzados por Métrica (Quantidade de Lotes vs Documentos Emitidos), Período de Emissão, Período de Vistoria e Tipo de Documento.

Trilha de Auditoria e Conformidade (LGPD): Registro completo de logs por requisição (captura de IP, usuário logado, ação e diff de alterações antes/depois) e exclusão lógica (Soft Delete).

Populador de Demonstração (Demo Mode): Geração automática de dados fictícios para visualização imediata do portfólio caso o banco de dados esteja vazio.

🛠️ Tecnologias Utilizadas

Backend: Python, FastAPI, SQLAlchemy (ORM), SQLite, PyJWT (Tokens JWT), Bcrypt.

Frontend: HTML5, CSS3, Bootstrap 5, HTMX (Interatividade assíncrona).

Visualização de Dados: Chart.js, Chartjs Plugin Datalabels.

Processamento de Documentos: DocxTemplate, python-multipart.

⚙️ Instalação e Execução Local

Clone o repositório:

git clone https://github.com/seu-usuario/gestao-fiscal-municipal.git
cd gestao-fiscal-municipal


Crie e ative um ambiente virtual:

python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate


Instale as dependências:

pip install -r requirements.txt


Inicie a aplicação:

uvicorn main:app --reload


Acesse no navegador: http://localhost:8000

🔑 Credenciais de Acesso (Modo Demonstração)

O sistema conta com um perfil de Administrador padrão pré-configurado na primeira inicialização para testes:

CPF / Usuário: 00000000000

Senha: 123456

📄 Licença

Distribuído sob a licença MIT. Veja LICENSE para mais detalhes.
