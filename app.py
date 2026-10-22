
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort
)
from database import conectar
from mysql.connector import Error
from datetime import date
import os
import secrets

app = Flask(__name__)

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
            cursor.execute(
                """
                SELECT ID_LIVRO, TITULO, ANO_PUBLICACAO, AUTOR
                FROM livros
                WHERE TITULO LIKE %s OR AUTOR LIKE %s
                ORDER BY ID_LIVRO
                """,
                (f"%{busca}%", f"%{busca}%")
            )
        else:
            cursor.execute(
                """
                SELECT ID_LIVRO, TITULO, ANO_PUBLICACAO, AUTOR
                FROM livros
                ORDER BY ID_LIVRO
                """
            )

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
        flash("Preencha o título e a data de publicação.", "erro")
        return render_template(
            "cadastrar_livro.html",
            titulo=titulo,
            ano_publicacao=ano_publicacao,
            autor=autor
        ), 400

    if len(titulo) > 45 or len(autor) > 45:
        flash(
            "Título e autor devem ter no máximo 45 caracteres.",
            "erro"
        )
        return render_template(
            "cadastrar_livro.html",
            titulo=titulo,
            ano_publicacao=ano_publicacao,
            autor=autor
        ), 400

    try:
        date.fromisoformat(ano_publicacao)
    except ValueError:
        flash("Informe uma data de publicação válida.", "erro")
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
            (titulo, ano_publicacao, autor or None)
        )

        conexao.commit()
        flash("Livro cadastrado com sucesso!", "sucesso")

        return redirect(url_for("listar_livros"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao cadastrar o livro.")
        flash("Não foi possível cadastrar o livro.", "erro")

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


@app.route("/livros/editar/<int:id_livro>", methods=["GET", "POST"])
def editar_livro(id_livro):
    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT ID_LIVRO, TITULO, ANO_PUBLICACAO, AUTOR
            FROM livros
            WHERE ID_LIVRO = %s
            """,
            (id_livro,)
        )

        livro = cursor.fetchone()

        if livro is None:
            abort(404)

        if request.method == "GET":
            return render_template("editar_livro.html", livro=livro)

        titulo = request.form.get("titulo", "").strip()
        ano_publicacao = request.form.get(
            "ano_publicacao", ""
        ).strip()
        autor = request.form.get("autor", "").strip()

        if not titulo or not ano_publicacao:
            flash("Preencha o título e a data de publicação.", "erro")
            livro.update({
                "TITULO": titulo,
                "AUTOR": autor,
                "ANO_PUBLICACAO": ano_publicacao
            })

            return render_template(
                "editar_livro.html",
                livro=livro
            ), 400

        if len(titulo) > 45 or len(autor) > 45:
            flash(
                "Título e autor devem ter no máximo 45 caracteres.",
                "erro"
            )
            livro.update({
                "TITULO": titulo,
                "AUTOR": autor,
                "ANO_PUBLICACAO": ano_publicacao
            })

            return render_template(
                "editar_livro.html",
                livro=livro
            ), 400

        try:
            date.fromisoformat(ano_publicacao)
        except ValueError:
            flash("Informe uma data de publicação válida.", "erro")
            livro.update({
                "TITULO": titulo,
                "AUTOR": autor,
                "ANO_PUBLICACAO": ano_publicacao
            })

            return render_template(
                "editar_livro.html",
                livro=livro
            ), 400

        cursor.execute(
            """
            UPDATE livros
            SET TITULO = %s,
                ANO_PUBLICACAO = %s,
                AUTOR = %s
            WHERE ID_LIVRO = %s
            """,
            (titulo, ano_publicacao, autor or None, id_livro)
        )

        conexao.commit()
        flash("Livro atualizado com sucesso!", "sucesso")

        return redirect(url_for("listar_livros"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao editar o livro.")
        flash("Não foi possível atualizar o livro.", "erro")

        return redirect(url_for("listar_livros"))

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


@app.route("/livros/excluir/<int:id_livro>", methods=["POST"])
def excluir_livro(id_livro):
    conexao = conectar()

    if conexao is None:
        flash("Não foi possível conectar ao banco de dados.", "erro")
        return redirect(url_for("listar_livros"))

    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            "DELETE FROM livros WHERE ID_LIVRO = %s",
            (id_livro,)
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            flash("O livro não foi encontrado.", "erro")
        else:
            conexao.commit()
            flash("Livro excluído com sucesso!", "sucesso")

    except Error as erro:
        conexao.rollback()
        app.logger.exception("Erro ao excluir o livro.")

        if getattr(erro, "errno", None) == 1451:
            flash(
                "Este livro possui registros vinculados, possivelmente "
                "empréstimos. Não é possível excluí-lo enquanto esses "
                "vínculos existirem.",
                "erro"
            )
        else:
            flash("Não foi possível excluir o livro.", "erro")

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro inesperado ao excluir o livro.")
        flash("Ocorreu um erro inesperado ao excluir o livro.", "erro")

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()

    return redirect(url_for("listar_livros"))


if __name__ == "__main__":
    app.run(port=5001, debug=True)
