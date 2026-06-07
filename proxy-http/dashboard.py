import os
from flask import Flask, jsonify, render_template, request, send_file
from logger import get_metricas, LOGS_CSV

app = Flask(__name__, template_folder="templates")

DIRECTORIO = os.path.dirname(os.path.abspath(__file__))


def leer_archivo(nombre):
    ruta = os.path.join(DIRECTORIO, nombre)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


def guardar_archivo(nombre, contenido):
    ruta = os.path.join(DIRECTORIO, nombre)
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        return True
    except:
        return False


@app.route("/")
def inicio():
    return render_template("dashboard.html", metricas=get_metricas())


@app.route("/exportar/csv")
def exportar_csv():
    if not os.path.exists(LOGS_CSV):
        return "No hay registros todavia.", 404
    return send_file(LOGS_CSV, mimetype="text/csv", as_attachment=True, download_name="logs.csv")


@app.route("/exportar/json")
def exportar_json():
    return jsonify(get_metricas())


@app.route("/blocked", methods=["GET", "POST"])
def blocked():
    if request.method == "GET":
        return jsonify({"contenido": leer_archivo("blocked.txt")})
    contenido = (request.get_json(silent=True) or {}).get("contenido", "")
    ok = guardar_archivo("blocked.txt", contenido)
    return jsonify({"ok": ok, "mensaje": "Lista actualizada" if ok else "Error al guardar"})


@app.route("/keywords", methods=["GET", "POST"])
def keywords():
    if request.method == "GET":
        return jsonify({"contenido": leer_archivo("keywords.txt")})
    contenido = (request.get_json(silent=True) or {}).get("contenido", "")
    ok = guardar_archivo("keywords.txt", contenido)
    return jsonify({"ok": ok, "mensaje": "Lista actualizada" if ok else "Error al guardar"})


def iniciar_dashboard():
    app.run(host="0.0.0.0", port=8081, debug=False, use_reloader=False)
