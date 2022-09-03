import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from dateutil.relativedelta import relativedelta
from functools import wraps

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# SQLiteの使用
db = SQL("sqlite:///todo.db")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ユーザーidがない場合
        if session.get("user_id") is None:
            # ログインページに送る
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    return render_template("apology.html", top=code, bottom=message)

@app.route("/")
@login_required
def home():
    # データベースからtodoとwillを取得、willの早い順に並べる
    result = db.execute("SELECT todo, will FROM todos WHERE user_id = ? ORDER BY will", session["user_id"])
    # 現在時刻を取得
    now = datetime.datetime.now()
    # 残日数のリストを宣言する
    diff = []
    # データベースから取得したデータを1行ずつ処理する
    for row in result:
        # willを文字列型からdatetime型に変換する
        row["will"] =datetime.datetime.strptime(row["will"],'%Y-%m-%d %H:%M:%S')
        # willから現在時刻を引く
        d = row["will"] - now
        # リストの最後にdの日を追加する
        diff.append(d.days)
        # willを文字列型に変換し、時刻を捨て日付のみにする
        row["will"] = row["will"].strftime('%Y-%m-%d')
    # データベースから取得したタイトルと期限、残日数のリストを送り、home.htmlを表示する
    return render_template("home.html", result = result, diff = diff)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    # リクエストメゾットがPOSTの場合、以下の処理を行う
    if request.method == "POST":
        # todoに入力がない場合エラーを返す
        if not request.form.get("todo"):
            return apology("タイトルを入力してください", 400)
        # intervalに入力がない場合エラーを返す
        elif not request.form.get("interval"):
            return apology("間隔を入力してください", 400)
        # didに入力がない場合エラーを返す
        elif not request.form.get("did"):
            return apology("最後に行った日を入力してください", 400)
        # 同じタイトル、ユーザーidのtodoがある場合エラーを返す
        elif len(db.execute("SELECT * FROM todos WHERE todo = ? AND user_id = ?", request.form.get("todo"),session["user_id"])) != 0:
            return apology("同じ名前のTODOが既にあります", 400)
        # 初期化する
        interval_month = 0
        interval_week = 0
        interval_day = 0
        # unitがmonthの場合、intervalをinterval_monthに入れる
        if request.form.get("unit") == "month":
            interval_month = int(request.form.get("interval"))
        # unitがweekの場合、intervalをinterval_weekに入れる
        elif request.form.get("unit") == "week":
            interval_week =  int(request.form.get("interval"))
        # それ以外（unitがday）の場合、intervalをinterval_dayに入れる
        else:
            interval_day = int(request.form.get("interval"))
        # didを文字列型からdatetime型に変換する
        did = datetime.datetime.strptime(request.form.get("did"), '%Y-%m-%d')
        # didにinterval_monthの月、interval_weekの週、interval_dayの日を足す
        will = did + relativedelta(months = interval_month, weeks = interval_week, days = interval_day)
        # todosにuser_id, todo, interval_month,interval_week, interval_day, did, willを挿入する
        db.execute("INSERT INTO todos (user_id, todo, interval_month,interval_week, interval_day, did, will) VALUES (?,?,?,?,?,?,?)",
                   session["user_id"], request.form.get("todo"), interval_month, interval_week, interval_day, request.form.get("did"), will)
        # メッセージを出す
        flash("追加しました")
        # ホームに戻す
        return redirect("/")
    #それ以外の場合add.htmlを表示する
    else:
        return render_template("add.html")


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    # リクエストメゾットがPOSTの場合
    if request.method == "POST":
        # 入力されたtodo、ログイン中のユーザーidの行を削除する
        db.execute("DELETE FROM todos WHERE todo = ? AND user_id = ?",request.form.get("todo"), session["user_id"])
        #メッセージ
        flash("削除しました")
        return redirect("/")
    # リクエストメゾットがGETの場合
    else:
        # ログイン中のユーザーidのタイトルを取得し、delete.htmlを表示する
        return render_template("delete.html", todos=db.execute("SELECT todo FROM todos WHERE user_id = ?", session["user_id"]))

@app.route("/update", methods=["GET", "POST"])
@login_required
def update():
    # リクエストメゾットがPOSTの場合
    if request.method == "POST":
        todo = request.form.get("todo")
        # 現在時刻を取得
        did = datetime.datetime.now()
        # 入力されたtodoとユーザーネームのinterval_month, interval_week, interval_dayを取得
        result = db.execute("SELECT interval_month, interval_week, interval_day FROM todos WHERE todo = ? AND user_id = ?", todo, session["user_id"])
        # 現在時刻didにinterval_monthの月、interval_weekの週、interval_dayの日を足す
        will = did + relativedelta(months = result[0]['interval_month'], weeks = result[0]["interval_week"], days = result[0]["interval_day"])
        # didとwillを更新する
        db.execute("UPDATE todos SET did = ?, will = ? WHERE todo = ? AND user_id = ?",did , will, todo , session["user_id"])
        #メッセージ
        flash("更新しました")
        # ホームに戻す
        return redirect("/")
    #リクエストメゾットがGETの場合、
    else:
        # ログイン中のユーザーidのタイトルを取得し、update.htmlを表示する
        return render_template("update.html", todos=db.execute("SELECT todo FROM todos WHERE user_id = ?", session["user_id"]))


@app.route("/login", methods=["GET", "POST"])
def login():
    #　ユーザーidをクリアする
    session.clear()
    # POSTの場合
    if request.method == "POST":
        # ユーザーネームが入力されていない
        if not request.form.get("username"):
            return apology("ユーザーネームを入力してください", 403)
        # パスワードが入力されていない
        elif not request.form.get("password"):
            return apology("パスワードを入力してください", 403)
        # 入力されたユーザーネームのデータを取得
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        # ユーザーネームとパスワードが正しいか確認
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("ユーザーネームまたはパスワードが無効です", 403)
        # ユーザーを記憶する
        session["user_id"] = rows[0]["id"]
        #メッセージ
        flash("ログインしました")
        # ホームに送る
        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    #　ユーザーidをクリアする
    session.clear()
    # ログインページに送る
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # POSTの場合
    if request.method == "POST":
        # ユーザーネームが入力されていない
        if not request.form.get("username"):
            return apology("ユーザーネームを入力してください", 400)
        # ユーザーネームが既に使われている
        if len(db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))) != 0:
            return apology("このユーザーネームは既に使われています", 400)
        # パスワードが入力されていない
        elif not request.form.get("password"):
            return apology("パスワードを入力してください", 400)
        # パスワードが一致しない
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("パスワードが一致しません", 400)
        # データベースに入れる
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", request.form.get(
            "username"), generate_password_hash(request.form.get("password")))
        #メッセージ
        flash("登録が完了しました")
        # ログインページに送る
        return redirect("/login")
    else:
        return render_template("register.html")