from sqlmodel import Session 
from passlib.context import CryptContext 

from app.core.database import engine 
from app.models.usuario import Usuario 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") 

def get_password_hash(password: str): 
    return pwd_context.hash(password) 

def create_user(): 
    print("\n=== Criar Usuário ===") 
    email = input("Email: ").strip() 
    senha = input("Senha: ").strip() 
    role = input("Role (gestor, vendedor, anunciador): ").strip() 

    with Session(engine) as session: 
        hashed = get_password_hash(senha) 
        user = Usuario(email=email, senha_hash=hashed, role=role) 
        session.add(user) 
        session.commit() 
        session.refresh(user) 

    print("\nUsuário criado com sucesso!") 
    print(f"ID: {user.id}") 
    print(f"Email: {user.email}") 
    print(f"Role: {user.role}") 

if __name__ == "__main__": 
    create_user()