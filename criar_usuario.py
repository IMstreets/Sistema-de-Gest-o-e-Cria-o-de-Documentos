import sqlite3
import bcrypt
import re
import sys

print("=========================================")
print("      SISTEMA FISCAL - NOVO USUÁRIO      ")
print("=========================================")
print("Dica: Para fechar o programa, deixe o Nome em branco e aperte ENTER.")

while True:
    nome_completo = input("\n1. Digite o Nome Completo (ou ENTER para sair): ").strip()
    
    # Se o nome estiver vazio, quebra o laço e finaliza o script
    if not nome_completo:
        break
        
    cpf_input = input("2. Digite o CPF para login (com ou sem pontos): ").strip()
    senha = input("3. Digite a senha de acesso: ")

    # Remove pontos e traços (salva apenas os números)
    cpf_limpo = re.sub(r'\D', '', cpf_input)

    if not cpf_limpo or not senha:
        print("❌ Erro: Todos os campos são obrigatórios. Tente novamente.")
        print("-" * 41)
        continue
        
    if len(cpf_limpo) != 11:
        print("❌ Erro: O CPF deve conter exatamente 11 números. Tente novamente.")
        print("-" * 41)
        continue
        
    # Criptografa a senha
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = sqlite3.connect("dados.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (username, senha_hash, nome_completo) VALUES (?, ?, ?)",
            (cpf_limpo, senha_hash, nome_completo)
        )
        conn.commit()
        print(f"✅ SUCESSO! O usuário '{nome_completo}' foi criado e já pode acessar.")
        print("-" * 41)
    except sqlite3.IntegrityError:
        print(f"❌ ERRO: O CPF '{cpf_limpo}' já está cadastrado no sistema.")
        print("-" * 41)
    finally:
        conn.close()

# Força o encerramento limpo do processo do Python
sys.exit()
