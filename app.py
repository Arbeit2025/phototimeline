"""フォト年表メーカー phototimeline

思い出を「日付・タイトル・メモ」のテキストだけで登録し、年ごとに
まとめた年表として表示する軽量ツール。画像アップロードや顔検出は
行わない。データは SQLite に保存する。単一ファイル Flask + SQLite。
"""
import os
import re
import sqlite3

from flask import Flask, g, jsonify, redirect, render_template_string, request, url_for

app = Flask(__name__)
DB_PATH = os.environ.get("PHOTOTIMELINE_DB", os.path.join(os.path.dirname(__file__), "phototimeline.db"))
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            memo TEXT NOT NULL DEFAULT ''
        );
        """
    )
    db.commit()
    db.close()


def grouped_entries(db):
    """年（新しい順）→ 年内は日付順、に並べた [(year, [rows]), ...] を返す。"""
    rows = db.execute(
        "SELECT * FROM entries ORDER BY substr(date, 1, 4) DESC, date ASC, id ASC"
    ).fetchall()
    groups = []
    for row in rows:
        year = row["date"][:4]
        if groups and groups[-1][0] == year:
            groups[-1][1].append(row)
        else:
            groups.append((year, [row]))
    return groups


PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>フォト年表メーカー</title>
<style>body{font-family:sans-serif;max-width:680px;margin:2em auto;padding:0 1em}
.year{border-left:4px solid #7aa5c4;padding-left:.8em;margin:1.2em 0}
.entry{margin:.6em 0}.date{color:#555;font-size:.9em}
input,textarea{margin:.2em 0}textarea{width:100%;box-sizing:border-box}</style>
</head><body>
<h1>フォト年表メーカー</h1>
<p>思い出を日付・タイトル・メモのテキストで登録して、年表として振り返るツールです。写真のアップロードや顔検出はしません。</p>

<h2>思い出を登録</h2>
<form method="post" action="{{ url_for('add') }}">
  <div><label>日付 <input type="date" name="date" required></label></div>
  <div><label>タイトル <input type="text" name="title" placeholder="例：初めての旅行" required></label></div>
  <div><label>メモ</label><textarea name="memo" rows="2" placeholder="その日のことを少し"></textarea></div>
  <button type="submit">登録する</button>
</form>

<h2>年表</h2>
{% for year, items in groups %}
<div class="year">
  <h3>{{ year }}年</h3>
  {% for e in items %}
  <div class="entry">
    <span class="date">{{ e.date }}</span> <strong>{{ e.title }}</strong>
    {% if e.memo %}<div>{{ e.memo }}</div>{% endif %}
    <form method="post" action="{{ url_for('delete', eid=e.id) }}" style="display:inline" onsubmit="return confirm('この思い出を削除しますか？')"><button type="submit">削除</button></form>
  </div>
  {% endfor %}
</div>
{% else %}
<p>まだ思い出が登録されていません。</p>
{% endfor %}
</body></html>"""


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    db = get_db()
    return render_template_string(PAGE, groups=grouped_entries(db))


@app.route("/add", methods=["POST"])
def add():
    date = (request.form.get("date") or "").strip()
    title = (request.form.get("title") or "").strip()
    memo = (request.form.get("memo") or "").strip()
    if date and title and DATE_RE.match(date):
        db = get_db()
        db.execute(
            "INSERT INTO entries(date, title, memo) VALUES(?, ?, ?)",
            (date, title, memo),
        )
        db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:eid>", methods=["POST"])
def delete(eid):
    db = get_db()
    db.execute("DELETE FROM entries WHERE id = ?", (eid,))
    db.commit()
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
