## core/db.py

import asyncpg
import logging

from contextlib import asynccontextmanager
from config.settings import config

pool: asyncpg.Pool | None = None

async def fetch(query: str, *args):
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def fetchrow(query: str, *args):
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)
    
async def fetchval(query: str, *args):
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)

async def execute(query: str, *args):
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

@asynccontextmanager
async def db_transaction():
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn

@asynccontextmanager
async def transaction():
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
            
@asynccontextmanager
async def db_connection():
    async with pool.acquire() as conn:
        yield conn
        
async def init_db_pool():
    global pool
    try:
        if pool is None:
            pool = await asyncpg.create_pool(
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                host=config.DB_HOST,
                port=config.DB_PORT,
                min_size=1,
                max_size=20,
                ssl='require',
            )
            logging.info("[ DB ] -------------------- Connection pool created")
        return pool
    except Exception as e:
        logging.error(f"❌ Gagal membuat database connection pool: {e}")
        return None

async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None
        logging.info("[ DB ] -------------------- Connection pool closed")
