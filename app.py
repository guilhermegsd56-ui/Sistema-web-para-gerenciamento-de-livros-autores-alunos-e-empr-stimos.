
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


# ==================================================
# PAINEL INICIAL
# ==================================================


@app.route("/")
def inicio():
    conexao = conectar()

    if conexao is None:
        flash("Não foi possível conectar ao banco de dados.", "erro")
        return render_template(
            "index.html",
            total_livros=0,
            total_autores=0,
            total_alunos=0,
            total_emprestimos=0,
            emprestimos_pendentes=0,
            emprestimos_devolvidos=0
        )

    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute("SELECT COUNT(*) FROM livros")
        total_livros = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM autor")
        total_autores = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM aluno")
        total_alunos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM emprestrimo")
        total_emprestimos = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM emprestrimo WHERE STATUS = %s",
            ("PENDENTE",)
        )
        emprestimos_pendentes = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM emprestrimo WHERE STATUS = %s",
            ("DEVOLVIDO",)
        )
        emprestimos_devolvidos = cursor.fetchone()[0]

        return render_template(
            "index.html",
            total_livros=total_livros,
            total_autores=total_autores,
            total_alunos=total_alunos,
            total_emprestimos=total_emprestimos,
            emprestimos_pendentes=emprestimos_pendentes,
            emprestimos_devolvidos=emprestimos_devolvidos
        )

    except Error as erro:
        print(f"Erro ao carregar o painel: {erro}")
        flash("Não foi possível carregar os indicadores.", "erro")
        return render_template(
            "index.html",
            total_livros=0,
            total_autores=0,
            total_alunos=0,
            total_emprestimos=0,
            emprestimos_pendentes=0,
            emprestimos_devolvidos=0
        )

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()



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

    dados = {
        "titulo": titulo,
        "ano_publicacao": ano_publicacao,
        "autor": autor
    }

    if not titulo or not ano_publicacao:
        flash("Preencha o título e a data de publicação.", "erro")
        return render_template("cadastrar_livro.html", **dados), 400

    if len(titulo) > 45 or len(autor) > 45:
        flash(
            "Título e autor devem ter no máximo 45 caracteres.",
            "erro"
        )
        return render_template("cadastrar_livro.html", **dados), 400

    try:
        data_publicacao = date.fromisoformat(ano_publicacao)

        if data_publicacao > date.today():
            flash("A data de publicação não pode ser futura.", "erro")
            return render_template(
                "cadastrar_livro.html", **dados
            ), 400

    except ValueError:
        flash("Informe uma data de publicação válida.", "erro")
        return render_template("cadastrar_livro.html", **dados), 400

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
            (titulo, data_publicacao, autor or None)
        )

        conexao.commit()
        flash("Livro cadastrado com sucesso!", "sucesso")

        return redirect(url_for("listar_livros"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao cadastrar o livro.")
        flash("Não foi possível cadastrar o livro.", "erro")
        return render_template("cadastrar_livro.html", **dados), 400

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

        livro.update({
            "TITULO": titulo,
            "ANO_PUBLICACAO": ano_publicacao,
            "AUTOR": autor
        })

        if not titulo or not ano_publicacao:
            flash("Preencha o título e a data de publicação.", "erro")
            return render_template("editar_livro.html", livro=livro), 400

        if len(titulo) > 45 or len(autor) > 45:
            flash(
                "Título e autor devem ter no máximo 45 caracteres.",
                "erro"
            )
            return render_template("editar_livro.html", livro=livro), 400

        try:
            data_publicacao = date.fromisoformat(ano_publicacao)

            if data_publicacao > date.today():
                flash("A data de publicação não pode ser futura.", "erro")
                return render_template(
                    "editar_livro.html", livro=livro
                ), 400

        except ValueError:
            flash("Informe uma data de publicação válida.", "erro")
            return render_template("editar_livro.html", livro=livro), 400

        cursor.execute(
            """
            UPDATE livros
            SET TITULO = %s,
                ANO_PUBLICACAO = %s,
                AUTOR = %s
            WHERE ID_LIVRO = %s
            """,
            (titulo, data_publicacao, autor or None, id_livro)
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
        return render_template("cadastrar_autor.html", hoje=hoje)

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
        return render_template("cadastrar_autor.html", **dados), 400

    if len(nome) > 45:
        flash("O nome deve ter no máximo 45 caracteres.", "erro")
        return render_template("cadastrar_autor.html", **dados), 400

    if len(filosofia) > 100:
        flash(
            "A filosofia do autor deve ter no máximo 100 caracteres.",
            "erro"
        )
        return render_template("cadastrar_autor.html", **dados), 400

    try:
        nascimento = date.fromisoformat(data_nascimento)

        if nascimento > date.today():
            flash("A data de nascimento não pode ser futura.", "erro")
            return render_template("cadastrar_autor.html", **dados), 400

    except ValueError:
        flash("Informe uma data de nascimento válida.", "erro")
        return render_template("cadastrar_autor.html", **dados), 400

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
        return render_template("cadastrar_autor.html", **dados), 400

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


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
                "editar_autor.html", autor=dados, hoje=hoje
            ), 400

        if len(nome) > 45:
            flash("O nome deve ter no máximo 45 caracteres.", "erro")
            return render_template(
                "editar_autor.html", autor=dados, hoje=hoje
            ), 400

        if len(filosofia) > 100:
            flash(
                "A filosofia do autor deve ter no máximo 100 caracteres.",
                "erro"
            )
            return render_template(
                "editar_autor.html", autor=dados, hoje=hoje
            ), 400

        try:
            nascimento = date.fromisoformat(data_nascimento)

            if nascimento > date.today():
                flash("A data de nascimento não pode ser futura.", "erro")
                return render_template(
                    "editar_autor.html", autor=dados, hoje=hoje
                ), 400

        except ValueError:
            flash("Informe uma data válida.", "erro")
            return render_template(
                "editar_autor.html", autor=dados, hoje=hoje
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


# ==================================================
# ALUNOS
# ==================================================

def calcular_idade(data_nascimento):
    hoje = date.today()
    idade = hoje.year - data_nascimento.year

    if (hoje.month, hoje.day) < (
        data_nascimento.month,
        data_nascimento.day
    ):
        idade -= 1

    return idade


@app.route("/alunos")
def listar_alunos():
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
                SELECT ID_ALUNO, NOME, IDADE, DATA_NASCIMENTO
                FROM aluno
                WHERE NOME LIKE %s
                ORDER BY NOME
                """,
                (f"%{busca}%",)
            )
        else:
            cursor.execute(
                """
                SELECT ID_ALUNO, NOME, IDADE, DATA_NASCIMENTO
                FROM aluno
                ORDER BY NOME
                """
            )

        alunos = cursor.fetchall()

        return render_template(
            "alunos.html",
            alunos=alunos,
            busca=busca
        )

    except Exception:
        app.logger.exception("Erro ao consultar os alunos.")
        return "Ocorreu um erro ao consultar os alunos.", 500

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


@app.route("/alunos/cadastrar", methods=["GET", "POST"])
def cadastrar_aluno():
    hoje = date.today().isoformat()

    if request.method == "GET":
        return render_template("cadastrar_aluno.html", hoje=hoje)

    nome = request.form.get("nome", "").strip()
    data_nascimento = request.form.get(
        "data_nascimento", ""
    ).strip()

    dados = {
        "nome": nome,
        "data_nascimento": data_nascimento,
        "hoje": hoje
    }

    if not nome or not data_nascimento:
        flash("Preencha todos os campos.", "erro")
        return render_template("cadastrar_aluno.html", **dados), 400

    if len(nome) > 45:
        flash("O nome deve ter no máximo 45 caracteres.", "erro")
        return render_template("cadastrar_aluno.html", **dados), 400

    try:
        nascimento = date.fromisoformat(data_nascimento)

        if nascimento > date.today():
            flash("A data de nascimento não pode ser futura.", "erro")
            return render_template("cadastrar_aluno.html", **dados), 400

        idade = calcular_idade(nascimento)

        if idade > 120:
            flash("Confira a data de nascimento informada.", "erro")
            return render_template("cadastrar_aluno.html", **dados), 400

    except ValueError:
        flash("Informe uma data de nascimento válida.", "erro")
        return render_template("cadastrar_aluno.html", **dados), 400

    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO aluno (NOME, IDADE, DATA_NASCIMENTO)
            VALUES (%s, %s, %s)
            """,
            (nome, idade, nascimento)
        )

        conexao.commit()
        flash("Aluno cadastrado com sucesso!", "sucesso")
        return redirect(url_for("listar_alunos"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao cadastrar o aluno.")
        flash("Não foi possível cadastrar o aluno.", "erro")
        return render_template("cadastrar_aluno.html", **dados), 400

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


@app.route("/alunos/editar/<int:id_aluno>", methods=["GET", "POST"])
def editar_aluno(id_aluno):
    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT ID_ALUNO, NOME, IDADE, DATA_NASCIMENTO
            FROM aluno
            WHERE ID_ALUNO = %s
            """,
            (id_aluno,)
        )

        aluno = cursor.fetchone()

        if aluno is None:
            abort(404)

        hoje = date.today().isoformat()

        if request.method == "GET":
            return render_template(
                "editar_aluno.html",
                aluno=aluno,
                hoje=hoje
            )

        nome = request.form.get("nome", "").strip()
        data_nascimento = request.form.get(
            "data_nascimento", ""
        ).strip()

        dados = {
            "ID_ALUNO": id_aluno,
            "NOME": nome,
            "IDADE": aluno["IDADE"],
            "DATA_NASCIMENTO": data_nascimento
        }

        if not nome or not data_nascimento:
            flash("Preencha todos os campos.", "erro")
            return render_template(
                "editar_aluno.html",
                aluno=dados,
                hoje=hoje
            ), 400

        if len(nome) > 45:
            flash("O nome deve ter no máximo 45 caracteres.", "erro")
            return render_template(
                "editar_aluno.html",
                aluno=dados,
                hoje=hoje
            ), 400

        try:
            nascimento = date.fromisoformat(data_nascimento)

            if nascimento > date.today():
                flash("A data de nascimento não pode ser futura.", "erro")
                return render_template(
                    "editar_aluno.html",
                    aluno=dados,
                    hoje=hoje
                ), 400

            idade = calcular_idade(nascimento)

            if idade > 120:
                flash("Confira a data de nascimento informada.", "erro")
                return render_template(
                    "editar_aluno.html",
                    aluno=dados,
                    hoje=hoje
                ), 400

        except ValueError:
            flash("Informe uma data de nascimento válida.", "erro")
            return render_template(
                "editar_aluno.html",
                aluno=dados,
                hoje=hoje
            ), 400

        cursor.execute(
            """
            UPDATE aluno
            SET NOME = %s,
                IDADE = %s,
                DATA_NASCIMENTO = %s
            WHERE ID_ALUNO = %s
            """,
            (nome, idade, nascimento, id_aluno)
        )

        conexao.commit()
        flash("Aluno atualizado com sucesso!", "sucesso")
        return redirect(url_for("listar_alunos"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao editar o aluno.")
        flash("Não foi possível atualizar o aluno.", "erro")
        return redirect(url_for("listar_alunos"))

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


@app.route("/alunos/excluir/<int:id_aluno>", methods=["POST"])
def excluir_aluno(id_aluno):
    conexao = conectar()

    if conexao is None:
        flash("Não foi possível conectar ao banco de dados.", "erro")
        return redirect(url_for("listar_alunos"))

    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            "DELETE FROM aluno WHERE ID_ALUNO = %s",
            (id_aluno,)
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            flash("O aluno não foi encontrado.", "erro")
        else:
            conexao.commit()
            flash("Aluno excluído com sucesso!", "sucesso")

    except Error as erro:
        conexao.rollback()
        app.logger.exception("Erro ao excluir o aluno.")

        if getattr(erro, "errno", None) == 1451:
            flash(
                "Este aluno possui registros vinculados, possivelmente "
                "empréstimos. Não é possível excluí-lo enquanto esses "
                "vínculos existirem.",
                "erro"
            )
        else:
            flash("Não foi possível excluir o aluno.", "erro")

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro inesperado ao excluir o aluno.")
        flash("Ocorreu um erro inesperado ao excluir o aluno.", "erro")

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()

    return redirect(url_for("listar_alunos"))


# ==================================================
# EMPRÉSTIMOS
# ==================================================


@app.route("/emprestimos")
def listar_emprestimos():
    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)

        busca = request.args.get("busca", "").strip()
        status = request.args.get("status", "TODOS").strip().upper()

        # Aceita apenas os filtros disponíveis.
        if status not in ("TODOS", "PENDENTE", "DEVOLVIDO"):
            status = "TODOS"

        consulta = """
            SELECT
                e.ID_IMPRESTIMO,
                e.DATA_EMPRESTIMO,
                e.DATA_DEVOLUCAO,
                e.STATUS,
                e.ID_ALUNO,
                e.ID_LIVRO,
                a.NOME AS NOME_ALUNO,
                l.TITULO AS TITULO_LIVRO
            FROM emprestrimo e
            LEFT JOIN aluno a ON a.ID_ALUNO = e.ID_ALUNO
            LEFT JOIN livros l ON l.ID_LIVRO = e.ID_LIVRO
            WHERE 1 = 1
        """

        parametros = []

        # Filtro por situação do empréstimo.
        if status != "TODOS":
            consulta += " AND e.STATUS = %s"
            parametros.append(status)

        # Pesquisa por aluno, livro ou status.
        if busca:
            consulta += """
                AND (
                    a.NOME LIKE %s
                    OR l.TITULO LIKE %s
                    OR e.STATUS LIKE %s
                )
            """

            parametros.extend([
                f"%{busca}%",
                f"%{busca}%",
                f"%{busca}%"
            ])

        consulta += " ORDER BY e.ID_IMPRESTIMO DESC"

        cursor.execute(consulta, tuple(parametros))
        emprestimos = cursor.fetchall()

        return render_template(
            "emprestimos.html",
            emprestimos=emprestimos,
            busca=busca,
            status=status
        )

    except Exception:
        app.logger.exception("Erro ao consultar empréstimos.")
        return "Ocorreu um erro ao consultar os empréstimos.", 500

    finally:
        if cursor is not None:
            cursor.close()

        conexao.close()



@app.route("/emprestimos/cadastrar", methods=["GET", "POST"])
def cadastrar_emprestimo():
    conexao = conectar()

    if conexao is None:
        return "Não foi possível conectar ao banco de dados.", 500

    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            "SELECT ID_ALUNO, NOME FROM aluno ORDER BY NOME"
        )
        alunos = cursor.fetchall()

        cursor.execute(
            "SELECT ID_LIVRO, TITULO FROM livros ORDER BY TITULO"
        )
        livros = cursor.fetchall()

        hoje = date.today().isoformat()

        if request.method == "GET":
            return render_template(
                "cadastrar_emprestimo.html",
                alunos=alunos,
                livros=livros,
                hoje=hoje,
                dados={}
            )

        id_aluno_texto = request.form.get("id_aluno", "").strip()
        id_livro_texto = request.form.get("id_livro", "").strip()
        data_emprestimo_texto = request.form.get(
            "data_emprestimo", ""
        ).strip()
        data_devolucao_texto = request.form.get(
            "data_devolucao", ""
        ).strip()

        dados = {
            "id_aluno": id_aluno_texto,
            "id_livro": id_livro_texto,
            "data_emprestimo": data_emprestimo_texto,
            "data_devolucao": data_devolucao_texto
        }

        if not all([
            id_aluno_texto,
            id_livro_texto,
            data_emprestimo_texto,
            data_devolucao_texto
        ]):
            flash("Preencha todos os campos.", "erro")
            return render_template(
                "cadastrar_emprestimo.html",
                alunos=alunos,
                livros=livros,
                hoje=hoje,
                dados=dados
            ), 400

        try:
            id_aluno = int(id_aluno_texto)
            id_livro = int(id_livro_texto)
            data_emprestimo = date.fromisoformat(
                data_emprestimo_texto
            )
            data_devolucao = date.fromisoformat(
                data_devolucao_texto
            )
        except ValueError:
            flash("Confira os dados informados.", "erro")
            return render_template(
                "cadastrar_emprestimo.html",
                alunos=alunos,
                livros=livros,
                hoje=hoje,
                dados=dados
            ), 400

        if data_devolucao < data_emprestimo:
            flash(
                "A data prevista de devolução não pode ser anterior "
                "à data do empréstimo.",
                "erro"
            )
            return render_template(
                "cadastrar_emprestimo.html",
                alunos=alunos,
                livros=livros,
                hoje=hoje,
                dados=dados
            ), 400

        cursor.execute(
            "SELECT ID_ALUNO FROM aluno WHERE ID_ALUNO = %s",
            (id_aluno,)
        )
        if cursor.fetchone() is None:
            flash("O aluno selecionado não existe.", "erro")
            return render_template(
                "cadastrar_emprestimo.html",
                alunos=alunos,
                livros=livros,
                hoje=hoje,
                dados=dados
            ), 400

        cursor.execute(
            "SELECT ID_LIVRO FROM livros WHERE ID_LIVRO = %s",
            (id_livro,)
        )
        if cursor.fetchone() is None:
            flash("O livro selecionado não existe.", "erro")
            return render_template(
                "cadastrar_emprestimo.html",
                alunos=alunos,
                livros=livros,
                hoje=hoje,
                dados=dados
            ), 400

        cursor.execute(
            """
            SELECT ID_IMPRESTIMO
            FROM emprestrimo
            WHERE ID_LIVRO = %s AND STATUS = 'PENDENTE'
            LIMIT 1
            """,
            (id_livro,)
        )

        if cursor.fetchone() is not None:
            flash(
                "Este livro já possui um empréstimo pendente.",
                "erro"
            )
            return render_template(
                "cadastrar_emprestimo.html",
                alunos=alunos,
                livros=livros,
                hoje=hoje,
                dados=dados
            ), 400

        cursor.execute(
            """
            INSERT INTO emprestrimo
                (DATA_EMPRESTIMO, DATA_DEVOLUCAO,
                 ID_ALUNO, ID_LIVRO, STATUS)
            VALUES (%s, %s, %s, %s, 'PENDENTE')
            """,
            (
                data_emprestimo,
                data_devolucao,
                id_aluno,
                id_livro
            )
        )

        conexao.commit()
        flash("Empréstimo cadastrado com sucesso!", "sucesso")
        return redirect(url_for("listar_emprestimos"))

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao cadastrar empréstimo.")
        flash("Não foi possível cadastrar o empréstimo.", "erro")
        return redirect(url_for("cadastrar_emprestimo"))

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()


@app.route(
    "/emprestimos/devolver/<int:id_emprestimo>",
    methods=["POST"]
)
def devolver_emprestimo(id_emprestimo):
    conexao = conectar()

    if conexao is None:
        flash("Não foi possível conectar ao banco de dados.", "erro")
        return redirect(url_for("listar_emprestimos"))

    cursor = None

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            UPDATE emprestrimo
            SET STATUS = 'DEVOLVIDO'
            WHERE ID_IMPRESTIMO = %s
              AND STATUS = 'PENDENTE'
            """,
            (id_emprestimo,)
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            flash(
                "Empréstimo não encontrado ou já devolvido.",
                "erro"
            )
        else:
            conexao.commit()
            flash("Devolução registrada com sucesso!", "sucesso")

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao registrar devolução.")
        flash("Não foi possível registrar a devolução.", "erro")

    finally:
        if cursor is not None:
            cursor.close()
        conexao.close()

    return redirect(url_for("listar_emprestimos"))


# ==================================================
# EXECUTAR A APLICAÇÃO
# ==================================================

if __name__ == "__main__":
    app.run(port=5001, debug=True)
