
import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel


DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria a tabela se ela ainda não existir.
    # Se o banco estiver indisponível, a aplicação não inicia.
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

    yield


app = FastAPI(
    title="ESSS Tasks API",
    description="API de tarefas para demonstrar Docker Compose e CI/CD",
    version="1.0.0",
    lifespan=lifespan,
)


class TaskCreate(BaseModel):
    title: str
    description: str = ""


@app.get("/")
def root():
    return {"message": "ESSS Tasks API está funcionando"}


@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Banco de dados indisponível",
        )


@app.get("/tasks")
def list_tasks():
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, description, created_at
                FROM tasks
                ORDER BY id
                """
            ).fetchall()
            return rows
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar as tarefas",
        )


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO tasks (title, description)
                VALUES (%s, %s)
                RETURNING id, title, description, created_at
                """,
                (task.title, task.description),
            ).fetchone()
            return row
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível salvar a tarefa",
        )
