from sqlmodel import  Session 
from app.models.usuario import  Usuario 
from app.core.database import  engine 
from app.services.security import  get_password_hash 


def main ():
    print("\n=== CRIAÇÃO DE USUÁRIO NA VPS ===" ) 

    email = input("Email: " ).strip() 
    senha = input("Senha: " ).strip() 
    role = input("Role (gestor / vendedor / anuncios): " ).strip() 

    senha_hash = get_password_hash(senha) 

    with Session(engine) as  session: 
        user = Usuario( 
            email=email, 
            senha_hash=senha_hash, 
            role=role, 
            is_active=True 
        ) 
        session.add(user) 
        session.commit() 
        session.refresh(user) 

        print("\nUsuário criado com sucesso!" ) 
        print(f"ID: {user.id }") 
        print(f"Email: {user.email} ") 
        print(f"Role: {user.role} ") 
        print("===========================================" ) 


if __name__ == "__main__" : 
    main()