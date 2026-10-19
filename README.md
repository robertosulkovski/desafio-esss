# ESSS Challenge — CI/CD com GitHub Actions e Docker Compose

Projeto desenvolvido como desafio técnico para automatizar a validação e a implantação de uma aplicação em um servidor Linux na AWS EC2, utilizando GitHub Actions, Docker Compose e conexão SSH.

## Objetivo

Implementar um pipeline CI/CD que valide o código e, após um push para a branch `main`, transfira os arquivos da aplicação para uma instância EC2, atualize os containers e verifique a disponibilidade da API por meio de um health check com tentativas limitadas.

## Arquitetura

A aplicação utiliza dois serviços definidos no `docker-compose.yml`:

- **API:** aplicação REST desenvolvida com FastAPI e executada pelo Uvicorn.
- **PostgreSQL:** banco de dados responsável pela persistência das tarefas.

A API depende da condição de saúde do PostgreSQL para iniciar. O banco utiliza o volume nomeado `postgres_data` para preservar os dados entre recriações dos containers.

### Tecnologias utilizadas

- Python
- FastAPI e Uvicorn
- PostgreSQL
- Docker e Docker Compose
- Git e GitHub
- GitHub Actions
- Linux e SSH
- AWS EC2

## Estrutura do projeto

```text
.
├── .github/
│   └── workflows/
│       └── deploy.yml
├── api/
│   ├── main.py
│   └── requirements.txt
├── scripts/
│   └── healthcheck.sh
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Como funciona o pipeline

O workflow está definido em `.github/workflows/deploy.yml` e é acionado por pushes para a branch `main`. Também permite execução manual pelo GitHub Actions, embora a implantação esteja condicionada a um evento de push para `main`.

### 1. Validação

O job `Validate application`:

1. Obtém o código do repositório.
2. Configura o Python.
3. Instala as dependências da API.
4. Verifica a sintaxe dos arquivos Python.
5. Valida a configuração do Docker Compose.

### 2. Implantação

Após a validação, o job `Deploy to EC2`:

1. Lê as configurações e a chave SSH armazenadas no GitHub.
2. Estabelece uma conexão SSH com a instância EC2.
3. Empacota os arquivos do repositório, excluindo `.git`, `.env`, ambientes virtuais e caches Python.
4. Transfere o pacote para o servidor.
5. Extrai os arquivos no diretório da aplicação.
6. Executa `sudo docker compose up -d --build`.
7. Verifica o estado dos serviços.
8. Executa `scripts/healthcheck.sh` no servidor remoto.

### 3. Health check

O script `scripts/healthcheck.sh` consulta o endpoint `/health` da API.

- Aceita exclusivamente HTTP 200 como sucesso.
- Realiza até 12 tentativas por padrão.
- Aguarda 5 segundos entre tentativas.
- Retorna código de saída diferente de zero se o serviço não ficar saudável dentro do limite.

Esse comportamento permite que uma falha no health check faça o job de implantação falhar.

## Endpoints da API

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/` | Mensagem de funcionamento da API |
| GET | `/health` | Verifica a conexão com o banco de dados |
| GET | `/tasks` | Lista as tarefas |
| POST | `/tasks` | Cria uma tarefa |

O endpoint `/health` retorna HTTP 200 quando a API consegue consultar o PostgreSQL. Caso o banco esteja indisponível, retorna HTTP 503.

A documentação interativa do FastAPI fica disponível em `/docs` quando a aplicação está em execução.

## Configuração local

### Pré-requisitos

- Git
- Docker Engine
- Docker Compose v2

### 1. Clonar o repositório

```bash
git clone https://github.com/robertosulkovski/desafio-esss.git
cd desafio-esss
```

### 2. Configurar a senha do PostgreSQL

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Edite o `.env` e defina uma senha para o PostgreSQL:

```dotenv
POSTGRES_PASSWORD=sua_senha_local
```

Use uma senha apropriada para seu ambiente. Não publique o arquivo `.env` no GitHub.

### 3. Iniciar os serviços

```bash
docker compose up -d --build
```

Verifique os containers:

```bash
docker compose ps
```

### 4. Testar a API

```bash
curl -i http://localhost:8000/health
```

