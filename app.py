
from flask import Flask, render_template
from database import conectar

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/livros")
def listar_livros():
    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT ID_LIVRO, TITULO, ANO_PUBLICACAO, AUTOR
            FROM livros
            ORDER BY ID_LIVRO
        """)

        livros = cursor.fetchall()

        return render_template("livros.html", livros=livros)

    except Exception as erro:
        app.logger.error("Erro ao consultar livros: %s", erro)
        return "Ocorreu um erro ao consultar os livros.", 500

    finally:
        if cursor is not None:
            cursor.close()

        conexao.close()


if __name__ == "__main__":
    app.run(port=5001, debug=True)
