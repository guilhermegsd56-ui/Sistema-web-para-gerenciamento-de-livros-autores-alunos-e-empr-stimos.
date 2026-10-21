
import mysql.connector
from mysql.connector import Error


def conectar():
    try:
        conexao = mysql.connector.connect(
            host="localhost",
            port=3307,
            user="root",
            password="",
            database="biblioteca_inteligente"
        )

        if conexao.is_connected():
            return conexao

    except Error as erro:
        print(f"Erro ao conectar ao MySQL: {erro}")

    return None
