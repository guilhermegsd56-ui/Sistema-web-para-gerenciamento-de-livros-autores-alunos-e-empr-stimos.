
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


# ==================================================
# LIVROS
# ==================================================

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


# ==================================================
# AUTORES
# ==================================================

@app.route("/autores")
def listar_autores():
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
                SELECT ID_AUTOR, NOME, FILOSOFIA_DO_AUTOR,
                       DATA_NASCIMENTO
                FROM autor
                WHERE NOME LIKE %s
                   OR FILOSOFIA_DO_AUTOR LIKE %s
                ORDER BY NOME
                """,
                (f"%{busca}%", f"%{busca}%")
            )
        else:
            cursor.execute(
                """
                SELECT ID_AUTOR, NOME, FILOSOFIA_DO_AUTOR,
                       DATA_NASCIMENTO
                FROM autor
                ORDER BY NOME
                """
            )

        autores = cursor.fetchall()

        return render_template(
            "autores.html",
            autores=autores,
            busca=busca
        )

    except Exception:
        app.logger.exception("Erro ao consultar os autores.")
        return "Ocorreu um erro ao consultar os autores.", 500

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


@app.route("/autores/cadastrar", methods=["GET", "POST"])
def cadastrar_autor():
    hoje = date.today().isoformat()

    if request.method == "GET":
        return render_template(
            "cadastrar_autor.html",
            hoje=hoje
        )

    nome = request.form.get("nome", "").strip()
    filosofia = request.form.get("filosofia", "").strip()
    data_nascimento = request.form.get(
        "data_nascimento", ""
    ).strip()

    dados = {
        "nome": nome,
        "filosofia": filosofia,
        "data_nascimento": data_nascimento,
        "hoje": hoje
    }

    if not nome or not filosofia or not data_nascimento:
        flash("Preencha todos os campos do formulário.", "erro")
        return render_template(
            "cadastrar_autor.html",
            **dados
        ), 400

    if len(nome) > 45:
        flash("O nome deve ter no máximo 45 caracteres.", "erro")
        return render_template(
            "cadastrar_autor.html",
            **dados
        ), 400

    if len(filosofia) > 100:
        flash(
            "A filosofia do autor deve ter no máximo 100 caracteres.",
            "erro"
        )
        return render_template(
            "cadastrar_autor.html",
            **dados
        ), 400

    try:
        nascimento = date.fromisoformat(data_nascimento)

        if nascimento > date.today():
            flash(
                "A data de nascimento não pode ser futura.",
                "erro"
            )
            return render_template(
                "cadastrar_autor.html",
                **dados
            ), 400

    except ValueError:
        flash("Informe uma data de nascimento válida.", "erro")
        return render_template(
            "cadastrar_autor.html",
            **dados
        ), 400

    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO autor
                (NOME, FILOSOFIA_DO_AUTOR, DATA_NASCIMENTO)
            VALUES (%s, %s, %s)
            """,
            (nome, filosofia, nascimento)
        )

        conexao.commit()
        flash("Autor cadastrado com sucesso!", "sucesso")

        return redirect(url_for("listar_autores"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao cadastrar o autor.")
        flash("Não foi possível cadastrar o autor.", "erro")

        return render_template(
            "cadastrar_autor.html",
            **dados
        ), 400

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


# ==================================================
# EDITAR AUTORES
# ==================================================

@app.route("/autores/editar/<int:id_autor>", methods=["GET", "POST"])
def editar_autor(id_autor):
    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT ID_AUTOR, NOME, FILOSOFIA_DO_AUTOR,
                   DATA_NASCIMENTO
            FROM autor
            WHERE ID_AUTOR = %s
            """,
            (id_autor,)
        )

        autor = cursor.fetchone()

        if autor is None:
            abort(404)

        hoje = date.today().isoformat()

        if request.method == "GET":
            return render_template(
                "editar_autor.html",
                autor=autor,
                hoje=hoje
            )

        nome = request.form.get("nome", "").strip()
        filosofia = request.form.get("filosofia", "").strip()
        data_nascimento = request.form.get(
            "data_nascimento", ""
        ).strip()

        dados = {
            "ID_AUTOR": id_autor,
            "NOME": nome,
            "FILOSOFIA_DO_AUTOR": filosofia,
            "DATA_NASCIMENTO": data_nascimento
        }

        if not nome or not filosofia or not data_nascimento:
            flash("Preencha todos os campos.", "erro")
            return render_template(
                "editar_autor.html",
                autor=dados,
                hoje=hoje
            ), 400

        if len(nome) > 45:
            flash("O nome deve ter no máximo 45 caracteres.", "erro")
            return render_template(
                "editar_autor.html",
                autor=dados,
                hoje=hoje
            ), 400

        if len(filosofia) > 100:
            flash(
                "A filosofia do autor deve ter no máximo 100 caracteres.",
                "erro"
            )
            return render_template(
                "editar_autor.html",
                autor=dados,
                hoje=hoje
            ), 400

        try:
            nascimento = date.fromisoformat(data_nascimento)

            if nascimento > date.today():
                flash(
                    "A data de nascimento não pode ser futura.",
                    "erro"
                )
                return render_template(
                    "editar_autor.html",
                    autor=dados,
                    hoje=hoje
                ), 400

        except ValueError:
            flash("Informe uma data válida.", "erro")
            return render_template(
                "editar_autor.html",
                autor=dados,
                hoje=hoje
            ), 400

        cursor.execute(
            """
            UPDATE autor
            SET NOME = %s,
                FILOSOFIA_DO_AUTOR = %s,
                DATA_NASCIMENTO = %s
            WHERE ID_AUTOR = %s
            """,
            (nome, filosofia, nascimento, id_autor)
        )

        conexao.commit()
        flash("Autor atualizado com sucesso!", "sucesso")

        return redirect(url_for("listar_autores"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao editar o autor.")
        flash("Não foi possível atualizar o autor.", "erro")
        return redirect(url_for("listar_autores"))

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


# ==================================================
# EXCLUIR AUTORES
# ==================================================

@app.route("/autores/excluir/<int:id_autor>", methods=["POST"])
def excluir_autor(id_autor):
    conexao = conectar()

    if conexao is None:
        flash("Não foi possível conectar ao banco de dados.", "erro")
        return redirect(url_for("listar_autores"))

    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            "DELETE FROM autor WHERE ID_AUTOR = %s",
            (id_autor,)
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            flash("O autor não foi encontrado.", "erro")
        else:
            conexao.commit()
            flash("Autor excluído com sucesso!", "sucesso")

    except Error as erro:
        conexao.rollback()
        app.logger.exception("Erro ao excluir o autor.")

        if getattr(erro, "errno", None) == 1451:
            flash(
                "Este autor possui registros vinculados e não pode "
                "ser excluído enquanto esses vínculos existirem.",
                "erro"
            )
        else:
            flash("Não foi possível excluir o autor.", "erro")

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro inesperado ao excluir o autor.")
        flash("Ocorreu um erro inesperado ao excluir o autor.", "erro")

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()

    return redirect(url_for("listar_autores"))


if __name__ == "__main__":
    app.run(port=5001, debug=True)
