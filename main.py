from fastapi import FastAPI, Request, Form, Depends, Cookie, Body
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, or_, cast
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from docxtpl import DocxTemplate
from datetime import datetime, timedelta
from urllib.parse import quote
import bcrypt
import jwt
import sqlite3
import io
import os
import uvicorn
import json
import re


SECRET_KEY = "chave_super_secreta_prefeitura_2026"
ALGORITHM = "HS256"


SQLALCHEMY_DATABASE_URL = "sqlite:///./dados.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Registro(Base):
    __tablename__ = "registros"
    id = Column(Integer, primary_key=True, index=True)
    numero_documento = Column(Integer)
    tipo = Column(String(50), default="Auto")
    inciso = Column(String(50))
    nome = Column(String(255), index=True)
    cpf = Column(String(20))
    data = Column(String(20))
    
    protocolo_denuncia = Column(String(100))
    
    numero_intimacao_fiscal = Column(String(50))
    dia_intimacao = Column(String(10))
    mes_intimacao = Column(String(20))
    ano_intimacao = Column(String(10))
    
    logradouro_proprietario = Column(String(255))
    numero_proprietario = Column(String(50))
    complemento_proprietario = Column(String(255))
    bairro_proprietario = Column(String(100))
    cidade_proprietario = Column(String(100), default="Montes Claros - MG")
    cep_proprietario = Column(String(20))
    
    tem_responsavel = Column(Boolean, default=False)
    nome_responsavel = Column(String(255))
    cpf_responsavel = Column(String(20))
    tipo_responsavel = Column(String, default="A/C")
    
    imoveis = Column(Text, default="[]")
    detalhes = Column(Text)

    status_documento = Column(String(50), default="Aguardando AR")
    status_limpeza = Column(String, nullable=True)
    status_fechamento = Column(String, nullable=True)
    status_passeio = Column(String, nullable=True)
    data_conferencia_limpeza = Column(String(20))
    data_conferencia_fechamento = Column(String(20))
    data_conferencia_passeio = Column(String(20))
    
    data_vistoria_limpeza = Column(String(20))
    data_vistoria_fechamento = Column(String(20))
    data_vistoria_passeio = Column(String(20))
    
    data_conferido = Column(String(20))
    observacoes_status = Column(Text)
    mes_multa = Column(String(20))
    ano_multa = Column(String(10))
    multa_limpeza = Column(Boolean, default=False)
    multa_fechamento = Column(Boolean, default=False)
    multa_passeio = Column(Boolean, default=False)
    ar_devolvido = Column(String(50), nullable=True)
    motivo_devolucao = Column(Text, nullable=True)
    novo_numero_refeito = Column(String(50), nullable=True)
    cancelado = Column(String(50), nullable=True)
    motivo_cancelamento = Column(Text, nullable=True)
    novo_numero_cancelado = Column(String(50), nullable=True)
    
    criado_por = Column(String(100), default="Desconhecido")
    excluido = Column(Boolean, default=False)

    @property
    def inciso_select(self):
        if not self.inciso: return ""
        t = str(self.inciso).upper()
        
        padroes = {"LIMPEZA": "i", "I": "i", "III": "iii", "IV": "iv", "I III": "i iii", "I IV": "i iv", "III IV": "iii iv", "I III IV": "i iii iv"}
        if t in padroes: return padroes[t]
        
        tem_i = "LIMPEZA" in t or re.search(r'\bI\b', t)
        tem_iii = "FECHAMENTO" in t or re.search(r'\bIII\b', t)
        tem_iv = "PASSEIO" in t or re.search(r'\bIV\b', t)
        
        if tem_i and tem_iii and tem_iv: return "i iii iv"
        if tem_i and tem_iii: return "i iii"
        if tem_i and tem_iv: return "i iv"
        if tem_iii and tem_iv: return "iii iv"
        if tem_i: return "i"
        if tem_iii: return "iii"
        if tem_iv: return "iv"
        
        return self.inciso

    @property
    def inciso_amigavel(self):
        mapa = {
            "i": "Limpeza", 
            "iii": "Fechamento", 
            "iv": "Passeio",
            "i iii": "Limpeza e Fechamento", 
            "i iv": "Limpeza e Passeio",
            "iii iv": "Fechamento e Passeio", 
            "i iii iv": "Limpeza, Fechamento e Passeio"
        }
        return mapa.get(self.inciso_select, self.inciso)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    senha_hash = Column(String(255))
    nome_completo = Column(String(100))

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"
    id = Column(Integer, primary_key=True, index=True)
    data_hora = Column(String(30), index=True)
    usuario_cpf = Column(String(50), index=True)
    usuario_nome = Column(String(100))
    ip = Column(String(50))
    acao = Column(String(50), index=True) # CRIAR, EDITAR, STATUS, EXCLUIR, LOGIN, EXPORTAR
    registro_id = Column(Integer, nullable=True, index=True)
    detalhes = Column(Text)

Base.metadata.create_all(bind=engine)



