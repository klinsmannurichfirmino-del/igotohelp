from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from .database import Base
from sqlalchemy.orm import relationship

class App(Base):
    __tablename__ = "apps"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    categoria = Column(String)
    descricao = Column(Text)
    arquivo = Column(String)
    status = Column(String, default="pending")
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    avaliacoes = Column(Integer, default=0)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