A resposta esperada quando a API e o banco estão saudáveis é HTTP 200, com conteúdo semelhante a:

```json
{
  "status": "ok",
  "database": "connected"
}
```

Para consultar a documentação interativa, acesse `http://localhost:8000/docs`.

### 5. Executar o health check

```bash
./scripts/healthcheck.sh http://localhost:8000/health 12 5
```

Os argumentos são, respectivamente, a URL, o número máximo de tentativas e o intervalo entre tentativas em segundos.

### 6. Encerrar os serviços

```bash
docker compose down
```

O comando acima preserva o volume nomeado do PostgreSQL. Para apagar também os dados persistidos, seria necessário remover explicitamente o volume; isso é destrutivo e não deve ser feito se os dados precisarem ser mantidos.

## Configuração do GitHub Actions

O workflow utiliza um runner self-hosted com acesso ao Docker e conectividade SSH com a instância de aplicação.

### Preparação do servidor EC2

**Antes da primeira implantação**, configure o arquivo `.env` no servidor EC2, no diretório `/home/ubuntu/desafio-esss/.env`.

O arquivo deve conter a senha do PostgreSQL:

```dotenv
POSTGRES_PASSWORD=sua_senha_forte
```

Substitua `sua_senha_forte` por uma senha real e segura. Não use literalmente esse exemplo como senha de produção.

Esse arquivo deve ser criado e mantido diretamente no servidor, pois o pipeline exclui `.env` do pacote transferido. Portanto, o arquivo precisa existir antes de executar o primeiro deploy.

Mantenha a mesma senha nas implantações seguintes para preservar a compatibilidade com o banco existente. Alterar apenas a variável no `.env` não altera automaticamente a senha de um usuário PostgreSQL já inicializado.

O `.env` não deve ser versionado nem incluído no repositório.

### Repository Variables

Configure os seguintes itens em **Settings → Secrets and variables → Actions → Variables** no repositório:

| Nome | Conteúdo |
|---|---|
| `EC2_HOST` | Endereço IP ou hostname alcançável pelo runner |
| `EC2_USER` | Usuário SSH do servidor |
| `EC2_SSH_PORT` | Porta SSH do servidor, normalmente `22` |

### Repository Secrets

Configure em **Settings → Secrets and variables → Actions → Secrets**:

| Nome | Conteúdo |
|---|---|
| `EC2_SSH_PRIVATE_KEY` | Chave privada SSH usada pelo runner para acessar o servidor de aplicação |

A chave privada deve permanecer no GitHub Secrets e não deve ser incluída no repositório, no README ou nos logs.

O servidor de aplicação deve aceitar a chave pública correspondente. Os grupos de segurança da AWS devem permitir SSH do runner para o servidor de aplicação, e o runner precisa conseguir executar Docker e Docker Compose.

### Segurança

- O `.env` é excluído pelo `.gitignore`.
- A implantação exclui `.env` do pacote transferido.
- A chave privada SSH é fornecida pelo GitHub Secrets e escrita temporariamente em um arquivo com permissões restritas.
- A senha do banco não deve ser armazenada no código ou no workflow.
- Em ambientes de produção, a chave do servidor SSH deve ser validada por fingerprint obtida por um canal confiável.

## Idempotência e persistência

O workflow pode ser executado repetidamente para atualizar a aplicação usando Docker Compose. O Compose gerencia os serviços declarados e evita a criação de containers independentes a cada execução. O volume nomeado `postgres_data` preserva os dados do banco durante a recriação dos containers.

A tabela `tasks` é criada pela aplicação com `CREATE TABLE IF NOT EXISTS`, evitando recriar a tabela se ela já existir.

## Evidências da execução

O workflow foi executado com sucesso no GitHub Actions após o commit que adicionou o script reutilizável de health check.

**Execução do workflow:** [Consultar GitHub Actions](https://github.com/robertosulkovski/desafio-esss/actions)

### Vídeo de demonstração

_A adicionar após a gravação._

O vídeo deverá demonstrar o push para `main`, a execução dos jobs de validação e implantação, o resultado do health check e uma requisição bem-sucedida à API implantada.

## Autor

**Roberto Sulkovski Roxo**

Repositório: [github.com/robertosulkovski/desafio-esss](https://github.com/robertosulkovski/desafio-esss)
