from ldap3 import Server, Connection, MODIFY_REPLACE
import os
from dotenv import load_dotenv


# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

def verificar_usuario_existente(conn, nome_usuario):
    # Realizar uma busca no AD inteiro (não especificando uma unidade organizacional)
    conn.search(
        search_base='DC=calf,DC=local',  # Base para buscar em todo o domínio
        search_filter=f'(&(objectClass=user)(CN={nome_usuario}))',  # Filtro de busca para o CN
        attributes=['distinguishedName']  # Retorna o DN completo do usuário
    )
    
    # Verificar se a busca retornou resultados
    return conn.entries

def desabilitar_usuarios_ldap(nomes):
    # Configurar o servidor LDAP (Active Directory)
    server = Server(os.getenv("IP_AD") , get_info='ALL')
    
    # Estabelecer uma conexão com o servidor LDAP usando credenciais administrativas
    conn = Connection(server, user='CN=Administrador GLPI,OU=DTIC,OU=SECAD,DC=calf,DC=local', password= os.getenv("PASSWORD_AD"), auto_bind=True)

    # Verifique se a conexão foi bem-sucedida
    if not conn.bound:
        print("Falha na conexão com o Active Directory.")
        return
    
    # Iterar sobre a lista de nomes para desabilitar os usuários
    for nome_usuario in nomes:
        # Verifique se o usuário existe no AD antes de tentar desabilitá-lo
        usuarios_encontrados = verificar_usuario_existente(conn, nome_usuario)
        
        if not usuarios_encontrados:
            print(f"Usuário {nome_usuario} não encontrado no AD.")
            continue
        
        # O DN do primeiro usuário encontrado será utilizado
        dn = usuarios_encontrados[0].distinguishedName.value
        
        # Tentar desabilitar o usuário (alterando o atributo userAccountControl)
        if conn.modify(dn, {'userAccountControl': [(MODIFY_REPLACE, [514])]}) :
            print(f"Usuário {nome_usuario} desabilitado com sucesso!")
        else:
            print(f"Falha ao desabilitar o usuário {nome_usuario}: {conn.last_error}")
            print(f"Erro LDAP: {conn.result}")
            print(f"Mensagem: {conn.result['description']}")
            print(f"Código de erro: {conn.result['result']}")
    
    # Fechar a conexão
    conn.unbind()

# Exemplo de uso
nomes = [
]
desabilitar_usuarios_ldap(nomes)