try:
    conn = sqlite3.connect("./dados.db")
    cursor = conn.cursor()
    colunas_novas = [
        "status_documento VARCHAR(50) DEFAULT 'Aguardando AR'",
        "data_conferencia_limpeza VARCHAR(20)",
        "data_conferencia_fechamento VARCHAR(20)",
        "data_conferencia_passeio VARCHAR(20)",
        "data_vistoria_limpeza VARCHAR(20)",
        "data_vistoria_fechamento VARCHAR(20)",
        "data_vistoria_passeio VARCHAR(20)",
        "data_conferido VARCHAR(20)",
        "observacoes_status TEXT",
        "status_limpeza VARCHAR",
        "status_fechamento VARCHAR",
        "status_passeio VARCHAR",
        "tipo_responsavel VARCHAR DEFAULT 'A/C'",
        "protocolo_denuncia VARCHAR(100)",
        "mes_multa VARCHAR(20)",
        "ano_multa VARCHAR(10)",
        "multa_limpeza BOOLEAN DEFAULT 0",
        "multa_fechamento BOOLEAN DEFAULT 0",
        "multa_passeio BOOLEAN DEFAULT 0",
        "ar_devolvido VARCHAR(50)",
        "motivo_devolucao TEXT",
        "novo_numero_refeito VARCHAR(50)",
        "cancelado VARCHAR(50)",
        "motivo_cancelamento TEXT",
        "novo_numero_cancelado VARCHAR(50)",
        "criado_por VARCHAR(100)",
        "excluido BOOLEAN DEFAULT 0"
    ]
    for col in colunas_novas:
        try:
            cursor.execute(f"ALTER TABLE registros ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
            
    # ========================================================
    # LIMPEZA AUTOMÁTICA DO CEP DA SECRETARIA
    # ========================================================
    cursor.execute("UPDATE registros SET cep_proprietario = '' WHERE cep_proprietario = '39400-218' OR cep_proprietario = '39400218'")
    # ========================================================

    # ========================================================
    # CORREÇÃO DE ACENTOS NO JSON DOS IMÓVEIS (CONVERTE PARA UTF-8)
    # ========================================================
    cursor.execute("SELECT id, imoveis FROM registros WHERE imoveis LIKE '%\\u%'")
    for row in cursor.fetchall():
        try:
            dados = json.loads(row[1])
            novo_json = json.dumps(dados, ensure_ascii=False)
            cursor.execute("UPDATE registros SET imoveis = ? WHERE id = ?", (novo_json, row[0]))
        except Exception:
            pass
    # ========================================================

    conn.commit()
    conn.close()
except Exception as e:
    print(f"Aviso de banco de dados: {e}")

db_setup = SessionLocal()
if not db_setup.query(Usuario).first():
    senha_codificada = bcrypt.hashpw("123456".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin = Usuario(username="00000000000", senha_hash=senha_codificada, nome_completo="Visitante (Portfólio)")
    db_setup.add(admin)
    db_setup.commit()

# Popula dados fictícios caso o banco esteja vazio (Ideal para Portfólio)
if not db_setup.query(Registro).first():
    exemplos = [
        Registro(
            numero_documento=101, tipo="Intimação", inciso="i iii", nome="JOÃO DA SILVA (DADO FICTÍCIO)",
            cpf="111.222.333-44", data="15/10/2026", status_documento="Conferido - Atendido",
            status_limpeza="Atendido", status_fechamento="Atendido",
            data_vistoria_limpeza="2026-10-25", data_vistoria_fechamento="2026-10-25",
            imoveis=json.dumps({"endereco_completo": "RUA DAS FLORES, S/N", "bairro": "CENTRO", "quadra": "10", "lotes": [{"inscricao": "01.02.003.0004.001", "numero": "12"}]}),
            criado_por="Sistema Demo"
        ),
        Registro(
            numero_documento=102, tipo="Intimação", inciso="i", nome="CONSTRUTORA EXEMPLO LTDA",
            cpf="12.345.678/0001-99", data="18/10/2026", status_documento="Auto 50/26",
            status_limpeza="Não Atendido", data_vistoria_limpeza="2026-10-28",
            imoveis=json.dumps({"endereco_completo": "AV. BRASIL", "bairro": "JARDIM PANORAMA", "quadra": "04", "lotes": [{"inscricao": "02.03.004.0005.001", "numero": "01"}, {"inscricao": "02.03.004.0006.001", "numero": "02"}]}),
            criado_por="Sistema Demo"
        ),
        Registro(
            numero_documento=50, tipo="Auto", inciso="i", nome="CONSTRUTORA EXEMPLO LTDA",
            cpf="12.345.678/0001-99", data="02/11/2026", numero_intimacao_fiscal="102/26",
            dia_intimacao="18", mes_intimacao="OUTUBRO", ano_intimacao="2026",
            status_documento="MULTADO", status_limpeza="Não Atendido", data_vistoria_limpeza="2026-11-08",
            mes_multa="Novembro", ano_multa="2026", multa_limpeza=True,
            imoveis=json.dumps({"endereco_completo": "AV. BRASIL", "bairro": "JARDIM PANORAMA", "quadra": "04", "lotes": [{"inscricao": "02.03.004.0005.001", "numero": "01"}, {"inscricao": "02.03.004.0006.001", "numero": "02"}]}),
            criado_por="Sistema Demo"
        )
    ]
    db_setup.add_all(exemplos)
    db_setup.commit()
db_setup.close()
    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
SENHA_EDICAO = "123456"

def obter_usuario_logado(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("auth_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return db.query(Usuario).filter(Usuario.username == username).first()
    except:
        return None

def checar_auth(usuario: Usuario = Depends(obter_usuario_logado)):
    return usuario

def registrar_log(db: Session, request: Request, usuario: Usuario, acao: str, registro_id: int = None, detalhes: str = ""):
    ip_cliente = request.headers.get("X-Forwarded-For") or (request.client.host if request.client else "Desconhecido")
    novo_log = LogAuditoria(
        data_hora=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        usuario_cpf=usuario.username if usuario else "Anonimo",
        usuario_nome=usuario.nome_completo if usuario else "Anônimo / Sistema",
        ip=ip_cliente,
        acao=acao,
        registro_id=registro_id,
        detalhes=detalhes
    )
    db.add(novo_log)

def extrair_snapshot(reg: Registro) -> dict:
    """Fotografa o estado atual do registro para comparar antes e depois da edição."""
    campos = [
        "numero_documento", "tipo", "inciso", "nome", "cpf", "data", "protocolo_denuncia",
        "numero_intimacao_fiscal", "dia_intimacao", "mes_intimacao", "ano_intimacao",
        "logradouro_proprietario", "numero_proprietario", "complemento_proprietario",
        "bairro_proprietario", "cidade_proprietario", "cep_proprietario",
        "tem_responsavel", "nome_responsavel", "cpf_responsavel", "tipo_responsavel",
        "imoveis", "status_documento", "status_limpeza", "status_fechamento", "status_passeio",
        "data_conferencia_limpeza", "data_conferencia_fechamento", "data_conferencia_passeio",
        "data_vistoria_limpeza", "data_vistoria_fechamento", "data_vistoria_passeio",
        "observacoes_status", "mes_multa", "ano_multa", "multa_limpeza", "multa_fechamento",
        "multa_passeio", "ar_devolvido", "motivo_devolucao", "novo_numero_refeito", "excluido"
    ]
    return {c: getattr(reg, c) for c in campos}

def calcular_diff(antes: dict, depois: dict) -> str:
    """Retorna um JSON apenas com os campos que foram alterados."""
    alteracoes = {}
    for k, v_antes in antes.items():
        v_depois = depois.get(k)
        if str(v_antes or "") != str(v_depois or ""):
            alteracoes[k] = {"antes": v_antes, "depois": v_depois}
    return json.dumps(alteracoes, ensure_ascii=False) if alteracoes else "Sem alterações de valores"

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    cpf_limpo = re.sub(r'\D', '', username)
    user = db.query(Usuario).filter(Usuario.username == cpf_limpo).first()

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.senha_hash.encode('utf-8')):
        registrar_log(db, request, None, "LOGIN_FALHA", detalhes=f"Tentativa falha para CPF: {cpf_limpo}")
        db.commit()
        return HTMLResponse("Credenciais Inválidas", status_code=401)
    
    registrar_log(db, request, user, "LOGIN_SUCESSO", detalhes="Sessão iniciada")
    db.commit()

    expire = datetime.utcnow() + timedelta(days=7)
    token = jwt.encode({"sub": user.username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    
    resposta = HTMLResponse("OK")
    resposta.set_cookie(key="auth_token", value=token, httponly=True, secure=True)
    return resposta

@app.post("/logout", response_class=HTMLResponse)
def logout():
    resposta = HTMLResponse("OK")
    # O servidor é quem apaga o cookie blindado
    resposta.delete_cookie("auth_token", httponly=True, secure=True)
    return resposta

@app.get("/", response_class=HTMLResponse)
def index(request: Request, busca: str = "", busca_endereco: str = "", filtro_inciso: str = "", data_inicio: str = "", data_fim: str = "", vistoria_inicio: str = "", vistoria_fim: str = "", filtro_status: str = "", ano_base: str = "", db: Session = Depends(get_db), auth = Depends(checar_auth)):
    
    # 1. Define o Ano de Exercício (Padrão: ano atual do PC)
    if not ano_base:
        ano_base = str(datetime.now().year)

    # 2. Isola TODO o sistema (Gráficos e Tabelas) apenas para o ano selecionado
    filtro_ativos = or_(Registro.excluido == False, Registro.excluido == None)
    q_autos = db.query(Registro).filter(filtro_ativos, Registro.tipo == "Auto", Registro.data.like(f"%/{ano_base}"))
    q_int = db.query(Registro).filter(filtro_ativos, Registro.tipo == "Intimação", Registro.data.like(f"%/{ano_base}"))

    # ... (mantenha os filtros de busca existentes aqui no meio) ...
    
    if busca:
        busca_limpa = busca.strip()

        busca_curinga = re.sub(r'[aáàãâäeéèêëiíìîïoóòõôöuúùûücç]', '_', busca_limpa, flags=re.IGNORECASE)
        
        filtro_txt = or_(
            cast(Registro.numero_documento, String).ilike(f"%{busca_limpa}%"),
            Registro.nome.ilike(f"%{busca_curinga}%") 
        )
        q_autos = q_autos.filter(filtro_txt)
        q_int = q_int.filter(filtro_txt)
        
    if busca_endereco:
        b_end_limpo = busca_endereco.strip()
        b_end_curinga = re.sub(r'[aáàãâäeéèêëiíìîïoóòõôöuúùûücç]', '_', b_end_limpo, flags=re.IGNORECASE)
        
        q_autos = q_autos.filter(Registro.imoveis.ilike(f"%{b_end_curinga}%")) 
        q_int = q_int.filter(Registro.imoveis.ilike(f"%{b_end_curinga}%"))     
        
            
    # Filtro de Status Geral no banco (apenas quando não for filtro individual por infração)
    if filtro_status and not filtro_status.startswith(("L_", "F_", "P_")):
        if filtro_status == "Aguardando AR":
            filtro_condicao = or_(
                Registro.status_documento == "Aguardando AR",
                Registro.status_documento == None,
                Registro.status_documento == ""
            )
            q_autos = q_autos.filter(filtro_condicao)
            q_int = q_int.filter(filtro_condicao)
        elif filtro_status == "Conferido - Não Atendido":
            filtro_condicao = or_(
                Registro.status_documento == "Conferido - Não Atendido",
                Registro.status_documento == "MULTADO",
                Registro.status_documento.like("Auto %")
            )
            q_autos = q_autos.filter(filtro_condicao)
            q_int = q_int.filter(filtro_condicao)
        elif filtro_status == "Virou Auto":
            q_autos = q_autos.filter(Registro.status_documento.like("Auto %"))
            q_int = q_int.filter(Registro.status_documento.like("Auto %"))
        elif filtro_status == "Multados":
            q_autos = q_autos.filter(Registro.status_documento == "MULTADO")
            q_int = q_int.filter(Registro.status_documento == "MULTADO")
        elif filtro_status == "Devolvido/Refeito":
            q_autos = q_autos.filter(Registro.status_documento.like("DEVOLVIDO - REFEITO%"))
            q_int = q_int.filter(Registro.status_documento.like("DEVOLVIDO - REFEITO%"))
        elif filtro_status == "Devolvido/Não Refeito":
            q_autos = q_autos.filter(Registro.status_documento == "DEVOLVIDO - NÃO REFEITO")
            q_int = q_int.filter(Registro.status_documento == "DEVOLVIDO - NÃO REFEITO")
        elif filtro_status == "Cancelado/Refeito":
            q_autos = q_autos.filter(Registro.status_documento.like("CANCELADO - REFEITO%"))
            q_int = q_int.filter(Registro.status_documento.like("CANCELADO - REFEITO%"))
        elif filtro_status == "Cancelado/Não Refeito":
            q_autos = q_autos.filter(Registro.status_documento == "CANCELADO - NÃO REFEITO")
            q_int = q_int.filter(Registro.status_documento == "CANCELADO - NÃO REFEITO")
        else:
            q_autos = q_autos.filter(Registro.status_documento == filtro_status)
            q_int = q_int.filter(Registro.status_documento == filtro_status)
        
    autos = q_autos.order_by(Registro.numero_documento.desc()).all()
    intimacoes = q_int.order_by(Registro.numero_documento.desc()).all()

    # 1. Filtro de Infração (Suporta busca exata ou "Contém")
    if filtro_inciso:
        if filtro_inciso.startswith("contem_"):
            alvo_inc = filtro_inciso.replace("contem_", "")
            autos = [a for a in autos if alvo_inc in a.inciso_select.split()]
            intimacoes = [i for i in intimacoes if alvo_inc in i.inciso_select.split()]
        else:
            autos = [a for a in autos if a.inciso_select == filtro_inciso]
            intimacoes = [i for i in intimacoes if i.inciso_select == filtro_inciso]

    # 2. Função que avalia o status real de cada infração (Limpeza, Fechamento, Passeio)
    def status_infracao_individual(reg, chave):
        inf_upper = str(reg.inciso_amigavel).upper() if reg.inciso_amigavel else ""
        if chave == "L" and "LIMPEZA" not in inf_upper: return None
        if chave == "F" and "FECHAMENTO" not in inf_upper: return None
        if chave == "P" and "PASSEIO" not in inf_upper: return None

        st_geral = str(reg.status_documento) if reg.status_documento else ""
        if "DEVOLVIDO" in st_geral or "CANCELADO" in st_geral:
            return "INVALIDO"

        st_ind = reg.status_limpeza if chave == "L" else (reg.status_fechamento if chave == "F" else reg.status_passeio)
        if st_ind == "Atendido": return "ATENDIDO"
        if st_ind == "Não Atendido": return "NAO_ATENDIDO"

        # Fallback para registros antigos sem marcação individual
        if st_geral == "Conferido - Atendido": return "ATENDIDO"
        if st_geral in ["Conferido - Não Atendido", "MULTADO"] or st_geral.startswith("Auto"):
            return "NAO_ATENDIDO"
        return "PENDENTE"

    # 3. Aplica o Filtro de Status Individual por Infração (ex: L_ATENDIDO)
    infracao_foco = None
    if filtro_status and filtro_status.startswith(("L_", "F_", "P_")):
        infracao_foco, estado_alvo = filtro_status.split("_", 1)
        autos = [a for a in autos if status_infracao_individual(a, infracao_foco) == estado_alvo]
        intimacoes = [i for i in intimacoes if status_infracao_individual(i, infracao_foco) == estado_alvo]

    # 4. Filtro por Período de Emissão
    if data_inicio or data_fim:
        def dentro_do_periodo_emissao(data_br):
            if not data_br: return False
            partes = str(data_br).strip().split('/')
            if len(partes) != 3: return False
            data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
            if data_inicio and data_iso < data_inicio: return False
            if data_fim and data_iso > data_fim: return False
            return True

        autos = [a for a in autos if dentro_do_periodo_emissao(a.data)]
        intimacoes = [i for i in intimacoes if dentro_do_periodo_emissao(i.data)]

    # 5. Filtro por Período de Vistoria (Isola a data da infração filtrada, se houver)
    if vistoria_inicio or vistoria_fim:
        def normalizar_iso(d_str):
            if not d_str: return None
            s = str(d_str).strip()
            if len(s.split('-')) == 3: return s
            if len(s.split('/')) == 3:
                p = s.split('/')
                return f"{p[2]}-{p[1]}-{p[0]}"
            return None

        def dentro_do_periodo_vistoria(reg):
            if infracao_foco == "L" or filtro_inciso in ["i", "contem_i"]:
                datas_v = [normalizar_iso(reg.data_vistoria_limpeza)]
            elif infracao_foco == "F" or filtro_inciso in ["iii", "contem_iii"]:
                datas_v = [normalizar_iso(reg.data_vistoria_fechamento)]
            elif infracao_foco == "P" or filtro_inciso in ["iv", "contem_iv"]:
                datas_v = [normalizar_iso(reg.data_vistoria_passeio)]
            else:
                datas_v = [
                    normalizar_iso(reg.data_vistoria_limpeza),
                    normalizar_iso(reg.data_vistoria_fechamento),
                    normalizar_iso(reg.data_vistoria_passeio)
                ]
            datas_validas = [d for d in datas_v if d]
            if not datas_validas:
                return False
            for d in datas_validas:
                if (not vistoria_inicio or d >= vistoria_inicio) and (not vistoria_fim or d <= vistoria_fim):
                    return True
            return False

        autos = [a for a in autos if dentro_do_periodo_vistoria(a)]
        intimacoes = [i for i in intimacoes if dentro_do_periodo_vistoria(i)]

    contagem_meses_docs = {}
    contagem_meses_lotes = {}
    
    # Estruturas com suporte a Métrica (lotes vs docs), Tipo e Mês
    estrutura_isolada = lambda: {"l": 0, "f": 0, "p": 0}
    grupo_isolada = lambda: {"Todos": estrutura_isolada(), "Autos": estrutura_isolada(), "Intimações": estrutura_isolada()}
    isoladas_geral = {"lotes": grupo_isolada(), "docs": grupo_isolada()}
    isoladas_mensal = {}

    # al/af/ap = Atendidos | nl/nf/np = Não Atendidos
    estrutura_base = lambda: {"nl": 0, "al": 0, "nf": 0, "af": 0, "np": 0, "ap": 0}
    grupo_status = lambda: {"Todos": estrutura_base(), "Autos": estrutura_base(), "Intimações": estrutura_base()}
    status_det_geral = {"lotes": grupo_status(), "docs": grupo_status()}
    status_det_mensal = {}
    
    pizza_autos = {"lotes": {}, "docs": {}}
    pizza_ints = {"lotes": {}, "docs": {}}
    total_lotes_autos = 0
    total_lotes_ints = 0

    def contar_lotes(registro):
        try:
            if registro.imoveis and registro.imoveis != "[]":
                dados = json.loads(registro.imoveis)
                lotes = dados.get("lotes", [])
                return len(lotes) if len(lotes) > 0 else 1
        except Exception:
            pass
        return 1

    for reg in autos + intimacoes:
        qtd_lotes = contar_lotes(reg)
        tipo_doc = "Autos" if reg.tipo == "Auto" else "Intimações"
        
        if reg.tipo == "Auto":
            total_lotes_autos += qtd_lotes
        else:
            total_lotes_ints += qtd_lotes

        inf = reg.inciso_amigavel
        inf_upper = str(inf).upper() if inf else ""
        tem_l = "LIMPEZA" in inf_upper
        tem_f = "FECHAMENTO" in inf_upper
        tem_p = "PASSEIO" in inf_upper

        if inf:
            alvo_pizza = pizza_autos if reg.tipo == "Auto" else pizza_ints
            alvo_pizza["lotes"][inf] = alvo_pizza["lotes"].get(inf, 0) + qtd_lotes
            alvo_pizza["docs"][inf] = alvo_pizza["docs"].get(inf, 0) + 1

        # Mês de emissão do documento
        mk_criacao = None
        if reg.data:
            partes = reg.data.split('/')
            if len(partes) == 3:
                mk_criacao = f"{partes[2]}-{partes[1]}"
                if mk_criacao not in contagem_meses_docs:
                    contagem_meses_docs[mk_criacao] = {"auto": 0, "int": 0}
                    contagem_meses_lotes[mk_criacao] = {"auto": 0, "int": 0}
                
                if reg.tipo == "Auto": 
                    contagem_meses_docs[mk_criacao]["auto"] += 1
                    contagem_meses_lotes[mk_criacao]["auto"] += qtd_lotes
                else: 
                    contagem_meses_docs[mk_criacao]["int"] += 1
                    contagem_meses_lotes[mk_criacao]["int"] += qtd_lotes

        # 1. Alimenta Demandas Isoladas (Lotes e Documentos)
        if mk_criacao and mk_criacao not in isoladas_mensal:
            isoladas_mensal[mk_criacao] = {"lotes": grupo_isolada(), "docs": grupo_isolada()}

        for metrica, peso in [("lotes", qtd_lotes), ("docs", 1)]:
            if tem_l:
                isoladas_geral[metrica]["Todos"]["l"] += peso
                isoladas_geral[metrica][tipo_doc]["l"] += peso
                if mk_criacao:
                    isoladas_mensal[mk_criacao][metrica]["Todos"]["l"] += peso
                    isoladas_mensal[mk_criacao][metrica][tipo_doc]["l"] += peso
            if tem_f:
                isoladas_geral[metrica]["Todos"]["f"] += peso
                isoladas_geral[metrica][tipo_doc]["f"] += peso
                if mk_criacao:
                    isoladas_mensal[mk_criacao][metrica]["Todos"]["f"] += peso
                    isoladas_mensal[mk_criacao][metrica][tipo_doc]["f"] += peso
            if tem_p:
                isoladas_geral[metrica]["Todos"]["p"] += peso
                isoladas_geral[metrica][tipo_doc]["p"] += peso
                if mk_criacao:
                    isoladas_mensal[mk_criacao][metrica]["Todos"]["p"] += peso
                    isoladas_mensal[mk_criacao][metrica][tipo_doc]["p"] += peso

        # 2. Validação Estrita de Vistoria (Apenas Atendidos e Não Atendidos reais)
        st_geral = str(reg.status_documento) if reg.status_documento else ""
        doc_invalido = ("DEVOLVIDO" in st_geral) or ("CANCELADO" in st_geral)

        def avaliar_item(status_individual):
            if doc_invalido:
                return None
            if status_individual in ["Atendido", "Não Atendido"]:
                return status_individual
            if st_geral == "Conferido - Atendido":
                return "Atendido"
            if st_geral in ["Conferido - Não Atendido", "MULTADO"] or st_geral.startswith("Auto"):
                return "Não Atendido"
            return None

        def obter_mes_vistoria(data_vist):
            if data_vist and len(str(data_vist).split('-')) == 3:
                p = str(data_vist).split('-')
                return f"{p[0]}-{p[1]}"
            return mk_criacao

        def contabilizar_status(chave_stat, data_vist):
            mk_v = obter_mes_vistoria(data_vist)
            if mk_v and mk_v not in status_det_mensal:
                status_det_mensal[mk_v] = {"lotes": grupo_status(), "docs": grupo_status()}
            
            for metrica, peso in [("lotes", qtd_lotes), ("docs", 1)]:
                status_det_geral[metrica]["Todos"][chave_stat] += peso
                status_det_geral[metrica][tipo_doc][chave_stat] += peso
                if mk_v:
                    status_det_mensal[mk_v][metrica]["Todos"][chave_stat] += peso
                    status_det_mensal[mk_v][metrica][tipo_doc][chave_stat] += peso

        if tem_l:
            res_l = avaliar_item(reg.status_limpeza)
            if res_l == "Atendido": contabilizar_status("al", reg.data_vistoria_limpeza)
            elif res_l == "Não Atendido": contabilizar_status("nl", reg.data_vistoria_limpeza)

        if tem_f:
            res_f = avaliar_item(reg.status_fechamento)
            if res_f == "Atendido": contabilizar_status("af", reg.data_vistoria_fechamento)
            elif res_f == "Não Atendido": contabilizar_status("nf", reg.data_vistoria_fechamento)

        if tem_p:
            res_p = avaliar_item(reg.status_passeio)
            if res_p == "Atendido": contabilizar_status("ap", reg.data_vistoria_passeio)
            elif res_p == "Não Atendido": contabilizar_status("np", reg.data_vistoria_passeio)

    meses_nomes = {"01":"Jan", "02":"Fev", "03":"Mar", "04":"Abr", "05":"Mai", "06":"Jun", "07":"Jul", "08":"Ago", "09":"Set", "10":"Out", "11":"Nov", "12":"Dez"}
    meses_ordenados = sorted(contagem_meses_docs.keys())
    
    status_mensal_formatado = {}
    for m in sorted(status_det_mensal.keys()):
        nome_mes = f"{meses_nomes.get(m.split('-')[1], m.split('-')[1])}/{m.split('-')[0]}"
        status_mensal_formatado[nome_mes] = status_det_mensal[m]

    isoladas_mensal_formatado = {}
    for m in sorted(isoladas_mensal.keys()):
        nome_mes = f"{meses_nomes.get(m.split('-')[1], m.split('-')[1])}/{m.split('-')[0]}"
        isoladas_mensal_formatado[nome_mes] = isoladas_mensal[m]

    pa_lotes = sorted(pizza_autos["lotes"].items(), key=lambda x: x[1], reverse=True)
    pa_docs = sorted(pizza_autos["docs"].items(), key=lambda x: x[1], reverse=True)
    pi_lotes = sorted(pizza_ints["lotes"].items(), key=lambda x: x[1], reverse=True)
    pi_docs = sorted(pizza_ints["docs"].items(), key=lambda x: x[1], reverse=True)

    dados_graficos = {
        "meses": [f"{meses_nomes.get(m.split('-')[1], m.split('-')[1])}/{m.split('-')[0]}" for m in meses_ordenados],
        "autos_por_mes_docs": [contagem_meses_docs[m]["auto"] for m in meses_ordenados],
        "ints_por_mes_docs": [contagem_meses_docs[m]["int"] for m in meses_ordenados],
        "autos_por_mes_lotes": [contagem_meses_lotes[m]["auto"] for m in meses_ordenados],
        "ints_por_mes_lotes": [contagem_meses_lotes[m]["int"] for m in meses_ordenados],
        
        "isoladas_geral": isoladas_geral,
        "isoladas_mensal": isoladas_mensal_formatado,
        
        "status_det_geral": status_det_geral,
        "status_det_mensal": status_mensal_formatado,

        "pizza_autos": {
            "lotes": {"labels": [k for k, v in pa_lotes], "valores": [v for k, v in pa_lotes]},
            "docs": {"labels": [k for k, v in pa_docs], "valores": [v for k, v in pa_docs]}
        },
        "pizza_ints": {
            "lotes": {"labels": [k for k, v in pi_lotes], "valores": [v for k, v in pi_lotes]},
            "docs": {"labels": [k for k, v in pi_docs], "valores": [v for k, v in pi_docs]}
        }
    }

    # Calcula o próximo número disponível DENTRO do ano específico
    ultimo_auto = db.query(Registro).filter(filtro_ativos, Registro.tipo == "Auto", Registro.data.like(f"%/{ano_base}")).order_by(Registro.numero_documento.desc()).first()
    ultimo_int = db.query(Registro).filter(filtro_ativos, Registro.tipo == "Intimação", Registro.data.like(f"%/{ano_base}")).order_by(Registro.numero_documento.desc()).first()
    
    return templates.TemplateResponse(request, "index.html", {
        "request": request, "autos": autos, "intimacoes": intimacoes, 
        "auth": auth, "busca": busca, "busca_endereco": busca_endereco, "filtro_inciso": filtro_inciso, 
        "data_inicio": data_inicio, "data_fim": data_fim, 
        "vistoria_inicio": vistoria_inicio, "vistoria_fim": vistoria_fim,
        "filtro_status": filtro_status, "ano_base": ano_base,
        "prox_auto": (ultimo_auto.numero_documento + 1) if ultimo_auto and ultimo_auto.numero_documento else 1,
        "prox_int": (ultimo_int.numero_documento + 1) if ultimo_int and ultimo_int.numero_documento else 1,
        "dados_graficos_json": json.dumps(dados_graficos),
        "total_lotes_autos": total_lotes_autos, "total_lotes_ints": total_lotes_ints,
        "total_lotes": total_lotes_autos + total_lotes_ints
    })

@app.post("/salvar", response_class=HTMLResponse)
async def salvar(request: Request, db: Session = Depends(get_db), auth = Depends(checar_auth)):
    if not auth: return HTMLResponse("Acesso negado.", status_code=403)

    try:
        # 1. Lê o formulário bruto da rede (bypassa o limite de segurança do Form(...))
        form = await request.form()
        
        id_val = form.get("id")
        registro_id = int(id_val) if id_val and str(id_val).strip() != "" else None
        
        numero_documento = int(form.get("numero_documento"))
        tipo = form.get("tipo")
        inciso = form.get("inciso")
        nome = form.get("nome")
        cpf = form.get("cpf", "")
        data = form.get("data", "")
        detalhes = form.get("detalhes", "")
        protocolo_denuncia = form.get("protocolo_denuncia", "")
        
        endereco_completo = form.get("endereco_completo", "")
        bairro = form.get("bairro", "")
        quadra = form.get("quadra", "")
        
        # 2. Extrai as listas completas independentemente do tamanho
        inscricoes = form.getlist("inscricoes")
        numeros_lotes = form.getlist("numeros_lotes")
        
        logradouro_proprietario = form.get("logradouro_proprietario", "")
        numero_proprietario = form.get("numero_proprietario", "")
        complemento_proprietario = form.get("complemento_proprietario", "")
        bairro_proprietario = form.get("bairro_proprietario", "")
        cidade_proprietario = form.get("cidade_proprietario", "Montes Claros - MG")
        cep_proprietario = form.get("cep_proprietario", "")
        
        tem_responsavel = (form.get("tem_responsavel") == "true")
        nome_responsavel = form.get("nome_responsavel", "")
        cpf_responsavel = form.get("cpf_responsavel", "")
        tipo_responsavel = form.get("tipo_responsavel")
        
        numero_intimacao_fiscal = form.get("numero_intimacao_fiscal", "")
        dia_intimacao = form.get("dia_intimacao", "")
        mes_intimacao = form.get("mes_intimacao", "")
        ano_intimacao = form.get("ano_intimacao", "")
        
        status_limpeza = form.get("status_limpeza")
        status_fechamento = form.get("status_fechamento")
        status_passeio = form.get("status_passeio")

        # 3. Validação de Duplicidade
        filtro_ativos = or_(Registro.excluido == False, Registro.excluido == None)
        existente = db.query(Registro).filter(filtro_ativos, Registro.tipo == tipo, Registro.numero_documento == numero_documento).first()
    
        if existente:
            if not registro_id or existente.id != registro_id:
                return HTMLResponse("DUPLICADO", status_code=200)
        
        # 4. Formata os lotes extraídos
        dados_imoveis = {
            "endereco_completo": endereco_completo,
            "bairro": bairro,
            "quadra": quadra,
            "lotes": [{"inscricao": i, "numero": n} for i, n in zip(inscricoes, numeros_lotes)]
        }
        imoveis_json = json.dumps(dados_imoveis, ensure_ascii=False)

        if registro_id:
            registro = db.query(Registro).filter(Registro.id == registro_id).first()
            if not registro:
                return HTMLResponse("Erro: Registro não encontrado.", status_code=404)
            snapshot_antes = extrair_snapshot(registro)
                       
            registro.numero_documento = numero_documento
            registro.tipo, registro.inciso = tipo, inciso
            registro.nome, registro.cpf, registro.data = nome, cpf, data
            registro.detalhes, registro.imoveis = detalhes, imoveis_json
            registro.protocolo_denuncia = protocolo_denuncia
            registro.logradouro_proprietario = logradouro_proprietario
            registro.numero_proprietario = numero_proprietario
            registro.complemento_proprietario = complemento_proprietario
            registro.bairro_proprietario = bairro_proprietario
            registro.cidade_proprietario = cidade_proprietario
            registro.cep_proprietario = cep_proprietario
            registro.tem_responsavel = tem_responsavel
            registro.nome_responsavel = nome_responsavel
            registro.cpf_responsavel = cpf_responsavel
            if tipo_responsavel: registro.tipo_responsavel = tipo_responsavel
            registro.numero_intimacao_fiscal = numero_intimacao_fiscal
            registro.dia_intimacao = dia_intimacao
            registro.mes_intimacao = mes_intimacao
            registro.ano_intimacao = ano_intimacao
            
            if status_limpeza is not None: registro.status_limpeza = status_limpeza
            if status_fechamento is not None: registro.status_fechamento = status_fechamento
            if status_passeio is not None: registro.status_passeio = status_passeio
        else:
            registro = Registro(
                numero_documento=numero_documento,
                tipo=tipo,
                inciso=inciso,
                nome=nome,
                cpf=cpf,
                data=data, 
                detalhes=detalhes,
                imoveis=imoveis_json,
                protocolo_denuncia=protocolo_denuncia,
                logradouro_proprietario=logradouro_proprietario,
                numero_proprietario=numero_proprietario,
                complemento_proprietario=complemento_proprietario,
                bairro_proprietario=bairro_proprietario,
                cidade_proprietario=cidade_proprietario,
                cep_proprietario=cep_proprietario,
                tem_responsavel=tem_responsavel,
                nome_responsavel=nome_responsavel,
                cpf_responsavel=cpf_responsavel,
                tipo_responsavel=tipo_responsavel or "A/C",
                numero_intimacao_fiscal=numero_intimacao_fiscal,
                dia_intimacao=dia_intimacao,
                mes_intimacao=mes_intimacao,
                ano_intimacao=ano_intimacao,
                criado_por=auth.nome_completo if auth else "Desconhecido"
            )
            db.add(registro)

        # ========================================================
        # LÓGICA: RECALCULAR STATUS GERAL CASO A INFRAÇÃO SEJA ALTERADA NA EDIÇÃO
        # ========================================================
        n_st = "Aguardando AR"
        
        if registro.inciso_amigavel:
            infracoes = str(registro.inciso_amigavel).upper()
            req_l = "LIMPEZA" in infracoes
            req_f = "FECHAMENTO" in infracoes
            req_p = "PASSEIO" in infracoes

            if req_l or req_f or req_p:
                pend = 0
                houve_nao = False
                iniciou = False

                if req_l:
                    if not registro.status_limpeza: pend += 1
                    else:
                        iniciou = True
                        if registro.status_limpeza == "Não Atendido": houve_nao = True
                if req_f:
                    if not registro.status_fechamento: pend += 1
                    else:
                        iniciou = True
                        if registro.status_fechamento == "Não Atendido": houve_nao = True
                if req_p:
                    if not registro.status_passeio: pend += 1
                    else:
                        iniciou = True
                        if registro.status_passeio == "Não Atendido": houve_nao = True

                tem_prz = (registro.data_conferencia_limpeza or registro.data_conferencia_fechamento or registro.data_conferencia_passeio)

                if pend == 0 and iniciou:
                    n_st = "Conferido - Não Atendido" if houve_nao else "Conferido - Atendido"
                elif iniciou or tem_prz:
                    n_st = "Conferir"
                    
                if (registro.mes_multa or registro.ano_multa) and registro.tipo == "Auto" and houve_nao:
                    n_st = "MULTADO"

        # SOBREPOSIÇÃO SUPREMA DE AR E CANCELAMENTO NA EDIÇÃO GERAL
        if registro.ar_devolvido == "Não Refeito":
            n_st = "DEVOLVIDO - NÃO REFEITO"
        elif registro.ar_devolvido == "Refeito":
            num_ref = registro.novo_numero_refeito.strip() if registro.novo_numero_refeito else "S/N"
            n_st = f"DEVOLVIDO - REFEITO Nº {num_ref}"
        elif registro.ar_devolvido == "Cancelado - Não Refeito":
            n_st = "CANCELADO - NÃO REFEITO"
        elif registro.ar_devolvido == "Cancelado - Refeito":
            num_ref = registro.novo_numero_refeito.strip() if registro.novo_numero_refeito else "S/N"
            n_st = f"CANCELADO - REFEITO Nº {num_ref}"

        st_atual = str(registro.status_documento) if registro.status_documento else ""
        if not st_atual.startswith("Auto"):
            registro.status_documento = n_st
        # ========================================================
        
        db.flush() # Alinhado fora do IF acima
        if registro_id:
            diff_str = calcular_diff(snapshot_antes, extrair_snapshot(registro))
            registrar_log(db, request, auth, "EDITAR_DOCUMENTO", registro.id, f"{registro.tipo} Nº {registro.numero_documento} | Mudanças: {diff_str}")
        else:
            registrar_log(db, request, auth, "CRIAR_DOCUMENTO", registro.id, f"Criado {registro.tipo} Nº {registro.numero_documento} ({registro.nome})")

        db.commit()
            
        # ========================================================
        # LÓGICA: Atualizar o status da Intimação Origem (COM DESVINCULAÇÃO)
        # ========================================================
        if tipo == "Auto":
            try:
                ano_auto = str(data).split('/')[2][-2:] if data and len(str(data).split('/')) == 3 else ""
                auto_str = f"Auto {numero_documento}/{ano_auto}" if ano_auto else f"Auto {numero_documento}"
                
                db.query(Registro).filter(Registro.tipo == "Intimação", Registro.status_documento == auto_str).update({"status_documento": "Aguardando AR"})
                db.commit()

                if numero_intimacao_fiscal:
                    num_int_origem = int(re.sub(r'\D', '', str(numero_intimacao_fiscal).split('/')[0]))
                    
                    ano_alvo = str(ano_intimacao).strip()
                    if not ano_alvo and "/" in str(numero_intimacao_fiscal):
                        ano_alvo = re.sub(r'\D', '', str(numero_intimacao_fiscal).split('/')[1])
                    
                    ano_busca = ""
                    if ano_alvo:
                        ano_busca = f"20{ano_alvo}" if len(ano_alvo) == 2 else ano_alvo

                    query_int = db.query(Registro).filter(Registro.tipo == "Intimação", Registro.numero_documento == num_int_origem)
                    
                    if ano_busca:
                        query_int = query_int.filter(Registro.data.like(f"%/{ano_busca}"))
                    
                    int_origem = query_int.order_by(Registro.id.desc()).first()
                    
                    if int_origem:
                        int_origem.status_documento = auto_str
                        db.commit()
            except Exception as e:
                pass 
        # ========================================================

        return HTMLResponse("OK")

    except Exception as e:
        db.rollback()
        print(f"ERRO CRÍTICO AO SALVAR: {str(e)}")
        return HTMLResponse(f"Erro interno no Python: {str(e)}", status_code=500)

    
@app.get("/editar/{id}", response_class=HTMLResponse)
def editar(request: Request, id: int, db: Session = Depends(get_db), auth = Depends(checar_auth)):
    filtro_ativos = or_(Registro.excluido == False, Registro.excluido == None)
    
    registro = db.query(Registro).filter(filtro_ativos, Registro.id == id).first() if id != 0 else None
    dados_imoveis = None
    if registro and registro.imoveis and registro.imoveis != "[]":
        try:
            dados_imoveis = json.loads(registro.imoveis)
        except:
            pass
            
    ano_vigente = str(datetime.now().year)
    if registro and registro.data and len(str(registro.data).split('/')) == 3:
        ano_vigente = str(registro.data).split('/')[2]
        
    # Ignora os registros excluídos ao calcular o próximo número
    ultimo_auto = db.query(Registro).filter(filtro_ativos, Registro.tipo == "Auto", Registro.data.like(f"%/{ano_vigente}")).order_by(Registro.numero_documento.desc()).first()
    ultimo_int = db.query(Registro).filter(filtro_ativos, Registro.tipo == "Intimação", Registro.data.like(f"%/{ano_vigente}")).order_by(Registro.numero_documento.desc()).first()
    
    prox_auto = (ultimo_auto.numero_documento + 1) if ultimo_auto and ultimo_auto.numero_documento else 1
    prox_int = (ultimo_int.numero_documento + 1) if ultimo_int and ultimo_int.numero_documento else 1
        
    return templates.TemplateResponse(request, "formulario.html", {
        "request": request, "reg": registro, "auth": auth, 
        "dados_imoveis": dados_imoveis, "prox_auto": prox_auto, "prox_int": prox_int
    })

@app.delete("/deletar/{id}", response_class=HTMLResponse)
def deletar(request: Request, id: int, db: Session = Depends(get_db), auth = Depends(checar_auth)):
    if not auth: return HTMLResponse("Acesso negado.", status_code=403)
    
    registro = db.query(Registro).filter(Registro.id == id).first()
    
    if registro:
        if registro.tipo == "Auto":
            ano_auto = str(registro.data).split('/')[2][-2:] if registro.data and len(str(registro.data).split('/')) == 3 else ""
            auto_str = f"Auto {registro.numero_documento}/{ano_auto}" if ano_auto else f"Auto {registro.numero_documento}"
            db.query(Registro).filter(Registro.tipo == "Intimação", Registro.status_documento == auto_str).update({"status_documento": "Aguardando AR"})
        
        # EXCLUSÃO LÓGICA (Soft Delete)
        registro.excluido = True
        registrar_log(
            db, request, auth, "EXCLUIR_DOCUMENTO", registro.id,
            f"Exclusão lógica do {registro.tipo} Nº {registro.numero_documento} - Proprietário: {registro.nome} (CPF: {registro.cpf})"
        )
        db.commit()
        
    return HTMLResponse("OK")

@app.get("/gerar/{id}")
def gerar_docx(id: int, db: Session = Depends(get_db)):
    registro = db.query(Registro).filter(Registro.id == id).first()
    tipo_formatado = "intimacao" if registro.tipo == "Intimação" else "auto"
    inciso_formatado = registro.inciso_select.replace(" ", "_").lower()
    modelo_path = os.path.join(os.getcwd(), "templates", "documentos", f"{tipo_formatado}_{inciso_formatado}.docx")
    
    if not os.path.exists(modelo_path):
        return HTMLResponse(f"Erro: O arquivo '{tipo_formatado}_{inciso_formatado}.docx' não foi encontrado na pasta do sistema.", status_code=404)

    # 1. Abre os dados dos imóveis primeiro
    try:
        dados_imoveis = json.loads(registro.imoveis) if registro.imoveis and registro.imoveis != "[]" else {}
    except Exception:
        dados_imoveis = {}

    # 2. Conta a quantidade de lotes (inscrições)
    lotes_lista = dados_imoveis.get("lotes", [])
    quantidade_lotes = len(lotes_lista) if len(lotes_lista) > 0 else 1

    # 3. Calcula o valor final: infrações * valor * quantidade de lotes
    quantidade_infracoes = len(registro.inciso_select.split())
    valor_base = 2807.10
    valor_total_calculado = quantidade_infracoes * valor_base * quantidade_lotes
    
    # Formata para o padrão brasileiro (R$ X.XXX,XX)
    multa_formatada = f"{valor_total_calculado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    dia_doc, mes_doc, ano_doc = "", "", ""
    ano_c = ""  # Variável declarada corretamente fora do IF
    
    if registro.data:
        p = str(registro.data).split('/')
        if len(p) == 3:
            dia_doc, ano_doc = p[0], p[2]
            ano_c = ano_doc[-2:]
            meses_dict = {"01": "JANEIRO", "02": "FEVEREIRO", "03": "MARÇO", "04": "ABRIL", "05": "MAIO", "06": "JUNHO", "07": "JULHO", "08": "AGOSTO", "09": "SETEMBRO", "10": "OUTUBRO", "11": "NOVEMBRO", "12": "DEZEMBRO"}
            mes_doc = meses_dict.get(p[1], "")
    def formatar_documento(doc_str):
        if not doc_str:
            return ""
        v = re.sub(r'\D', '', str(doc_str))
        if len(v) == 11:
            return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
        elif len(v) == 14:
            return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
        return doc_str
        
    # Função auxiliar para forçar caixa alta no Word
    def cx_alta(texto):
        return str(texto).upper().strip() if texto else ""

    # Lógica para adicionar o /ANO no número da intimação automaticamente
    num_int_formatado = str(registro.numero_intimacao_fiscal).strip() if registro.numero_intimacao_fiscal else ""
    if num_int_formatado and "/" not in num_int_formatado:
        ano_int = str(registro.ano_intimacao).strip() if registro.ano_intimacao else ""
        if ano_int:
            num_int_formatado = f"{num_int_formatado}/{ano_int[-2:]}"
    
    contexto = {
        "n_doc": registro.numero_documento,
        "tipo": cx_alta(registro.tipo),
        "inciso": cx_alta(registro.inciso_amigavel),
        "nome": cx_alta(registro.nome),
        "cpf": formatar_documento(registro.cpf),
        "data": registro.data,
        "data_hoje": dia_doc,
        "mes_hoje": cx_alta(mes_doc),
        "ano_hoje": ano_doc,
        "ano_c": ano_c,
        "detalhes": cx_alta(registro.detalhes),
        "endereco_completo": cx_alta(dados_imoveis.get("endereco_completo", "")),
        "bairro": cx_alta(dados_imoveis.get("bairro", "")),
        "quadra": cx_alta(dados_imoveis.get("quadra", "")),
        "lotes": [
            {"inscricao": cx_alta(l.get("inscricao", "")), "numero": cx_alta(l.get("numero", ""))} 
            for l in dados_imoveis.get("lotes", [])
        ],
        "valor_total_multa": multa_formatada,
        "logradouro_proprietario": cx_alta(registro.logradouro_proprietario),
        "numero_proprietario": cx_alta(registro.numero_proprietario),
        "complemento_proprietario": cx_alta(registro.complemento_proprietario),
        "bairro_proprietario": cx_alta(registro.bairro_proprietario),
        "cidade_proprietario": cx_alta(registro.cidade_proprietario),
        "cep_proprietario": registro.cep_proprietario,
        "tem_responsavel": registro.tem_responsavel,
        "prefixo_responsavel": cx_alta(registro.tipo_responsavel) if registro.tipo_responsavel else "A/C",
        "nome_responsavel": cx_alta(registro.nome_responsavel),
        "cpf_responsavel": formatar_documento(registro.cpf_responsavel),
        "numero_intimacao_fiscal": cx_alta(num_int_formatado),
        "dia_intimacao": cx_alta(registro.dia_intimacao),
        "mes_intimacao": cx_alta(registro.mes_intimacao),
        "ano_intimacao": cx_alta(registro.ano_intimacao),
    }
    
    doc = DocxTemplate(modelo_path)
    doc.render(contexto)
    
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    nome_arquivo = f"{registro.numero_documento} {registro.nome}.docx"
    nome_seguro = quote(nome_arquivo)
    
    headers = {"Content-Disposition": f"attachment; filename*=utf-8''{nome_seguro}"}
    return StreamingResponse(file_stream, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers=headers)


@app.get("/api/intimacao/{numero}")
def buscar_intimacao(numero: str, db: Session = Depends(get_db)):
    try:
        partes = str(numero).split('/')
        num_str = re.sub(r'\D', '', partes[0])
        if not num_str:
            return {"encontrado": False}
            
        num_limpo = int(num_str)
        
        # Garante que não vai puxar dados de uma intimação que foi excluída
        filtro_ativos = or_(Registro.excluido == False, Registro.excluido == None)
        query = db.query(Registro).filter(filtro_ativos, Registro.tipo == "Intimação", Registro.numero_documento == num_limpo)

        # Filtra pelo ano se o usuário digitar com barra (ex: 2907/25)
        if len(partes) > 1:
            ano_str = re.sub(r'\D', '', partes[1])
            if len(ano_str) == 2:
                ano_str = f"20{ano_str}"
            if len(ano_str) == 4:
                query = query.filter(Registro.data.like(f"%/{ano_str}"))

        registro = query.order_by(Registro.id.desc()).first()
        
        if not registro:
            return {"encontrado": False}

        dados_imoveis = None
        if registro.imoveis and registro.imoveis != "[]":
            try:
                dados_imoveis = json.loads(registro.imoveis)
            except Exception:
                pass

        def limpar_none(texto):
            if not texto or str(texto).strip().lower() == "none":
                return ""
            return str(texto).strip()

        logradouro = limpar_none(registro.logradouro_proprietario)
        numero_prop = limpar_none(registro.numero_proprietario)
        complemento_prop = limpar_none(registro.complemento_proprietario)
        bairro_prop = limpar_none(registro.bairro_proprietario)

        if logradouro and not numero_prop and not bairro_prop:
            match_bairro = re.split(r'[-–]', logradouro)
            if len(match_bairro) > 1:
                bairro_prop = match_bairro[-1].strip()
                logradouro = "-".join(match_bairro[:-1]).strip()

            partes = [p.strip() for p in logradouro.split(',')]
            logradouro = partes[0]

            if len(partes) > 1:
                numero_prop = re.sub(r'(?i)^n[º°o.]?\s*', '', partes[1]).strip()
            
            if len(partes) > 2:
                complemento_prop = ", ".join(partes[2:]).strip()

        dia_int, mes_int, ano_int = "", "", ""
        if registro.data:
            partes_dt = str(registro.data).split('/')
            if len(partes_dt) == 3:
                dia_int, ano_int = partes_dt[0], partes_dt[2]
                meses_dict = {"01": "JANEIRO", "02": "FEVEREIRO", "03": "MARÇO", "04": "ABRIL", "05": "MAIO", "06": "JUNHO", "07": "JULHO", "08": "AGOSTO", "09": "SETEMBRO", "10": "OUTUBRO", "11": "NOVEMBRO", "12": "DEZEMBRO"}
                mes_int = meses_dict.get(partes_dt[1], "")

        return {
            "encontrado": True,
            "inciso": registro.inciso_select,
            "nome": registro.nome,
            "cpf": registro.cpf,
            "logradouro_proprietario": logradouro,
            "numero_proprietario": numero_prop,
            "complemento_proprietario": complemento_prop,
            "bairro_proprietario": bairro_prop,
            "cidade_proprietario": limpar_none(registro.cidade_proprietario) or "MONTES CLAROS - MG",
            "cep_proprietario": limpar_none(registro.cep_proprietario),
            "tem_responsavel": registro.tem_responsavel,
            "tipo_responsavel": limpar_none(registro.tipo_responsavel) or "A/C",
            "nome_responsavel": limpar_none(registro.nome_responsavel),
            "cpf_responsavel": limpar_none(registro.cpf_responsavel),
            "dia_intimacao": dia_int,
            "mes_intimacao": mes_int,
            "ano_intimacao": ano_int,
            "dados_imoveis": dados_imoveis
        }
    except Exception as e:
        print(f"Erro na API de busca: {e}")
        return {"encontrado": False}

@app.post("/exportar")
def exportar_planilha(request: Request, ids: list[int] = Body(...), db: Session = Depends(get_db), auth = Depends(checar_auth)):
    registrar_log(db, request, auth, "EXPORTAR_PLANILHA", detalhes=f"Exportou {len(ids)} registros. IDs: {ids}")
    db.commit()
    # Organiza do menor para o maior número
    registros = db.query(Registro).filter(Registro.id.in_(ids)).order_by(Registro.numero_documento.asc()).all()
    linhas = []
    
    def limpar(texto):
        return str(texto).replace('\t', ' ').replace('\n', ' ').strip().upper() if texto else ""

    for reg in registros:
        # Captura o ano de criação do documento automaticamente (ex: "2026" -> "26")
        ano_doc_curto = ""
        if reg.data and len(str(reg.data).split('/')) == 3:
            ano_doc_curto = str(reg.data).split('/')[2][-2:]
                
        data_doc = limpar(reg.data)
        nome = limpar(reg.nome)

        if reg.tem_responsavel and reg.nome_responsavel:
            prefixo = limpar(reg.tipo_responsavel) if reg.tipo_responsavel else "A/C"
            nome_resp = limpar(reg.nome_responsavel)
            nome = f"{nome} {prefixo} {nome_resp}"
        
      
        infracao = limpar(reg.inciso_amigavel)
        
        bairro_lote = ""
        end_lote_str = ""
        try:
            imoveis = json.loads(reg.imoveis) if reg.imoveis and reg.imoveis != "[]" else {}
            end_comp = str(imoveis.get("endereco_completo", "")).strip()
            bairro_lote = str(imoveis.get("bairro", "")).strip()
            quadra = str(imoveis.get("quadra", "")).strip()
            lotes = imoveis.get("lotes", [])
            
            lotes_formatados = " ".join([f"INSCRIÇÃO: {l.get('inscricao','')} LOTE: {l.get('numero','')}" for l in lotes])
            end_lote_str = f"{end_comp} BAIRRO: {bairro_lote} {lotes_formatados} QUADRA: {quadra}".strip()
        except Exception:
            pass

        if reg.tipo == "Auto":
            # AUTO: O Nº da intimação de origem RECEBE o /ano
            num_int_planilha = str(reg.numero_intimacao_fiscal).strip() if reg.numero_intimacao_fiscal else ""
            if num_int_planilha and "/" not in num_int_planilha:
                ano_int = str(reg.ano_intimacao).strip() if reg.ano_intimacao else ""
                if ano_int:
                    num_int_planilha = f"{num_int_planilha}/{ano_int[-2:]}"
                elif ano_doc_curto: # Fallback caso esqueça de preencher o ano
                    num_int_planilha = f"{num_int_planilha}/{ano_doc_curto}"
            
            num_intimacao = limpar(num_int_planilha)
            linha = f"{num_intimacao}\t{data_doc}\t{nome}\t{limpar(bairro_lote)}\t{infracao}"
            linhas.append(linha)
            
        else:
            # INTIMAÇÃO: O Nº do documento NÃO recebe o /ano (permanece puro)
            n_doc = str(reg.numero_documento).strip() if reg.numero_documento else ""
                
            p_end = []
            if reg.logradouro_proprietario: p_end.append(reg.logradouro_proprietario.strip())
            if reg.numero_proprietario: p_end.append(f"nº {reg.numero_proprietario.strip()}")
            if reg.complemento_proprietario: p_end.append(reg.complemento_proprietario.strip())
            
            end_prop = ", ".join(p_end)
            if reg.bairro_proprietario:
                end_prop += f" - {reg.bairro_proprietario.strip()}"
                
            cid = str(reg.cidade_proprietario).strip() if reg.cidade_proprietario else ""
            if cid and cid.upper() not in ["MONTES CLAROS - MG", "MONTES CLAROS", "MONTES CLAROS-MG"]:
                end_prop += f" - {cid}"
                
            cep = re.sub(r'\D', '', str(reg.cep_proprietario)) if reg.cep_proprietario else ""
            protocolo = limpar(reg.protocolo_denuncia)
            
            linha = f"{n_doc}\t{data_doc}\t{nome}\t{limpar(end_prop)}\t{limpar(cep)}\t{limpar(end_lote_str)}\t{protocolo}\t{limpar(bairro_lote)}\t{infracao}"
            linhas.append(linha)
            
    return HTMLResponse("\n".join(linhas))

@app.post("/exportar_sigep")
def exportar_sigep(request: Request, ids: list[int] = Body(...), db: Session = Depends(get_db), auth = Depends(checar_auth)):
    registrar_log(db, request, auth, "EXPORTAR_SIGEP", detalhes=f"Exportou {len(ids)} registros. IDs: {ids}")
    db.commit()
    registros = db.query(Registro).filter(Registro.id.in_(ids)).all()
    agrupamento = {}
    
    def cx_alta(texto):
        return str(texto).upper().strip() if texto else ""

    for reg in registros:
        if reg.tem_responsavel and reg.nome_responsavel:
            nome_limpo = cx_alta(reg.nome_responsavel)
        else:
            nome_limpo = cx_alta(reg.nome)
        
        ano_curto = ""
        if reg.data and len(str(reg.data).split('/')) == 3:
            ano_curto = str(reg.data).split('/')[2][-2:]
            
        cep_limpo = re.sub(r'\D', '', str(reg.cep_proprietario)) if reg.cep_proprietario else ""
        logradouro = cx_alta(reg.logradouro_proprietario)
        bairro = cx_alta(reg.bairro_proprietario)
        numero = cx_alta(reg.numero_proprietario)
        complemento = cx_alta(reg.complemento_proprietario)[:30] 
        
        # A chave de agrupamento identifica se é o mesmo dono no mesmo endereço
        chave = (nome_limpo, cep_limpo, logradouro, numero, complemento, bairro, ano_curto, reg.tipo)
        
        if chave not in agrupamento:
            agrupamento[chave] = []
        agrupamento[chave].append(reg.numero_documento)
        
    grupos = []
    
    for chave, numeros in agrupamento.items():
        nome_l, cep_l, log_l, num_l, comp_l, bairro_l, ano_c, tipo_reg = chave
        
        # Envia os grupos de volta para o JavaScript decidir o que fazer
        grupos.append({
            "nome": nome_l,
            "cep": cep_l,
            "logradouro": log_l,
            "numero": num_l,
            "complemento": comp_l,
            "bairro": bairro_l,
            "ano": ano_c,
            "tipo": tipo_reg,
            "numeros": sorted(numeros)
        })
        
    return grupos

@app.get("/auditoria", response_class=HTMLResponse)
def ver_auditoria(
    request: Request, 
    busca: str = "", 
    acao: str = "", 
    limite: int = 200, 
    db: Session = Depends(get_db), 
    auth = Depends(checar_auth)
):
    if not auth:
        return HTMLResponse("Acesso restrito. Faça login.", status_code=403)
        
    query = db.query(LogAuditoria)
    
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(or_(
            LogAuditoria.usuario_nome.ilike(termo),
            LogAuditoria.usuario_cpf.ilike(termo),
            LogAuditoria.detalhes.ilike(termo),
            LogAuditoria.data_hora.ilike(termo),
            LogAuditoria.ip.ilike(termo),
            cast(LogAuditoria.registro_id, String) == busca.strip()
        ))
        
    if acao:
        query = query.filter(LogAuditoria.acao == acao)
        
    total_banco = query.count()
    logs = query.order_by(LogAuditoria.id.desc()).limit(limite).all()
    
    linhas_html = "".join([
        f"<tr><td>{l.id}</td><td>{l.data_hora}</td><td>{l.usuario_nome} ({l.usuario_cpf})</td>"
        f"<td>{l.ip}</td><td><span class='badge bg-dark'>{l.acao}</span></td>"
        f"<td>{l.registro_id or '-'}</td><td style='font-family:monospace; font-size:12px;'>{l.detalhes}</td></tr>"
        for l in logs
    ]) or "<tr><td colspan='7' class='text-center py-4 text-muted'>Nenhum registo encontrado para este filtro.</td></tr>"
    
    acoes_disponiveis = ["CRIAR_DOCUMENTO", "EDITAR_DOCUMENTO", "ALTERAR_STATUS", "EXCLUIR_DOCUMENTO", "LOGIN_SUCESSO", "LOGIN_FALHA", "EXPORTAR_PLANILHA", "EXPORTAR_SIGEP"]
    opcoes_acao = "".join([
        f"<option value='{a}' {'selected' if acao == a else ''}>{a}</option>" 
        for a in acoes_disponiveis
    ])

    html = f"""
    <html><head><title>Auditoria LGPD</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
    <body class="p-4 bg-light">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div>
                <h4 class="mb-0">🔒 Trilha de Auditoria e Conformidade</h4>
                <small class="text-muted">A exibir {len(logs)} de {total_banco} registos encontrados no histórico total</small>
            </div>
            <a href="/" class="btn btn-secondary btn-sm fw-bold">Voltar ao Sistema</a>
        </div>
        
        <form method="get" action="/auditoria" class="card p-3 mb-3 shadow-sm border-0">
            <div class="row g-2 align-items-end">
                <div class="col-md-5">
                    <label class="form-label small fw-bold mb-1">Pesquisar (Utilizador, CPF, Data, Nº Doc ou Texto alterado)</label>
                    <input type="text" name="busca" class="form-control form-control-sm" value="{busca}" placeholder="Ex: João, 1022, 26/10/2026...">
                </div>
                <div class="col-md-3">
                    <label class="form-label small fw-bold mb-1">Tipo de Ação</label>
                    <select name="acao" class="form-select form-select-sm">
                        <option value="">Todas as Ações</option>
                        {opcoes_acao}
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label small fw-bold mb-1">Limite no ecrã</label>
                    <select name="limite" class="form-select form-select-sm">
                        <option value="200" {'selected' if limite == 200 else ''}>200 linhas</option>
                        <option value="500" {'selected' if limite == 500 else ''}>500 linhas</option>
                        <option value="2000" {'selected' if limite == 2000 else ''}>2000 linhas</option>
                    </select>
                </div>
                <div class="col-md-2 d-flex gap-1">
                    <button type="submit" class="btn btn-primary btn-sm fw-bold w-100">Filtrar</button>
                    <a href="/auditoria" class="btn btn-outline-secondary btn-sm w-100">Limpar</a>
                </div>
            </div>
        </form>

        <div class="card shadow-sm table-responsive">
            <table class="table table-sm table-striped table-hover mb-0">
                <thead class="table-dark">
                    <tr><th>ID</th><th>Data/Hora</th><th>Utilizador</th><th>IP</th><th>Ação</th><th>ID Doc</th><th>Detalhes (Antes -> Depois)</th></tr>
                </thead>
                <tbody>{linhas_html}</tbody>
            </table>
        </div>
    </body></html>
    """
    return HTMLResponse(html)

@app.post("/salvar_status", response_class=HTMLResponse)
def salvar_status(request: Request, id: str = Form(...),
                  status_limpeza: str = Form(None), status_fechamento: str = Form(None), status_passeio: str = Form(None),
                  data_conferencia_limpeza: str = Form(""), data_conferencia_fechamento: str = Form(""), data_conferencia_passeio: str = Form(""),
                  data_vistoria_limpeza: str = Form(""), data_vistoria_fechamento: str = Form(""), data_vistoria_passeio: str = Form(""),
                  observacoes_status: str = Form(""),
                  is_multado: bool = Form(False), # <--- NOVA VARIÁVEL
                  mes_multa: str = Form(""),
                  ano_multa: str = Form(""),
                  multa_limpeza: str = Form(None),
                  multa_fechamento: str = Form(None),
                  multa_passeio: str = Form(None),
                  ar_devolvido: str = Form(None),
                  motivo_devolucao: str = Form(""),
                  novo_numero_refeito: str = Form(""),
                  cancelado: str = Form(None),
                  motivo_cancelamento: str = Form(""),
                  novo_numero_cancelado: str = Form(""),
                  db: Session = Depends(get_db), auth = Depends(checar_auth)):


    if not auth: return HTMLResponse("Acesso negado", status_code=403)
    
    try:
        registro_id = int(id)
    except (ValueError, TypeError):
        return HTMLResponse("ID inválido", status_code=400)
        
    reg = db.query(Registro).filter(Registro.id == registro_id).first()
    if reg:
        snapshot_antes = extrair_snapshot(reg)
        reg.status_limpeza = status_limpeza
        reg.status_fechamento = status_fechamento
        reg.status_passeio = status_passeio
        reg.data_conferencia_limpeza = data_conferencia_limpeza
        reg.data_conferencia_fechamento = data_conferencia_fechamento
        reg.data_conferencia_passeio = data_conferencia_passeio
        reg.data_vistoria_limpeza = data_vistoria_limpeza
        reg.data_vistoria_fechamento = data_vistoria_fechamento
        reg.data_vistoria_passeio = data_vistoria_passeio
        reg.observacoes_status = observacoes_status

        multado_bool = str(is_multado).lower() in ["true", "on", "yes", "1"]

        reg.mes_multa = mes_multa if is_multado else ""
        reg.ano_multa = ano_multa if is_multado else ""
        reg.multa_limpeza = (str(multa_limpeza).lower() in["true", "on", "1"]) if multado_bool else False
        reg.multa_fechamento = (str(multa_fechamento).lower() in["true", "on", "1"]) if multado_bool else False
        reg.multa_passeio = (str(multa_passeio).lower() in["true", "on", "1"]) if multado_bool else False

        reg.ar_devolvido = ar_devolvido
        reg.motivo_devolucao = motivo_devolucao
        reg.novo_numero_refeito = novo_numero_refeito
        reg.cancelado = cancelado
        reg.motivo_cancelamento = motivo_cancelamento
        reg.novo_numero_cancelado = novo_numero_cancelado
        
        # LÓGICA DE STATUS DOMINANTE (CÁLCULO PADRÃO DE VISTORIAS)
        novo_status = "Aguardando AR" # Status base seguro

        if reg.inciso_amigavel:
            infracoes = str(reg.inciso_amigavel).upper()
            req_l = "LIMPEZA" in infracoes
            req_f = "FECHAMENTO" in infracoes
            req_p = "PASSEIO" in infracoes

            if req_l or req_f or req_p:
                pend = 0
                houve_nao = False
                iniciou = False

                if req_l:
                    if not reg.status_limpeza: pend += 1
                    else:
                        iniciou = True
                        if reg.status_limpeza == "Não Atendido": houve_nao = True
                if req_f:
                    if not reg.status_fechamento: pend += 1
                    else:
                        iniciou = True
                        if reg.status_fechamento == "Não Atendido": houve_nao = True
                if req_p:
                    if not reg.status_passeio: pend += 1
                    else:
                        iniciou = True
                        if reg.status_passeio == "Não Atendido": houve_nao = True

                tem_prz = (reg.data_conferencia_limpeza or reg.data_conferencia_fechamento or reg.data_conferencia_passeio)

                if pend == 0 and iniciou:
                    novo_status = "Conferido - Não Atendido" if houve_nao else "Conferido - Atendido"
                elif iniciou or tem_prz:
                    novo_status = "Conferir"
                    
                if multado_bool and reg.tipo == "Auto" and houve_nao:
                    novo_status = "MULTADO"

        # REGRA SUPREMA: SE O AR VOLTOU OU FOI CANCELADO
        if ar_devolvido == "Não Refeito":
            novo_status = "DEVOLVIDO - NÃO REFEITO"
        elif ar_devolvido == "Refeito":
            num_ref = novo_numero_refeito.strip() if novo_numero_refeito else "S/N"
            novo_status = f"DEVOLVIDO - REFEITO Nº {num_ref}"
        elif ar_devolvido == "Cancelado - Não Refeito":
            novo_status = "CANCELADO - NÃO REFEITO"
        elif ar_devolvido == "Cancelado - Refeito":
            num_ref = novo_numero_refeito.strip() if novo_numero_refeito else "S/N"
            novo_status = f"CANCELADO - REFEITO Nº {num_ref}"

        status_atual = str(reg.status_documento) if reg.status_documento else ""
        if not status_atual.startswith("Auto"):
            reg.status_documento = novo_status

        diff_str = calcular_diff(snapshot_antes, extrair_snapshot(reg))
        registrar_log(db, request, auth, "ALTERAR_STATUS", reg.id, f"{reg.tipo} Nº {reg.numero_documento} | Mudanças: {diff_str}")
        db.commit()
    return HTMLResponse("OK")

if __name__ == "__main__":
    import webbrowser
    from threading import Timer
    import socket
    import uvicorn

    # Tenta descobrir o IPv4 local da máquina
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Não gera tráfego real, apenas descobre a rota padrão
        s.connect(("8.8.8.8", 80))
        meu_ip = s.getsockname()[0]
        s.close()
    except Exception:
        meu_ip = "127.0.0.1"

    print("\n" + "="*60)
    print(" 🚀 SISTEMA FISCAL INICIADO")
    print("="*60)
    print(f" Para acessar NESTE computador, acesse:")
    print(f" https://localhost:8000")
    print("-" * 60)
    print(f" Para acessar de OUTROS computadores na mesma rede:")
    print(f" https://{meu_ip}:8000")
    print("="*60 + "\n")

    def abrir_navegador():
        webbrowser.open("https://localhost:8000")

    Timer(1.5, abrir_navegador).start()
    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_keyfile="key.pem", ssl_certfile="cert.pem", reload=False)
