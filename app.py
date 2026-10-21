
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)
from database import conectar

import os
import secrets

app = Flask(__name__)

# Configure SECRET_KEY como variável de ambiente em produção.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    secrets.token_hex(32)
)


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
        busca = request.args.get("busca", "").strip()

        if busca:
            consulta = """
                SELECT ID_LIVRO, TITULO, ANO_PUBLICACAO, AUTOR
                FROM livros
                WHERE TITULO LIKE %s OR AUTOR LIKE %s
                ORDER BY ID_LIVRO
            """

            termo = f"%{busca}%"
            cursor.execute(consulta, (termo, termo))

        else:
            consulta = """
                SELECT ID_LIVRO, TITULO, ANO_PUBLICACAO, AUTOR
                FROM livros
                ORDER BY ID_LIVRO
            """

            cursor.execute(consulta)

        livros = cursor.fetchall()

        return render_template(
            "livros.html",
            livros=livros,
            busca=busca
        )

    except Exception:
        app.logger.exception("Erro ao consultar os livros.")
        return "Ocorreu um erro ao consultar os livros.", 500

    finally:
        if cursor is not None:
            cursor.close()

        conexao.close()


@app.route("/livros/cadastrar", methods=["GET", "POST"])
def cadastrar_livro():
    if request.method == "GET":
        return render_template("cadastrar_livro.html")

    titulo = request.form.get("titulo", "").strip()
    ano_publicacao = request.form.get(
        "ano_publicacao", ""
    ).strip()
    autor = request.form.get("autor", "").strip()

    if not titulo or not ano_publicacao:
        flash(
            "Preencha o título e a data de publicação.",
            "erro"
        )
        return render_template(
            "cadastrar_livro.html",
            titulo=titulo,
            ano_publicacao=ano_publicacao,
            autor=autor
        ), 400

    if len(titulo) > 45 or len(autor) > 45:
        flash(
            "O título e o autor devem ter no máximo 45 caracteres.",
            "erro"
        )
        return render_template(
            "cadastrar_livro.html",
            titulo=titulo,
            ano_publicacao=ano_publicacao,
            autor=autor
        ), 400

    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO livros (TITULO, ANO_PUBLICACAO, AUTOR)
            VALUES (%s, %s, %s)
            """,
            (
                titulo,
                ano_publicacao,
                autor or None
            )
        )

        conexao.commit()

        flash("Livro cadastrado com sucesso!", "sucesso")
        return redirect(url_for("listar_livros"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao cadastrar o livro.")

        flash(
            "Não foi possível cadastrar o livro. "
            "Confira os dados e tente novamente.",
            "erro"
        )

        return render_template(
            "cadastrar_livro.html",
            titulo=titulo,
            ano_publicacao=ano_publicacao,
            autor=autor
        ), 400

    finally:
        if cursor is not None:
            cursor.close()

        conexao.close()


if __name__ == "__main__":
    app.run(port=5001, debug=True)
