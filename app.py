from flask import Flask
from flask import send_from_directory
from flask import request
from flask import redirect
from flask import render_template
from datetime import datetime
import sqlite3
import atexit

app = Flask(__name__, template_folder="web")

MET_CLIENTS = []		# ["1.1.1.1", "127.0.0.1", ...]
AUTHORIZED_CLIENTS = {} # {"1.1.1.1":"psswd", "127.0.0.1":"lol123", ...}
DB_CONN = sqlite3.connect('data.db', check_same_thread=False)
DB_CURS = DB_CONN.cursor()

LOGINS = {
	"admin":"admin",
	"john":"doe"
}

def exit_handler():
	global DB_CURS, DB_CONN
	DB_CURS.close()
	DB_CONN.close()
	print("Closed DB")

def serveDocFile(filename):
	file = open(f"web/{filename}", "r")
	content = file.read()
	file.close()
	return content

def isClientNew(ip_addr):
	global MET_CLIENTS
	return ip_addr not in MET_CLIENTS

def isClientAuthorized(ip_addr):
	global AUTHORIZED_CLIENTS
	return ip_addr in AUTHORIZED_CLIENTS.keys()

def validateLogin(uname, psswd):
	global LOGINS
	if uname not in LOGINS.keys():
		return False
	if LOGINS[uname] != psswd:
		return False
	return True

def getEntries():
	global DB_CURS
	entries = DB_CURS.execute("SELECT rowid, * FROM people")
	return tuple(entries)

def renderManagementPage(ip_addr):
	username = AUTHORIZED_CLIENTS[ip_addr]
	date = datetime.now()
	weekday = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")[date.weekday()]
	date = f"{date.day}.{date.month}.{date.year} ({weekday})"
	return render_template("root.html", username=username, date=date, ip_addr=ip_addr, db_entries=getEntries())

def renderEditorPage(operation, id, name, age, email, address):
	return render_template("entry_editor.html", operation=operation, id=id, name=name, age=age, email=email, address=address)

def renderEntryEditPage(entry_id):
	entry = next(DB_CURS.execute(f"SELECT rowid, * FROM people WHERE rowid={entry_id}"))
	return renderEditorPage("Edit entry", *entry)

def renderNewEntryPage():
	return renderEditorPage("Add new entry", "auto-assigned", *(("",) * 4))

def handleKnownClient(ip_addr):
	if isClientAuthorized(ip_addr):
		return redirect("/man")
	else:
		return redirect("/login")

@app.route("/new_client", methods=["GET"])
def new_client():
	if not isClientNew(request.remote_addr):
		return redirect("/")
	return serveDocFile("new_client.html")

@app.route("/ack", methods=["GET"])
def ack_new_client():
	global MET_CLIENTS
	MET_CLIENTS.append(request.remote_addr)
	return redirect("/")

@app.route("/man", methods=["GET"])
def client_management():
	if isClientNew(request.remote_addr):
		return redirect("/new_client")
	if not isClientAuthorized(request.remote_addr):
		return redirect("/login")
	return renderManagementPage(request.remote_addr)

@app.route("/new", methods=["GET"])
def new():
	if not isClientAuthorized(request.remote_addr) or isClientNew(request.remote_addr):
		return "Access Denied - Not logged in", 401
	return renderNewEntryPage()

@app.route("/edit", methods=["GET"])
def edit():
	if not isClientAuthorized(request.remote_addr) or isClientNew(request.remote_addr):
		return "Access Denied - Not logged in", 401
	return renderEntryEditPage(request.args.get("id"))

@app.route("/del", methods=["GET"])
def delete():
	global DB_CURS, DB_CONN
	if not isClientAuthorized(request.remote_addr) or isClientNew(request.remote_addr):
		return "Access Denied - Not logged in", 401
	DB_CURS.execute(f"DELETE FROM people WHERE rowid={request.args.get('id')}")
	DB_CONN.commit()
	return redirect("/man")

@app.route("/submit", methods=["GET"])
def submit():
	global DB_CURS, DB_CONN
	if not isClientAuthorized(request.remote_addr) or isClientNew(request.remote_addr):
		return "Access Denied - Not logged in", 401
	args = request.args
	if args.get("operation") == "Add new entry":
		DB_CURS.execute("INSERT INTO people VALUES (?, ?, ?, ?)",
			(args.get("name"), args.get("age"), args.get("email"), args.get("address"))
		)
		DB_CONN.commit()
	elif args.get("operation") == "Edit entry":
		DB_CURS.execute("UPDATE people SET name=?, age=?, email=?, address=? WHERE rowid=?",
			(args.get("name"), args.get("age"), args.get("email"), args.get("address"),
			 args.get("id"))
		)
		DB_CONN.commit()
	else:
		return "Invalid form operation", 400
	return redirect("/man")

@app.route("/auth", methods=["GET"])
def client_auth():
	if isClientNew(request.remote_addr) or isClientAuthorized(request.remote_addr):
		return "Invalid authentication request", 400
	args = request.args
	username = args.get("username")
	password = args.get("password")
	if validateLogin(username, password):
		global AUTHORIZED_CLIENTS
		AUTHORIZED_CLIENTS[request.remote_addr] = username
		return redirect("/man")
	else:
		return "Access Denied - Invalid login credentials", 401

@app.route("/login", methods=["GET"])
def client_login():
	if isClientNew(request.remote_addr):
		return redirect("/new_client")
	if isClientAuthorized(request.remote_addr):
		return redirect("/man")
	return serveDocFile("login.html")

@app.route("/logout", methods=["GET"])
def client_logout():
	if isClientNew(request.remote_addr) or not isClientAuthorized(request.remote_addr):
		return "Invalid logout request", 400
	global AUTHORIZED_CLIENTS
	del AUTHORIZED_CLIENTS[request.remote_addr]
	return serveDocFile("logout.html")

@app.route("/docs", methods=["GET"])
def docs():
	return serveDocFile("docs.html")

@app.route("/", methods=["GET"])
def main():
    if isClientNew(request.remote_addr):
    	return redirect("/new_client")
    else:
    	return handleKnownClient(request.remote_addr)

DB_CURS.execute("DROP TABLE IF EXISTS people")
DB_CURS.execute('''CREATE TABLE people
               (name text, age int, email text, address text)''')
DB_CURS.execute("INSERT INTO people (name, age, email, address) VALUES ('Eric', 18, 'erik123@gmail.com', '78 Plane rd., California')")
DB_CURS.execute("INSERT INTO people (name, age, email, address) VALUES ('John', 24, 'john@tech.com', '92 Main rd., Texas')")
DB_CURS.execute("INSERT INTO people (name, age, email, address) VALUES ('Rebekah', 34, 'rebs@tvd.cw', '97 Oak tree rd., Virginia')")
DB_CURS.execute("INSERT INTO people (name, age, email, address) VALUES ('Nik', 14, 'admin@outlook.com', '8/71 Quartz M., Virginia')")
DB_CURS.execute("INSERT INTO people (name, age, email, address) VALUES ('Edward', 19, 'edd0_94@gmail.com', '12/6 Hollow rd., Canada')")
DB_CURS.execute("INSERT INTO people (name, age, email, address) VALUES ('Willy', 21, 'william@willspage.net', '22 Grounded Bears, Mars')")
DB_CONN.commit()

atexit.register(exit_handler)
app.run(port=8080)