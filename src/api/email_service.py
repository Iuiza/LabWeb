from pydantic import EmailStr

async def enviar_email_acesso(email_destinatario: EmailStr, senha: str):
    """
    Função mock para "enviar" o e-mail de acesso.
    Numa aplicação real, aqui entraria a lógica de envio de e-mail (ex: com fastapi-mail).
    """
    print("--- SIMULAÇÃO DE ENVIO DE E-MAIL ---")
    print(f"Para: {email_destinatario}")
    print("Assunto: Sua conta na plataforma 'Extensão UNEB em Foco' foi criada!")
    print("\nOlá!")
    print("Sua conta foi criada com sucesso. Use as seguintes credenciais para acessar a plataforma:")
    print(f"  Login: {email_destinatario}")
    print(f"  Senha: {senha}")
    print("É recomendado que você altere sua senha no primeiro acesso.")
    print("-------------------------------------")
    # Retorna True para indicar sucesso na simulação
    return True